package com.zxh.rtchat

import kotlin.math.sqrt

/**
 * 静音门:持续静音超过滞回时长后停止上行麦克风音频,把挂机期间的输入 token 降到零。
 *
 * 逐行等价移植自 `desktop/rtchat/gate.py`(PC 版已在真机验证过),
 * 滞回逻辑保持一致:能量掉到阈值以下后,仍继续发送 gateMs 的静音
 * (保证服务端 VAD 的断句计时拿到连续时间轴),连续静音超时才停发;
 * 一旦检测到声音立即恢复。
 *
 * 说明:这是「省输入 token」,不是回声消除——不阻断下行,
 * 全双工插话打断不受影响。
 */
class SilenceGate(
    private val thresholdRms: Int = DEFAULT_THRESHOLD_RMS,
    private val gateMs: Int = DEFAULT_GATE_MS,
) {
    companion object {
        /** 与 PC 版 config.json 的 silence_threshold_rms 一致(该值按 PC 麦克风实测调过)。 */
        const val DEFAULT_THRESHOLD_RMS = 600

        /** 与 PC 版 silence_gate_ms 一致。 */
        const val DEFAULT_GATE_MS = 1500

        /**
         * 16bit 单声道 PCM 的 RMS 幅度。
         * 等价 PC 版的 numpy 实现 np.sqrt(np.mean(a*a));小端字节序( '&' 与 WebRTC/PortAudio 一致)。
         */
        fun rms(pcm: ByteArray): Double {
            if (pcm.isEmpty()) return 0.0
            var sum = 0.0
            var n = 0
            var i = 0
            while (i + 1 < pcm.size) {
                // 小端:低位在前
                val v = ((pcm[i + 1].toInt() shl 8) or (pcm[i].toInt() and 0xFF)).toShort()
                sum += v.toDouble() * v.toDouble()
                n++
                i += 2
            }
            return if (n == 0) 0.0 else sqrt(sum / n)
        }
    }

    private val lock = Any()
    private var active = false // 初始静音不发,来声音才开(与 PC 版一致)
    private var silentMs = 0.0

    @Volatile var framesIn: Long = 0
        private set
    @Volatile var framesSent: Long = 0
        private set

    /** 累计「实际发出」的音频时长(秒),供费用估算使用。 */
    @Volatile var sentSec: Double = 0.0
        private set

    fun reset() {
        synchronized(lock) {
            active = false
            silentMs = 0.0
            framesIn = 0
            framesSent = 0
            sentSec = 0.0
        }
    }

    /**
     * 喂一帧麦克风 PCM16 数据,返回这一帧是否应当继续上行。
     * @param frameMs 该帧真实时长(毫秒),由调用方按 dataSize/samplesPerSec 算出,不在内部假设。
     */
    fun feed(pcm: ByteArray, frameMs: Double): Boolean {
        synchronized(lock) {
            framesIn++
            if (rms(pcm) >= thresholdRms.toDouble()) {
                active = true
                silentMs = 0.0
                framesSent++
                sentSec += frameMs / 1000.0
                return true
            }
            // 低于阈值:未激活态直接丢;激活态进入滞回计时
            if (!active) return false
            if (silentMs >= gateMs.toDouble()) {
                active = false
                return false
            }
            silentMs += frameMs
            framesSent++
            sentSec += frameMs / 1000.0
            return true
        }
    }

    /** 实际发送帧占比,用于在日志里判断省了多少。 */
    val sentRatio: Double
        get() = synchronized(lock) { if (framesIn == 0L) 0.0 else framesSent.toDouble() / framesIn }
}
