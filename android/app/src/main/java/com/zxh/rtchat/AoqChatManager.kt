package com.zxh.rtchat

import android.content.Context
import android.util.Log
import com.alibaba.aoq.clientsdk.AoqClientEngine
import com.alibaba.aoq.clientsdk.AoqClientListener
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.Locale
import java.util.concurrent.Executors

/**
 * AOQ 引擎封装:换 token -> 建连 -> session.update -> 事件分流。
 * 对齐 PC 版 realtime_chat 的会话语义(三角色/server_vad/优雅结束)。
 * 全部 API 签名经 javap 对 v1.3.0 AAR 校验(2026-10-02)。
 */
class AoqChatManager(
    private val appContext: Context,
    private val credentialsProvider: () -> SettingsStore.Credentials,
    private val micGainProvider: () -> Float = { 1.0f },
    private val listener: ChatListener,
) : AoqClientListener() {

    interface ChatListener {
        /** state: connecting / ready / speaking / interrupted / closed */
        fun onState(state: String)
        fun onUserTranscript(text: String)
        fun onAssistantText(delta: String)
        fun onError(code: String, message: String)

        /** 诊断信息(每步进度),显示在界面上便于用户反馈问题 */
        fun onDebug(message: String)
    }

    /**
     * 用量费率口径(阿里云百炼 qwen3.8-omni-flash-realtime / 北京地域,依据 docs/§2.6 实测值)。
     * 官方调价时只需改这里,不要散落在算式里。单位:元 / 百万 token。
     */
    private object Rate {
        const val AUDIO_IN_TOK_PER_SEC = 7.0
        const val AUDIO_OUT_TOK_PER_SEC = 12.5
        const val AUDIO_IN_PER_M = 6.0
        const val AUDIO_OUT_PER_M = 12.0
        const val TEXT_IN_PER_M = 1.5
        const val TEXT_OUT_PER_M = 4.5

        /** 文本 token 粗略折算:中日韩约 1 字≈1 token、ASCII 约 4 字符≈1 token,混合文本取 2。 */
        const val CHARS_PER_TEXT_TOKEN = 2.0
    }

    companion object {
        private const val TAG = "AoqChat"
        const val MODEL = SessionPresets.MODEL
        const val REGION_HOST = "cn-beijing.maas.aliyuncs.com"
    }

    private val executor = Executors.newSingleThreadExecutor()
    private var engine: AoqClientEngine? = null
    private var preset: SessionPresets.Preset = SessionPresets.default()
    @Volatile private var closed = false
    @Volatile private var playbackFrames = 0
    @Volatile private var sessionStartMs = 0L

    // ---------- 用量统计(均在 teardown 时归零,防止跨会话累加) ----------
    /** 下行音频真实时长(秒)。按帧数据折算,不再假设「10ms/帧」。 */
    @Volatile private var playbackAudioSec = 0.0
    /** 累计为当前会话上下文的文本 token(用户+AI),用于模拟「多轮历史逐轮重新计入输入」。 */
    @Volatile private var contextTokens = 0.0
    @Volatile private var textInTokens = 0.0
    @Volatile private var textOutTokens = 0.0
    /** 首帧校核只打一次,避免刷屏。 */
    @Volatile private var frameSizeChecked = false

    // ---------- 费用累计(进程级):从打开应用到退出;退出即清零。转后台/换老师不清零 ----------
    @Volatile private var totalCostAcc = 0.0   // 累计(元)
    @Volatile private var sessionAccrued = 0.0 // 本会话已计入累计的部分(防重复计入)

    // ---------- 静音门(省输入 token) ----------
    private val silenceGate = SilenceGate()
    /**
     * 静音门开关。
     *
     * **默认关闭**：它依赖两个尚未在真机验证的 SDK 假设 ——
     *   ① 能否同时注册「下行播放」与「上行采集」两个音频观察者；
     *   ② 频繁 enableSendMediaStream 切换是否安全。
     * 真机反馈：不开启静音门时上行正常（能识别说话、有回复），
     * 开启后出现「状态一直聆听中、云端无回复」，故默认关闭。
     * 确认可行后再改回 true；也可以调 setSilenceGateEnabled(true) 自行试验。
     */
    private var gateEnabled = false
    /** fail-open:若停上行后收不到采帧(SDK 可能一并停了采集),永久放弃本轮会话的静音门。 */
    @Volatile private var gateFailedOpen = false
    @Volatile private var gateMuted = false
    @Volatile private var lastCaptureAtMs = 0L

    /** 最近一次主动拆除连接的时刻:用于忽略"旧引擎迟到的 Disconnected 通知",避免状态竞态。 */
    @Volatile private var lastTeardownAtMs = 0L

    // ---------- 对外生命周期 ----------

    fun start(preset: SessionPresets.Preset) {
        connectAsync(preset, teardownFirst = false)
    }

    private fun debug(msg: String) {
        AppLog.w(msg)
        listener.onDebug(msg)
    }

    fun switchPreset(preset: SessionPresets.Preset) {
        // 内部重连:不发 closed 状态(UI 的 running 保持 true,避免状态竞态导致双连接)
        connectAsync(preset, teardownFirst = true)
    }

    /** 统一连接序列(换 token -> 建引擎 -> 连接)。teardownFirst=true 用于换老师内部重连。 */
    private fun connectAsync(preset: SessionPresets.Preset, teardownFirst: Boolean) {
        closed = true
        listener.onState("connecting")
        executor.execute {
            if (teardownFirst) teardown()
            this@AoqChatManager.preset = preset
            closed = false
            try {
                debug("正在换取连接令牌…")
                val cfg = exchangeToken(credentialsProvider())
                debug("令牌 OK,中继节点 ${cfg.relayEndpoints.size} 个,正在连接…")
                val eng = initEngine()
                connect(eng, cfg)
            } catch (e: Exception) {
                Log.e(TAG, "connect failed", e)
                listener.onError("start", e.message ?: e.toString())
                listener.onState("closed")
            }
        }
    }

    fun stop() {
        closed = true
        executor.execute { teardown() }
        listener.onState("closed")
    }

    private fun teardown() {
        // 用量统计必须全部归零:switchPreset() 会走「teardown + 重连」,
        // 若不清零,重开会话后指标会从上次继续累加(旧版本会把费用越算越高)。
        sessionStartMs = 0L
        playbackFrames = 0
        playbackAudioSec = 0.0
        contextTokens = 0.0
        textInTokens = 0.0
        textOutTokens = 0.0
        frameSizeChecked = false
        silenceGate.reset()
        sessionAccrued = 0.0 // 仅清算"已计入累计"的记账位;totalCostAcc 为进程级累计,不在此清零
        gateFailedOpen = false
        gateMuted = false
        lastCaptureAtMs = 0L
        lastTeardownAtMs = System.currentTimeMillis()
        unregisterRouteListener()
        try {
            abandonAudioFocus()
        } catch (_: Throwable) {
        }
        exitCommunicationMode()
        try {
            sendJson(SessionPresets.buildSessionFinish())
        } catch (_: Throwable) {
        }
        try {
            engine?.disconnect()
            AoqClientEngine.destroy()
        } catch (_: Throwable) {
        }
        engine = null
    }

    // ---------- token 换取(个人自用:客户端直接持 key,与 PC 版 config.json 同安全水位) ----------

    private data class ConnectCfg(
        val token: String,
        val sid: String,
        val certFingerprint: String,
        val relayEndpoints: List<AoqClientEngine.AoqRelayEndpoint>,
        val workspaceIdHash: String,
    )

    private fun exchangeToken(creds: SettingsStore.Credentials): ConnectCfg {
        if (!creds.isComplete) {
            throw RuntimeException("未配置凭据:请在设置里填入 API Key 和业务空间 ID")
        }
        val host = "${creds.workspaceId}.$REGION_HOST"
        val url = URL("https://$host/api/v1/webrtc/realtime?model=$MODEL")
        val conn = (url.openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            connectTimeout = 10_000
            readTimeout = 10_000
            setRequestProperty("Content-Type", "application/json")
            setRequestProperty("Authorization", "Bearer ${creds.apiKey}")
            setRequestProperty("x-dashscope-rtc-transport", "moq")
            doOutput = true
        }
        conn.outputStream.use { it.write("{\"clientIp\":\"\"}".toByteArray()) }
        val code = conn.responseCode
        val body = (if (code in 200..299) conn.inputStream else conn.errorStream)
            ?.bufferedReader()?.readText() ?: ""
        conn.disconnect()
        if (code !in 200..299) {
            val hint = when (code) {
                401, 403 -> "(请检查 API Key 是否正确、是否有实时语音权限)"
                else -> ""
            }
            throw RuntimeException("换 token 失败 HTTP $code$hint: ${body.take(200)}")
        }
        val json = JSONObject(body)
        val endpoints = mutableListOf<AoqClientEngine.AoqRelayEndpoint>()
        val arr = json.optJSONArray("clientRelayEndpoints")
        for (i in 0 until (arr?.length() ?: 0)) {
            val o = arr!!.getJSONObject(i)
            endpoints.add(
                AoqClientEngine.AoqRelayEndpoint().apply {
                    endpoint = o.getString("endpoint")
                    port = o.getInt("port")
                    routeIndex = i
                }
            )
        }
        return ConnectCfg(
            token = json.getString("aoqTokenForClient"),
            sid = json.getString("sid"),
            certFingerprint = json.getString("clientRelayCertFingerprint"),
            relayEndpoints = endpoints,
            workspaceIdHash = json.getJSONObject("extraInfo").getString("workspaceIdHash"),
        )
    }

    // ---------- 引擎 ----------

    private fun initEngine(): AoqClientEngine {
        val cfg = AoqClientEngine.AoqCreateConfig().apply {
            workDir = appContext.filesDir.absolutePath
        }
        val eng = AoqClientEngine.createEngine(appContext, cfg, this).also { engine = it }
        // 官方 Demo(PhoneCallView.swift:1244-1255):connect 前显式配置 Opus 16k 编解码
        // (Android SDK 默认解码 48k,与官方意图不符)
        try {
            val codec = AoqClientEngine.AoqAudioCodecConfig().apply {
                trackType = AoqClientEngine.AoqTrackType.AoqTrackTypeAudio
                codecType = AoqClientEngine.AoqEncoderType.AoqEncoderTypeAudioOpus
                sampleRate = 16000
                channel = 1
                bitrate = 24000
            }
            val rcEnc = eng.setAudioEncoderConfig(codec)
            val rcDec = eng.setAudioDecoderConfig(codec)
            debug("Opus 编解码(官方 16k):编码 rc=$rcEnc,解码 rc=$rcDec")
        } catch (e: Exception) {
            debug("编解码配置异常:${e.message}")
        }
        // 探测 Opus 插件(下行音频解码依赖,官方文档特别强调需加载;缺失则解码输出静音)
        try {
            System.loadLibrary("PluginOpus")
            debug("Opus 插件加载: OK")
        } catch (e: Throwable) {
            debug("Opus 插件加载失败: ${e.message}(下行音频可能无法解码=静音)")
        }
        return eng
    }

    // ---------- 安卓音频焦点(Android 规则:通话音频须申请,防与其他 App 抢声道被静音) ----------

    private var audioFocusHeld = false

    /**
     * 焦点请求对象必须**复用到归还**,不能归还时新建 ——
     * 这是 AudioFocusRequest 的使用要求,否则部分机型不会真正释放。
     */
    private var focusRequest: android.media.AudioFocusRequest? = null

    private fun requestAudioFocus() {
        if (android.os.Build.VERSION.SDK_INT < 26) return
        val am = appContext.getSystemService(Context.AUDIO_SERVICE) as android.media.AudioManager
        val req = android.media.AudioFocusRequest.Builder(android.media.AudioManager.AUDIOFOCUS_GAIN_TRANSIENT)
            .setAudioAttributes(
                android.media.AudioAttributes.Builder()
                    .setUsage(android.media.AudioAttributes.USAGE_VOICE_COMMUNICATION)
                    .setContentType(android.media.AudioAttributes.CONTENT_TYPE_SPEECH)
                    .build()
            )
            // 必须注册监听:别的 App(导航/闹钟/来电)抢走声道时要能收到通知,
            // 否则本应用会毫无察觉地继续上行(白烧钱)或继续出声(该停时没停)。
            .setOnAudioFocusChangeListener { change -> onAudioFocusChanged(change) }
            .build()
        focusRequest = req
        val rc = am.requestAudioFocus(req)
        audioFocusHeld = rc == android.media.AudioManager.AUDIOFOCUS_REQUEST_GRANTED
        debug("音频焦点: ${if (audioFocusHeld) "已获得" else "获取失败(rc=$rc)"}")
    }

    /**
     * 焦点变化**只做记录,绝不改变上行**。
     *
     * 真机教训:原先在焦点丢失时调用 enableSendMediaStream(false) 停上行,
     * 结果 vivo 上一次 AUDIOFOCUS_LOSS 就让整轮对话失效 ——
     * 服务端收不到音频,既不识别用户语音,AI 也不回复,而且没有任何界面提示。
     * 焦点被抢占只意味着"该让出播放",并不代表不能录音;
     * 通话类 App 在这种情况下照常上行,否则对方的声音就听不到了。
     */
    private fun onAudioFocusChanged(change: Int) {
        val name = when (change) {
            android.media.AudioManager.AUDIOFOCUS_GAIN -> "GAIN 获得"
            android.media.AudioManager.AUDIOFOCUS_LOSS -> "LOSS 永久丢失"
            android.media.AudioManager.AUDIOFOCUS_LOSS_TRANSIENT -> "LOSS_TRANSIENT 暂时被打断"
            android.media.AudioManager.AUDIOFOCUS_LOSS_TRANSIENT_CAN_DUCK -> "CAN_DUCK 需降低音量"
            else -> "未知"
        }
        debug("音频焦点变化:$name(不改变上行)")
    }

    /** 音频路由实况:模式/扬声器/通信设备(验证我们的设置是否被 SDK 顶掉)。 */
    private fun audioRouteText(): String {
        val am = appContext.getSystemService(Context.AUDIO_SERVICE) as android.media.AudioManager
        val mode = am.mode // 0=NORMAL 1=RINGTONE 2=IN_CALL 3=IN_COMMUNICATION
        val spk = am.isSpeakerphoneOn
        val device = if (android.os.Build.VERSION.SDK_INT >= 31) {
            am.communicationDevice?.let { nameOfAudioType(it.type) } ?: "未指定"
        } else {
            try {
                val outs = am.getDevices(android.media.AudioManager.GET_DEVICES_OUTPUTS)
                if (outs.isEmpty()) "无" else outs.joinToString("+") { nameOfAudioType(it.type) }
            } catch (e: Exception) {
                "查询失败"
            }
        }
        return "mode=$mode(3=通话) 扬声器=$spk 通信设备/可用输出=$device"
    }

    private fun nameOfAudioType(type: Int): String = when (type) {
        android.media.AudioDeviceInfo.TYPE_BUILTIN_SPEAKER -> "扬声器"
        android.media.AudioDeviceInfo.TYPE_BUILTIN_EARPIECE -> "听筒"
        android.media.AudioDeviceInfo.TYPE_BLUETOOTH_SCO -> "蓝牙SCO"
        android.media.AudioDeviceInfo.TYPE_BLUETOOTH_A2DP -> "蓝牙A2DP"
        android.media.AudioDeviceInfo.TYPE_WIRED_HEADSET -> "有线耳机"
        else -> "type=$type"
    }

    /** 各音量流实时值(截图即见根因:通话音量是否为 0)。 */
    private fun volumeStreamsText(): String {
        val am = appContext.getSystemService(Context.AUDIO_SERVICE) as android.media.AudioManager
        val call = am.getStreamVolume(android.media.AudioManager.STREAM_VOICE_CALL)
        val music = am.getStreamVolume(android.media.AudioManager.STREAM_MUSIC)
        return "通话音量=$call/${am.getStreamMaxVolume(android.media.AudioManager.STREAM_VOICE_CALL)} 媒体音量=$music"
    }

    /** 安卓规则:通话类音频必须进入 MODE_IN_COMMUNICATION,否则 STREAM_VOICE_CALL 播放被系统丢弃(无声)。 */
    private fun enterCommunicationMode() {
        val am = appContext.getSystemService(Context.AUDIO_SERVICE) as android.media.AudioManager
        try {
            am.mode = android.media.AudioManager.MODE_IN_COMMUNICATION
            debug("音频模式:已进入 IN_COMMUNICATION(原模式=$modeBefore)")
        } catch (e: Exception) {
            debug("进入通话音频模式失败:${e.message}")
        }
    }

    private fun exitCommunicationMode() {
        val am = appContext.getSystemService(Context.AUDIO_SERVICE) as android.media.AudioManager
        try {
            am.isSpeakerphoneOn = false
            am.mode = android.media.AudioManager.MODE_NORMAL
            debug("音频模式:已恢复 NORMAL")
        } catch (_: Throwable) {
        }
    }

    private var modeBefore = 0

    /** 安卓通话类 App 标准做法:通话音量为 0 时自动调到 70%(否则通话音频无声)。 */
    private fun ensureAudibleVolume() {
        val am = appContext.getSystemService(Context.AUDIO_SERVICE) as android.media.AudioManager
        val stream = android.media.AudioManager.STREAM_VOICE_CALL
        val cur = am.getStreamVolume(stream)
        if (cur == 0) {
            val target = (am.getStreamMaxVolume(stream) * 7 / 10).coerceAtLeast(1)
            try {
                am.setStreamVolume(stream, target, 0)
                debug("通话音量为 0,已自动调到 $target")
            } catch (e: Exception) {
                debug("自动调通话音量失败(请在系统设置里调大通话音量):${e.message}")
            }
        }
    }

    private fun abandonAudioFocus() {
        if (android.os.Build.VERSION.SDK_INT < 26) return
        val req = focusRequest
        focusRequest = null
        if (!audioFocusHeld || req == null) {
            audioFocusHeld = false
            return
        }
        val am = appContext.getSystemService(Context.AUDIO_SERVICE) as android.media.AudioManager
        // 归还时必须传当初申请的那个对象,不能新建
        am.abandonAudioFocusRequest(req)
        audioFocusHeld = false
    }

    /**
     * 是否接了"通话用"外接设备(蓝牙 SCO / 有线 / USB 耳机)。
     * 刻意**不算 A2DP**:它是媒体流,延迟大且不带麦克风,通话必须用 SCO。
     *
     * 真机教训(vivo / Android 13):原先用 `availableCommunicationDevices` 判断,
     * 它会把"蓝牙已开启但根本没连耳机"的设备也算进来,于是误判成有耳机,
     * 触发 `enableSpeakerphone(false)` → SDK 报 error 128
     * "EnableSpeakerphone false requires Voip mode" → 音频管线异常。
     * 现在只认**当前实际通信设备** `communicationDevice`,判断保守宁可不切。
     */
    private fun hasCallOutputDevice(): Boolean {
        val am = appContext.getSystemService(Context.AUDIO_SERVICE) as android.media.AudioManager
        val wanted = setOf(
            android.media.AudioDeviceInfo.TYPE_BLUETOOTH_SCO,
            android.media.AudioDeviceInfo.TYPE_WIRED_HEADSET,
            android.media.AudioDeviceInfo.TYPE_USB_HEADSET,
        )
        return try {
            if (android.os.Build.VERSION.SDK_INT >= 31) {
                am.communicationDevice?.let { it.type in wanted } ?: false
            } else {
                // Android 11 及以下没有 communicationDevice,退回枚举输出设备,
                // 但排除"仅蓝牙开启未连接"的情况:只有 SCO 出现才算耳机。
                am.getDevices(android.media.AudioManager.GET_DEVICES_OUTPUTS)
                    .any { it.type in wanted }
            }
        } catch (e: Exception) {
            AppLog.w("检测外接音频设备失败:${e.message}")
            false
        }
    }

    /**
     * 按当前耳机状态决定要不要开外放。
     *
     * 原来无论有没有耳机都强制开扬声器 —— 用户戴着蓝牙耳机时声音仍从外放出来,
     * 旁边的人能听到对话内容(隐私泄露),而且用户以为在用耳机。
     * 现在:有耳机就走耳机,没耳机才开外放。
     */
    private var lastHeadsetPresent = false
    private var routePolicyKnown = false

    private fun applySpeakerPolicy(): Boolean {
        val withHeadset = hasCallOutputDevice()
        val speakerOn = !withHeadset
        // 状态没变就不重复下发(SDK 的 route 回调较频繁,避免反复调用)
        if (routePolicyKnown && withHeadset == lastHeadsetPresent) return speakerOn
        routePolicyKnown = true
        lastHeadsetPresent = withHeadset
        val rc = try {
            engine?.enableSpeakerphone(speakerOn) ?: -1
        } catch (e: Throwable) {
            AppLog.w("切换扬声器失败:${e.message}")
            -1
        }
        try {
            val am = appContext.getSystemService(Context.AUDIO_SERVICE) as android.media.AudioManager
            am.isSpeakerphoneOn = speakerOn
        } catch (_: Throwable) {
        }
        debug("音频输出策略:${if (speakerOn) "外放(未检测到耳机)" else "耳机(已跳过外放)"} rc=$rc")
        return speakerOn
    }

    /** 耳机插拔广播:插上要立刻切到耳机,拔掉要立刻回外放,否则会有一段时间声音跑错地方。 */
    private var routeReceiver: android.content.BroadcastReceiver? = null

    private fun registerRouteListener() {
        if (routeReceiver != null) return
        val receiver = object : android.content.BroadcastReceiver() {
            override fun onReceive(ctx: android.content.Context?, intent: android.content.Intent?) {
                val plugged = intent?.getIntExtra("state", 0) == 1
                debug("耳机广播:state=$plugged")
                applySpeakerPolicy()
            }
        }
        try {
            androidx.core.content.ContextCompat.registerReceiver(
                appContext, receiver,
                android.content.IntentFilter(android.media.AudioManager.ACTION_HEADSET_PLUG),
                androidx.core.content.ContextCompat.RECEIVER_NOT_EXPORTED,
            )
            routeReceiver = receiver
        } catch (e: Exception) {
            AppLog.w("注册耳机监听失败(不影响使用):${e.message}")
        }
    }

    private fun unregisterRouteListener() {
        routeReceiver?.let {
            try {
                appContext.unregisterReceiver(it)
            } catch (_: Throwable) {
            }
        }
        routeReceiver = null
    }

    /** 官方 PhoneCallView 时序:Connected 后启动音频。capture 带 isVoipMode=true,player 用默认(isDefaultSpeaker=true)。 */
    private fun startAudioDevices() {
        if (android.os.Build.VERSION.SDK_INT >= 23 &&
            appContext.checkSelfPermission(android.Manifest.permission.RECORD_AUDIO) !=
            android.content.pm.PackageManager.PERMISSION_GRANTED
        ) {
            throw RuntimeException("缺少麦克风权限:请在弹窗或系统设置中授予后,点「连接」重试")
        }
        requestAudioFocus() // 安卓规则①:先抢音频焦点
        val amTmp = appContext.getSystemService(Context.AUDIO_SERVICE) as android.media.AudioManager
        modeBefore = amTmp.mode
        enterCommunicationMode() // 安卓规则②:进入通话音频模式,否则通话流被系统静音

        // === 官方 PhoneCallView 顺序:播放 → 扬声器 → 采集 ===
        // WebRTC AEC 需要播放(render)流先就位作为回声参考;顺序颠倒会让音频管线初始化异常(无声)
        val rcPlay = engine?.startAudioPlayer(
            AoqClientEngine.AoqAudioPlaybackConfig().apply {
                channel = 1
                isExternal = false
                isDefaultSpeaker = true
            }
        ) ?: -1
        // 输出设备策略:检测到耳机就不开外放(见 applySpeakerPolicy 的隐私说明)
        applySpeakerPolicy()
        registerRouteListener()
        // 采集放最后
        val rcCap = engine?.startAudioCapture(
            AoqClientEngine.AoqAudioCaptureConfig().apply {
                channel = 1
                isExternal = false
                isVoipMode = true // 官方 PhoneCallView 实参
            }
        ) ?: -1

        debug("音频设备(官方顺序 播放→输出策略→采集):播放 rc=$rcPlay,采集 rc=$rcCap")
        debug("当前${volumeStreamsText()}")
        debug("路由:${audioRouteText()}")
        ensureAudibleVolume()
        if (rcCap != 0) listener.onError("audio", "启动麦克风失败(rc=$rcCap),请检查麦克风权限")
        if (rcPlay != 0) listener.onError("audio", "启动播放失败(rc=$rcPlay)")
    }

    private fun connect(eng: AoqClientEngine, cfg: ConnectCfg) {
        fun track(type: AoqClientEngine.AoqTrackType) =
            AoqClientEngine.AoqTrackParam().apply {
                trackType = type
                trackMode = AoqClientEngine.AoqTrackMode.AoqTrackModeSegment // 官方默认;Stream 模式被 native 守卫拒绝(不支持该音频订阅)
            }
        val connectCfg = AoqClientEngine.AoqConnectConfig().apply {
            token = cfg.token
            sid = cfg.sid
            certFingerprint = cfg.certFingerprint
            relayEndpoints = cfg.relayEndpoints
            workspaceIdHash = cfg.workspaceIdHash
            publishTracks = listOf(track(AoqClientEngine.AoqTrackType.AoqTrackTypeAudio), track(AoqClientEngine.AoqTrackType.AoqTrackTypeData))
            subscribeTracks = listOf(track(AoqClientEngine.AoqTrackType.AoqTrackTypeAudio), track(AoqClientEngine.AoqTrackType.AoqTrackTypeData))
        }
        // 官方时序:关推流 -> connect(音频设备在 Connected 回调后启动)
        eng.enableSendMediaStream(AoqClientEngine.AoqTrackType.AoqTrackTypeAudio, false)
        val rc = eng.connect(connectCfg)
        if (rc != 0) {
            throw RuntimeException("engine.connect 返回错误码 $rc")
        }
    }

    private fun sendJson(json: JSONObject) {
        val msg = AoqClientEngine.AoqDataMsg().apply { data = json.toString().toByteArray(Charsets.UTF_8) }
        engine?.sendDataMsg(msg)
    }

    /** 连接就绪(session.updated 已确认)后:放推流 + 下行帧探针,进入就绪态。 */
    private fun onSessionReady() {
        val rcSend = engine?.enableSendMediaStream(AoqClientEngine.AoqTrackType.AoqTrackTypeAudio, true) ?: -1
        debug("音频推流 rc=$rcSend")

        // 下行音频帧诊断:直接观察远端音频是否到达本机(区分"没数据"还是"有数据没播出来")
        try {
            val observer = object : AoqClientListener.AoqAudioFrameListener {
                override fun onPlaybackAudioFrame(frame: AoqClientEngine.AoqAudioFrameData) {
                    playbackFrames++
                    // 真实时长 = 采样数 / 采样率(PCM16 单声道),不再依赖「10ms/帧」的假设
                    val sps = frame.samplesPerSec
                    val ms = frameMsOf(frame)
                    if (sps > 0) playbackAudioSec += (frame.dataSize / 2).toDouble() / sps.toDouble()
                    if (!frameSizeChecked) {
                        frameSizeChecked = true
                        debug("帧尺寸校核(下行):${sps}Hz ${frame.dataSize}B -> %.2fms/帧".format(Locale.US, ms))
                    }
                    if (playbackFrames == 1 || playbackFrames % 100 == 0) {
                        val data = frame.dataPtr
                        val nonZero = if (data == null) -1 else data.count { it.toInt() != 0 }
                        val verdict = when {
                            nonZero < 0 -> "无数据指针(异常)"
                            nonZero == 0 -> "数据流已到达(全零不代表静音:此观察源不反映实际播放)"
                            else -> "有声音数据"
                        }
                        debug("下行音频 ${playbackFrames}帧 ${sps}Hz ${frame.dataSize}B 非零=${nonZero} -> $verdict")
                    }
                }

                /**
                 * 处理后的采集帧(3A 之后、编码发布之前),唯一的"上行写"入口:
                 * ①静音门统计(先于缩放,保证按原始音量判定);
                 * ②「麦克风灵敏度」就地压低音频(经 ReadWrite 观察者生效)。
                 * 该回调运行在 SDK 音频线程:只做就地改帧,不做耗时操作。
                 */
                override fun onProcessCapturedAudioFrame(frame: AoqClientEngine.AoqAudioFrameData) {
                    val data = frame.dataPtr ?: return
                    val sps = frame.samplesPerSec
                    if (sps <= 0) return
                    lastCaptureAtMs = System.currentTimeMillis()
                    if (gateEnabled && !gateFailedOpen) {
                        if (silenceGate.framesIn == 0L) {
                            debug("帧尺寸校核(上行):${sps}Hz ${frame.dataSize}B -> %.2fms/帧".format(
                                Locale.US, frameMsOf(frame)))
                        }
                        applyUplink(silenceGate.feed(data, frameMsOf(frame)))
                    }
                    MicGain.applyInPlace(data, frame.dataSize, micGainProvider())
                }
            }
            engine?.setAudioFrameObserver(observer)
            val cfgDown = AoqClientEngine.AoqAudioObserverConfig().apply {
                sampleRate = 16000
                channels = 1
                mode = AoqClientEngine.AoqAudioObserverMode.AoqAudioObserverModeReadOnly
            }
            val rcObs = engine?.enableAudioFrameObserver(
                true,
                AoqClientEngine.AoqAudioSource.AoqAudioSourcePlayback,
                cfgDown,
            ) ?: -1
            debug("音频观察者(下行) rc=$rcObs")
            // 上行观察者:读写模式,承载「麦克风灵敏度」的就地压低(以及静音门统计)。
            // 多源注册(下行只读 + 上行读写)对应 SDK 的 4 个独立回调,属设计用法;
            // 若真机出现上行异常,先把灵敏度档位调回「很高」(0 dB)排除增益因素。
            val rcObsUp = engine?.enableAudioFrameObserver(
                true,
                AoqClientEngine.AoqAudioSource.AoqAudioSourceProcessCaptured,
                AoqClientEngine.AoqAudioObserverConfig().apply {
                    sampleRate = 16000
                    channels = 1
                    mode = AoqClientEngine.AoqAudioObserverMode.AoqAudioObserverModeReadWrite
                },
            ) ?: -1
            debug("音频观察者(上行/读写) rc=$rcObsUp")
        } catch (e: Exception) {
            debug("音频观察者异常:${e.message}")
        }
        if (sessionStartMs == 0L) sessionStartMs = System.currentTimeMillis()
        listener.onState("ready")
    }

    /** 一帧的真实毫秒数(PCM16 单声道:每采样 2 字节)。 */
    private fun frameMsOf(frame: AoqClientEngine.AoqAudioFrameData): Double {
        val sps = frame.samplesPerSec
        return if (sps <= 0) 0.0 else (frame.dataSize / 2).toDouble() / sps.toDouble() * 1000.0
    }

    /** 静音门 -> 停/恢复上行。状态未变则不调 SDK,避免无谓调用。 */
    private fun applyUplink(send: Boolean) {
        if (gateFailedOpen && !send) return
        if (send == !gateMuted) return // 已是目标状态
        gateMuted = !send
        val rc = engine?.enableSendMediaStream(
            AoqClientEngine.AoqTrackType.AoqTrackTypeAudio, send
        ) ?: -1
        debug("静音门:${if (send) "恢复上行" else "停止上行"}(rc=$rc,累计发送率=${(silenceGate.sentRatio * 100).toInt()}%)")
    }

    /** 看门狗:若停上行后连采帧都收不到,说明 SDK 一并停了采集 → fail-open 恢复常发。 */
    private fun watchdogGate() {
        if (!gateEnabled || gateFailedOpen) return
        if (gateMuted && lastCaptureAtMs > 0 && System.currentTimeMillis() - lastCaptureAtMs > 1000) {
            gateFailedOpen = true
            debug("静音门:停上行后收不到采帧,已 fail-open 恢复常发(行为回退到旧版本)")
            applyUplink(true)
        }
    }

    /** 用量估算:(本次费用元, 累计费用元, 连接秒数)。
     *  本次:静音门生效按实际发送量/否则按连接时长 + 下行真实帧折算 + 文本 token;
     *  累计:从打开应用到退出的进程级累计(转后台/换老师不清;退出即清零)。仅供参考。 */
    fun usageEstimate(): Triple<Double, Double, Long> {
        watchdogGate()
        val start = sessionStartMs
        val connSecs = if (start > 0) (System.currentTimeMillis() - start) / 1000.0 else 0.0
        val upSecs = if (gateEngaged()) silenceGate.sentSec else connSecs
        val sessionCost =
            upSecs * Rate.AUDIO_IN_TOK_PER_SEC * Rate.AUDIO_IN_PER_M / 1_000_000 +
                playbackAudioSec * Rate.AUDIO_OUT_TOK_PER_SEC * Rate.AUDIO_OUT_PER_M / 1_000_000 +
                textInTokens * Rate.TEXT_IN_PER_M / 1_000_000 +
                textOutTokens * Rate.TEXT_OUT_PER_M / 1_000_000
        // 把本会话的新增部分计入进程累计(重连后"本次"归零,累计继续)
        val delta = sessionCost - sessionAccrued
        if (delta > 0) {
            totalCostAcc += delta
            sessionAccrued = sessionCost
        }
        return Triple(sessionCost, totalCostAcc, connSecs.toLong())
    }

    /** 静音门是否真的在起作用:收到过上行采帧,且没走 fail-open。 */
    private fun gateEngaged(): Boolean = gateEnabled && !gateFailedOpen && silenceGate.framesIn > 0

    // ---------- 文本 token 统计 ----------

    private fun charsToTokens(s: String): Double = s.length / Rate.CHARS_PER_TEXT_TOKEN

    /** 用户一轮发言:本轮 + 到目前为止的上下文都要重新作为输入发给服务端。 */
    private fun noteUserTurn(text: String) {
        val cur = charsToTokens(text)
        textInTokens += contextTokens + cur
        contextTokens += cur
    }

    /** AI 每个增量:既是输出,也会进入下一轮的输入上下文。 */
    private fun noteAssistantDelta(delta: String) {
        val t = charsToTokens(delta)
        textOutTokens += t
        contextTokens += t
    }

    /**
     * 静音门开关。**默认关闭**(见 [gateEnabled] 处说明),真机验证通过前请勿开启。
     * 开启后若出现漏字/吞句,调 false 即可回到"始终上行"的旧行为。
     */
    fun setSilenceGateEnabled(enabled: Boolean) {
        gateEnabled = enabled
        if (!enabled) {
            gateFailedOpen = true
            gateMuted = true
            applyUplink(true)
        } else {
            gateFailedOpen = false
        }
        debug("静音门开关:${if (enabled) "开启" else "关闭"}")
    }

    // ---------- AoqClientListener 回调(签名经 javap 校验) ----------

    override fun onConnectionStatusChange(status: AoqClientEngine.AoqConnectionStatus) {
        AppLog.w("连接状态: $status")
        when (status) {
            AoqClientEngine.AoqConnectionStatus.AoqConnectionStatusConnected -> {
                // 官方 PhoneCallView 时序:connected -> 启动音频;session.update 在收到 session.created 后发
                debug("通道已连接,启动音频设备…")
                startAudioDevices()
            }
            AoqClientEngine.AoqConnectionStatus.AoqConnectionStatusFailed -> {
                listener.onError("connect", "连接失败")
                listener.onState("closed")
            }
            AoqClientEngine.AoqConnectionStatus.AoqConnectionStatusDisconnected -> {
                // 防竞态:刚主动拆过连接(改设置/切角色)时,旧引擎的 Disconnected 通知可能迟到,
                // 照常上报会把重连后的新连接状态刷成"已断开"(PC 版踩过同款坑)。
                val sinceTeardown = System.currentTimeMillis() - lastTeardownAtMs
                if (!closed && sinceTeardown > 2000) {
                    listener.onState("closed")
                } else if (!closed) {
                    AppLog.w("忽略迟到的 Disconnected(主动拆除 ${sinceTeardown}ms 前)")
                }
            }
            else -> listener.onState("connecting")
        }
    }

    override fun onDataMsg(msg: AoqClientEngine.AoqDataMsg) {
        val text = String(msg.data ?: return, Charsets.UTF_8)
        val json = try {
            JSONObject(text)
        } catch (e: Exception) {
            Log.w(TAG, "non-json data msg: ${text.take(120)}")
            return
        }
        val type = json.optString("type")
        AppLog.w("<< $type")
        when (type) {
            "session.created" -> {
                debug("收到 session.created,下发会话配置…")
                sendJson(SessionPresets.buildSessionUpdate(preset))
            }
            "session.updated" -> onSessionReady()
            "input_audio_buffer.speech_started" -> listener.onState("interrupted")
            "response.created" -> listener.onState("speaking")
            "response.done" -> listener.onState("ready")
            "conversation.item.input_audio_transcription.completed" -> {
                json.optString("transcript").takeIf { it.isNotEmpty() }?.let {
                    noteUserTurn(it)
                    listener.onUserTranscript(it)
                }
            }
            "response.audio_transcript.delta" -> {
                json.optString("delta").takeIf { it.isNotEmpty() }?.let {
                    noteAssistantDelta(it)
                    listener.onAssistantText(it)
                }
            }
            "error" -> {
                val err = json.optJSONObject("error")
                listener.onError(err?.optString("code") ?: "unknown", err?.optString("message") ?: text)
            }
            else -> debug("事件:$type")
        }
    }

    override fun onError(errorCode: Int, message: String) {
        AppLog.w("ERROR engine error $errorCode $message")
        listener.onError("engine:$errorCode", message)
    }

    // ---------- 音频设备诊断回调 ----------

    override fun onAudioDeviceStateChanged(state: AoqClientEngine.AoqAudioDeviceState) {
        debug("音频设备:${state.state}(reason=${state.reason})")
    }

    override fun onAudioDeviceRouteChanged(route: Int) {
        debug("音频路由切换:route=$route")
        // 蓝牙耳机接入/摘下由 SDK 回调告知,这里重新按「有耳机就不外放」决策
        applySpeakerPolicy()
    }

    override fun onAudioDeviceInterrupted(interrupted: Boolean) {
        debug("音频设备打断:interrupted=$interrupted")
    }

    override fun onWarning(code: Int, message: String) {
        Log.w(TAG, "warn $code $message")
    }

    /** 订阅统计(每 5s 一条):下行字节数 + 播放音量,一锤定音"数据到没到/音量是否为 0"。 */
    private var lastStatsAt = 0L

    override fun onStats(stats: AoqClientEngine.AoqStats) {
        val now = System.currentTimeMillis()
        if (now - lastStatsAt < 5000) return
        lastStatsAt = now
        val sub = stats.audioSubscribeStats?.firstOrNull()
        if (sub != null) {
            debug("下行统计:已收 ${sub.bytes / 1024}KB ${sub.bitrate}bps | ${volumeStreamsText()}")
        } else {
            debug("下行统计:无音频订阅轨道!")
        }
    }
}
