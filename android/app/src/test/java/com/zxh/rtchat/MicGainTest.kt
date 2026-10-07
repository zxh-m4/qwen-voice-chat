package com.zxh.rtchat

import org.junit.Assert.assertEquals
import org.junit.Test

/** v1.5「麦克风灵敏度」逻辑的单测(纯逻辑,不依赖 Android)。 */
class MicGainTest {

    private fun readInt16(b: ByteArray, i: Int): Int =
        (b[i].toInt() and 0xFF) or (b[i + 1].toInt() shl 8)

    @Test
    fun defaultIsOriginal() {
        assertEquals(1, MicGain.DEFAULT)
        assertEquals(1.0f, MicGain.factor(MicGain.DEFAULT), 1e-6f)
    }

    @Test
    fun sevenLevelsMapToDecibels() {
        assertEquals(0.5011872f, MicGain.factor(2), 1e-4f)  // -6 dB
        assertEquals(0.2511886f, MicGain.factor(3), 1e-4f)  // -12 dB
        assertEquals(0.1258925f, MicGain.factor(4), 1e-4f)  // -18 dB
        assertEquals(0.0630957f, MicGain.factor(5), 1e-4f)  // -24 dB
        assertEquals(0.0251189f, MicGain.factor(6), 1e-4f)  // -32 dB
        assertEquals(0.01f, MicGain.factor(7), 1e-6f)       // -40 dB
    }

    @Test
    fun invalidFallsBackToDefault() {
        for (bad in intArrayOf(0, 8, -1, 99)) {
            assertEquals(MicGain.DEFAULT, MicGain.normalize(bad))
        }
        assertEquals(1.0f, MicGain.factor(0), 1e-6f)
    }

    @Test
    fun scalesLittleEndianInt16() {
        // 1000 = 0x03E8, -1000 = 0xFC18
        val data = byteArrayOf(0xE8.toByte(), 0x03, 0x18, 0xFC.toByte())
        MicGain.applyInPlace(data, data.size, 0.5f)
        assertEquals(500, readInt16(data, 0))
        assertEquals(-500, readInt16(data, 2))
    }

    @Test
    fun zeroDbLeavesBytesUntouched() {
        val data = byteArrayOf(0xE8.toByte(), 0x03)
        MicGain.applyInPlace(data, data.size, 1.0f)
        assertEquals(1000, readInt16(data, 0))
    }

    @Test
    fun clipsOnOverflow() {
        // 32767 = 0xFF7F,理论上 -0dB 附近不冲突;用系数 0.99 验证不溢出
        val max = byteArrayOf(0xFF.toByte(), 0x7F)
        MicGain.applyInPlace(max, 2, 0.99f)
        assertEquals(32439, readInt16(max, 0))
    }

    @Test
    fun onlyProcessesGivenSize() {
        // size=2 时后面的字节不得被改动
        val data = byteArrayOf(0xE8.toByte(), 0x03, 0xE8.toByte(), 0x03)
        MicGain.applyInPlace(data, 2, 0.5f)
        assertEquals(500, readInt16(data, 0))
        assertEquals(1000, readInt16(data, 2))
    }
}
