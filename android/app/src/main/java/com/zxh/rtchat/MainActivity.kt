package com.zxh.rtchat

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.graphics.Typeface
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.view.View
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.EditText
import android.widget.ImageButton
import android.widget.LinearLayout
import android.widget.RadioGroup
import android.widget.ScrollView
import android.widget.Spinner
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import java.util.Locale

class MainActivity : AppCompatActivity(), AoqChatManager.ChatListener {

    companion object {
        const val REQ_PERM = 41
    }

    /**
     * 应用内语言在这里生效(必须早于 setContentView 与任何 getString)。
     * 用 applicationContext 建 store,避免在 attach 阶段持有尚未成型的 Activity。
     */
    override fun attachBaseContext(newBase: Context) {
        val lang = SettingsStore(newBase.applicationContext).appLanguage
        super.attachBaseContext(LocaleHelper.wrap(newBase, lang))
    }

    private lateinit var store: SettingsStore
    private lateinit var manager: AoqChatManager
    private lateinit var stateDot: View
    private lateinit var stateText: TextView
    private lateinit var bubbleContainer: LinearLayout
    private lateinit var scroll: ScrollView
    private lateinit var errText: TextView
    private lateinit var usageText: TextView
    private lateinit var btnToggle: Button
    private lateinit var spinner: Spinner
    private var running = false
    private val usageHandler = Handler(Looper.getMainLooper())
    private val usageTick = object : Runnable {
        override fun run() {
            if (running) {
                val (sessionCost, totalCost, secs) = manager.usageEstimate()
                // Locale.US:小数分隔符固定为「.」,避免系统语言变化时显示成 ¥0,022
                usageText.text = String.format(
                    Locale.US, getString(R.string.usage_format),
                    sessionCost, totalCost, secs / 60, secs % 60
                )
                usageHandler.postDelayed(this, 2000)
            }
        }
    }
    private var currentAiBubble: TextView? = null
    private var lastPresetKey: String = SessionPresets.default().key

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        AppLog.init(applicationContext)
        setContentView(R.layout.activity_main)
        store = SettingsStore(this)
        stateDot = findViewById(R.id.stateDot)
        stateText = findViewById(R.id.stateText)
        bubbleContainer = findViewById(R.id.bubbleContainer)
        scroll = findViewById(R.id.scrollTranscript)
        errText = findViewById(R.id.errText)
        usageText = findViewById(R.id.usageText)
        btnToggle = findViewById(R.id.btnToggle)
        spinner = findViewById(R.id.presetSpinner)
        val btnLang = findViewById<Button>(R.id.btnLang)
        btnLang.text = getString(LocaleHelper.shortLabelRes(store.appLanguage))
        btnLang.setOnClickListener { showLanguageDialog() }
        findViewById<ImageButton>(R.id.btnSettings).setOnClickListener { showSettingsDialog(required = false) }
        findViewById<ImageButton>(R.id.btnHelp).setOnClickListener { showHelpDialog() }

        spinner.adapter = ArrayAdapter(
            this, android.R.layout.simple_spinner_dropdown_item,
            SessionPresets.ALL.map { presetLabel(it) },
        )
        spinner.onItemSelectedListener = object : android.widget.AdapterView.OnItemSelectedListener {
            override fun onItemSelected(p: android.widget.AdapterView<*>?, v: View?, pos: Int, id: Long) {
                if (!running) return
                val preset = SessionPresets.ALL.getOrElse(pos) { SessionPresets.default() }
                if (preset.key == lastPresetKey) return
                lastPresetKey = preset.key
                sysLine(getString(R.string.sys_switch_preset, presetLabel(preset)))
                manager.switchPreset(preset)
            }

            override fun onNothingSelected(p: android.widget.AdapterView<*>?) {}
        }
        btnToggle.setOnClickListener { toggle() }
        manager = AoqChatManager(
            this,
            { store.credentials },
            { MicGain.factor(store.micGainLevel) },
            this,
        )

        if (!store.credentials.isComplete) {
            showSettingsDialog(required = true)
        } else {
            startIfMicGrantedOrRequest() // 打开即自动连接(权限已授则直连;未授则授权后自动连)
        }
    }

    // ---------- 生命周期 ----------

    /** 刚刚因「退到后台」自动断开过,回到前台要提示一次 */
    private var bgDisconnected = false

    override fun onStart() {
        super.onStart()
        if (bgDisconnected) {
            bgDisconnected = false
            errText.setTextColor(ContextCompat.getColor(this, R.color.err_text))
            errText.text = getString(R.string.info_bg_disconnected)
        }
    }

    /**
     * 退到后台(按 Home / 切换到别的 App / 锁屏)时立刻断开连接。
     *
     * 为什么必须做:安卓**不会**因为退到后台就替我们关闭连接和麦克风。
     * 不处理的结果是——用户以为已经退出了,实际麦克风可能还在收音、
     * 费用按秒累计(实测 ≈0.15 元/小时),而且界面没有任何提示。
     * 这是最容易招来"我明明关了还在扣钱"投诉的问题。
     *
     * 取舍:这里只拦"完全不可见"(onStop),不拦 onPause,
     * 这样用户切到浏览器查 API Key 之类的操作不会被打断。
     * 若将来要支持后台通话,必须同时挂一条常驻通知(安卓规定)。
     */
    override fun onStop() {
        super.onStop()
        disconnectForBackground()
    }

    private fun disconnectForBackground() {
        if (!running) return
        if (this::manager.isInitialized) manager.stop()
        running = false
        usageHandler.removeCallbacks(usageTick)
        usageText.text = ""
        btnToggle.text = getString(R.string.btn_connect)
        bgDisconnected = true
        AppLog.w("退到后台,已自动断开(避免后台计费与麦克风持续采集)")
    }

    // ---------- 界面语言 ----------

    /** 角色名按当前界面语言取(给用户看的下拉列表);日志仍用 SessionPresets 里的原始 label。 */
    private fun presetLabel(p: SessionPresets.Preset): String = when (p.key) {
        "english_teacher" -> getString(R.string.preset_english)
        "japanese_teacher" -> getString(R.string.preset_japanese)
        "russian_teacher" -> getString(R.string.preset_russian)
        "chinese_teacher" -> getString(R.string.preset_chinese)
        "spanish_teacher" -> getString(R.string.preset_spanish)
        "french_teacher" -> getString(R.string.preset_french)
        "korean_teacher" -> getString(R.string.preset_korean)
        "german_teacher" -> getString(R.string.preset_german)
        else -> p.label // 新增预设忘了配字符串时的兜底
    }

    private fun langName(lang: String): String =
        getString(if (lang == LocaleHelper.LANG_ZH) R.string.lang_name_zh else R.string.lang_name_en)

    /**
     * 语言选择:顶栏常驻按钮,一点即达。
     * 切换后 recreate() 重建界面;若正在通话会随之断开(属预期行为,重新点连接即可)。
     */
    private fun showLanguageDialog() {
        val langs = LocaleHelper.SUPPORTED
        val names = langs.map { langName(it) }.toTypedArray()
        val current = langs.indexOf(store.appLanguage)
        AlertDialog.Builder(this)
            .setTitle(getString(R.string.lang_title))
            .setSingleChoiceItems(names, current) { dialog, which ->
                val picked = langs[which]
                dialog.dismiss()
                if (picked == store.appLanguage) return@setSingleChoiceItems
                store.appLanguage = picked
                Toast.makeText(this, getString(R.string.lang_switched), Toast.LENGTH_SHORT).show()
                recreate()
            }
            .setNegativeButton(getString(R.string.btn_cancel), null)
            .show()
    }

    // ---------- 设置(首次引导 + 随时修改) ----------

    private fun showSettingsDialog(required: Boolean) {
        val view = layoutInflater.inflate(R.layout.dialog_settings, null)
        // 安全:已保存的 API Key 不回填明文(输入框为密码圆点样式),仅提示已保存
        val editKey = view.findViewById<EditText>(R.id.editApiKey)
        if (store.apiKey.isNotEmpty()) {
            editKey.hint = getString(R.string.hint_key_saved)
        }
        // 安全:业务空间 ID 同样不回填明文(密码圆点样式),仅提示已保存
        val editWs = view.findViewById<EditText>(R.id.editWorkspace)
        if (store.workspaceId.isNotEmpty()) {
            editWs.hint = getString(R.string.hint_ws_saved)
        }
        // 麦克风灵敏度:七档单选,按已存档位预选
        val radioMic = view.findViewById<RadioGroup>(R.id.radioMic)
        radioMic.check(micLevelToButtonId(store.micGainLevel))

        val dialog = AlertDialog.Builder(this)
            .setTitle(getString(if (required) R.string.settings_title_first else R.string.settings_title))
            .setView(view)
            .setPositiveButton(getString(R.string.btn_save), null)
            .setNegativeButton(getString(if (required) R.string.btn_exit else R.string.btn_cancel)) { _, _ ->
                if (required) finish()
            }
            .setCancelable(!required)
            .create()

        dialog.setOnShowListener {
            dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener {
                val keyInput = editKey.text.toString().trim()
                val wsInput = editWs.text.toString().trim()
                // 输入框为空且已有保存值 -> 沿用已存值(两个字段都支持"留空不改")
                val key = if (keyInput.isEmpty() && store.apiKey.isNotEmpty()) store.apiKey else keyInput
                val ws = if (wsInput.isEmpty() && store.workspaceId.isNotEmpty()) store.workspaceId else wsInput
                if (key.isEmpty()) {
                    Toast.makeText(this, getString(R.string.toast_need_key), Toast.LENGTH_SHORT).show()
                    return@setOnClickListener
                }
                if (!key.startsWith("sk-")) {
                    Toast.makeText(this, getString(R.string.toast_key_prefix), Toast.LENGTH_SHORT).show()
                    return@setOnClickListener
                }
                if (ws.isEmpty()) {
                    Toast.makeText(this, getString(R.string.toast_need_ws), Toast.LENGTH_SHORT).show()
                    return@setOnClickListener
                }
                store.save(key, ws)
                store.micGainLevel = buttonIdToMicLevel(radioMic.checkedRadioButtonId)
                dialog.dismiss()
                startConnection()
            }
        }
        dialog.show()
    }

    // ---------- 麦克风灵敏度档位 ↔ 按钮 id 映射 ----------

    private fun micLevelToButtonId(level: Int): Int = when (MicGain.normalize(level)) {
        2 -> R.id.radioMic2
        3 -> R.id.radioMic3
        4 -> R.id.radioMic4
        5 -> R.id.radioMic5
        6 -> R.id.radioMic6
        7 -> R.id.radioMic7
        else -> R.id.radioMic1
    }

    private fun buttonIdToMicLevel(id: Int): Int = when (id) {
        R.id.radioMic2 -> 2
        R.id.radioMic3 -> 3
        R.id.radioMic4 -> 4
        R.id.radioMic5 -> 5
        R.id.radioMic6 -> 6
        R.id.radioMic7 -> 7
        else -> MicGain.DEFAULT
    }

    // ---------- 使用说明 ----------

    /**
     * 使用说明全文走 res/raw 而非 string 资源:
     * AAPT 会把 string 里字面换行折叠成空格(实测已确认),长段说明会挤成一坨;
     * raw 文件原样打包,换行与缩进完整保留。
     */
    private fun loadHelpText(): String {
        val resId = if (store.appLanguage == LocaleHelper.LANG_ZH) R.raw.help_zh else R.raw.help_en
        val base = resources.openRawResource(resId).bufferedReader().use { it.readText() }
        // 体验版(trial,包内有内置凭据):帮助页最前面加"体验版说明"(分享给朋友的场景)
        return if (BuildConfig.BUILTIN_KEY_ENC.isNotEmpty()) trialNotice() + "\n\n" + base else base
    }

    /** 试用版说明(仅 trial 变体出现;official 版无内置凭据,不显示)。 */
    private fun trialNotice(): String =
        if (store.appLanguage == LocaleHelper.LANG_ZH) {
            "【试用版说明】\n" +
                "本安装包为作者提供的分享试用版,已内置体验额度——安装后无需填写任何凭据即可直接使用,费用由作者承担。\n" +
                "仅供个人体验:请勿公开传播,请勿用于商业用途。\n" +
                "如果试用后觉得好用,请注册你自己的阿里云百炼账号并填入自己的 API Key 继续使用" +
                "(开源版可在 GitHub 搜 qwen-voice-chat,作者 zxh-m4)。"
        } else {
            "[Trial notice]\n" +
                "This package is the author's trial build with bundled credentials — it works right away, " +
                "no setup needed; costs are covered by the author.\n" +
                "For personal trial only: please do not redistribute publicly or use it commercially.\n" +
                "If you find it useful, please register your own Alibaba Cloud Bailian account " +
                "and switch to your own API Key to keep using it " +
                "(open-source build: search \"qwen-voice-chat\" on GitHub by zxh-m4)."
        }

    private fun showHelpDialog() {
        val tv = TextView(this).apply {
            text = loadHelpText()
            setTextColor(0xFF37474F.toInt())
            textSize = 14f
            setLineSpacing(4f, 1f)
            setPadding(dp(20), dp(12), dp(20), dp(12))
        }
        val sv = ScrollView(this).apply { addView(tv) }
        AlertDialog.Builder(this)
            .setTitle(getString(R.string.help_title))
            .setView(sv)
            .setPositiveButton(getString(R.string.btn_ok), null)
            .show()
    }

    private var pendingAutoConnect = false

    /** 首次进入自动连接:权限已授予直接连;未授予先请求,授权成功后自动连;拒绝则等手动。 */
    private fun startIfMicGrantedOrRequest() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
            == PackageManager.PERMISSION_GRANTED
        ) {
            startConnection()
        } else {
            pendingAutoConnect = true
            requestMicIfNeeded()
        }
    }

    /**
     * 启动会话(点「连接」与设置对话框保存后统一走这里)。
     * 按钮文字从第一帧起与真实状态一致。
     */
    private fun startConnection() {
        if (!store.credentials.isComplete) {
            showSettingsDialog(required = true)
            return
        }
        if (running) manager.stop() // 通话中改凭据重连:先断旧会话
        errText.text = ""
        manager.start(SessionPresets.byKey(presetKeyAt(spinner.selectedItemPosition)))
        running = true
        btnToggle.text = getString(R.string.btn_disconnect)
        usageHandler.removeCallbacks(usageTick) // 无论从哪条路径进来都恰好一个费用刷新器
        usageHandler.post(usageTick)
        scheduleConnectTimeout()
        requestMicIfNeeded() // 已授权时是空操作
    }

    private fun requestMicIfNeeded() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
            != PackageManager.PERMISSION_GRANTED
        ) {
            ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.RECORD_AUDIO), REQ_PERM)
        }
    }

    private fun toggle() {
        if (running) {
            manager.stop()
            running = false
            usageHandler.removeCallbacks(usageTick)
            usageText.text = ""
            btnToggle.text = getString(R.string.btn_connect)
        } else {
            startConnection()
        }
    }

    private fun presetKeyAt(pos: Int): String =
        SessionPresets.ALL.getOrElse(pos) { SessionPresets.default() }.key

    /** 25 秒仍未就绪:提示用户,便于反馈(接口正常时通常 2~5 秒内就绪)。 */
    private fun scheduleConnectTimeout() {
        errText.postDelayed({
            if (running && stateText.text == getString(R.string.state_connecting)) {
                errText.setTextColor(ContextCompat.getColor(this, R.color.err_text))
                errText.text = getString(R.string.err_connect_timeout)
            }
        }, 25_000)
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == REQ_PERM) {
            if (grantResults.firstOrNull() == PackageManager.PERMISSION_GRANTED) {
                if (pendingAutoConnect) {
                    pendingAutoConnect = false
                    startConnection() // 授权完成,补上自动连接
                }
            } else {
                pendingAutoConnect = false
                errText.setTextColor(ContextCompat.getColor(this, R.color.err_text))
                errText.text = getString(R.string.err_no_mic)
                btnToggle.text = getString(R.string.btn_connect)
            }
        }
    }

    // ---------- ChatListener(SDK 线程回调,统一 post 主线程) ----------

    private fun ui(block: () -> Unit) = runOnUiThread(block)

    override fun onState(state: String) = ui {
        val (label, dot) = when (state) {
            "connecting" -> getString(R.string.state_connecting) to R.drawable.dot_idle
            "ready" -> getString(R.string.state_ready) to R.drawable.dot_ready
            "speaking" -> getString(R.string.state_speaking) to R.drawable.dot_speaking
            "interrupted" -> getString(R.string.state_interrupted) to R.drawable.dot_ready
            else -> getString(R.string.state_closed) to R.drawable.dot_idle
        }
        stateText.text = label
        stateDot.setBackgroundResource(dot)
        if (state != "connecting") closeAiLine() // 任何状态转换都封行,打断后的新回复开新气泡
        if (state == "closed" && running) {
            running = false
            btnToggle.text = getString(R.string.btn_connect)
        }
    }

    override fun onUserTranscript(text: String) = ui {
        closeAiLine()
        addBubble("$text", isUser = true)
    }

    override fun onAssistantText(delta: String) = ui {
        var bubble = currentAiBubble
        if (bubble == null) {
            bubble = addBubble(getString(R.string.ai_prefix), isUser = false)
            currentAiBubble = bubble
        }
        bubble.append(delta)
        scroll.fullScroll(View.FOCUS_DOWN)
    }

    override fun onError(code: String, message: String) = ui {
        // 技术细节只进日志。屏幕只显示人话 ——
        // 服务端返回的原始报错可能带内部信息(如业务空间 ID),被人瞥一眼不合适。
        AppLog.w("错误详情 [$code] $message")
        errText.setTextColor(ContextCompat.getColor(this, R.color.err_text))
        errText.text = friendlyError(code, message)
    }

    /**
     * 把错误翻成用户看得懂的一句话。
     * 我们自己抛的错误(start / audio)其 message 本身就是给用户的指导语,原样显示;
     * 其余(鉴权失败、连接失败、引擎报错等)只显示分类提示,细节去日志里看。
     */
    private fun friendlyError(code: String, message: String): String {
        if (code == "start" || code == "audio") return message
        val c = code.lowercase()
        return when {
            c.contains("401") || c.contains("403") || c.contains("auth") || c.contains("apikey") ->
                getString(R.string.err_auth)
            c.contains("timeout") -> getString(R.string.err_timeout)
            c.contains("audio") -> getString(R.string.err_audio)
            c.contains("engine") -> getString(R.string.err_engine)
            c.contains("token") || c.contains("connect") || c.contains("start") ->
                getString(R.string.err_network)
            else -> getString(R.string.err_generic)
        }
    }

    override fun onDebug(message: String) {
        // 诊断只写日志文件(Manager 层 AppLog 已记录),不再显示在界面上
    }

    // ---------- 气泡 ----------

    private fun addBubble(text: String, isUser: Boolean): TextView {
        val tv = TextView(this).apply {
            this.text = text
            textSize = 15f
            setPadding(dp(14), dp(9), dp(14), dp(9))
            setTextColor(if (isUser) 0xFFFFFFFF.toInt() else 0xFF263238.toInt())
            background = ContextCompat.getDrawable(this@MainActivity, if (isUser) R.drawable.bg_bubble_user else R.drawable.bg_bubble_ai)
            setLineSpacing(3f, 1f)
        }
        val lp = LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.WRAP_CONTENT,
            LinearLayout.LayoutParams.WRAP_CONTENT,
        ).apply {
            topMargin = dp(8)
            gravity = if (isUser) Gravity.END else Gravity.START
        }
        bubbleContainer.addView(tv, lp)
        scroll.post { scroll.fullScroll(View.FOCUS_DOWN) }
        return tv
    }

    private fun closeAiLine() {
        currentAiBubble = null
    }

    private fun sysLine(text: String) {
        val tv = TextView(this).apply {
            this.text = "— $text —"
            textSize = 12f
            setTextColor(0xFF90A4AE.toInt())
            gravity = Gravity.CENTER
        }
        val lp = LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT,
            LinearLayout.LayoutParams.WRAP_CONTENT,
        ).apply { topMargin = dp(10) }
        bubbleContainer.addView(tv, lp)
        scroll.post { scroll.fullScroll(View.FOCUS_DOWN) }
    }

    private fun dp(v: Int): Int = (v * resources.displayMetrics.density).toInt()

    override fun onDestroy() {
        usageHandler.removeCallbacks(usageTick)
        if (this::manager.isInitialized && running) manager.stop()
        super.onDestroy()
    }
}
