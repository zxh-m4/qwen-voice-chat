package com.zxh.rtchat

/**
 * 「麦克风灵敏度」:档位 → 上传音频的整体增益(端侧压低;配合"靠近麦克风 + 大声说")。
 *
 * 1 = 0 dB(默认,原样)… 7 = -40 dB;系数 = 10^(-dB/20)。
 * 与 PC 版 desktop/rtchat/config.py 的 MIC_GAIN_LEVELS 保持同一套档位。
 * 纯逻辑(不依赖 Android),单测见 MicGainTest。
 */
object MicGain {

    const val DEFAULT = 1

    private val FACTORS = mapOf(
        1 to 1.0f,
        2 to 0.5011872f,  // -6 dB
        3 to 0.2511886f,  // -12 dB
        4 to 0.1258925f,  // -18 dB
        5 to 0.0630957f,  // -24 dB
        6 to 0.0251189f,  // -32 dB
        7 to 0.01f,       // -40 dB
    )

    /** 非法值(越界/未知)回落到默认档(0 dB)。 */
    fun normalize(level: Int): Int = if (FACTORS.containsKey(level)) level else DEFAULT

    /** 档位 → 增益系数(1.0 = 原样)。 */
    fun factor(level: Int): Float = FACTORS.getValue(normalize(level))

    /**
     * 就地缩放 PCM16 小端音频(仅处理前 [size] 字节)。
     * 增益 >= 1 时不做任何事(零开销,保证默认档行为与旧版完全一致)。
     */
    fun applyInPlace(data: ByteArray, size: Int, gain: Float) {
        if (gain >= 1.0f) return
        var i = 0
        while (i + 1 < size) {
            val lo = data[i].toInt() and 0xFF
            val hi = data[i + 1].toInt()          // 有符号高字节,负数时自动带符号位
            val v = (hi shl 8) or lo              // int16 小端
            val s = (v * gain).toInt().coerceIn(-32768, 32767)
            data[i] = (s and 0xFF).toByte()
            data[i + 1] = ((s shr 8) and 0xFF).toByte()
            i += 2
        }
    }
}
