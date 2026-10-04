package com.zxh.rtchat

import android.util.Base64

/**
 * 内置凭据的轻量保护(试用版专用):异或PAD + Base64 + 倒序。
 *
 * 说明:客户端内置密钥在原理上无法做到密码学意义的保密(解密逻辑同在应用内),
 * 本方案的目标是——不让明文出现在 APK 字符串表中,挡住常规反编译随手提取;
 * 正式版不含任何内置凭据(此功能为空串直接返回空)。
 */
object SecretVault {

    private val PAD = byteArrayOf(
        0x5D, 0x2A, 0x9F.toByte(), 0x11, 0xE3.toByte(), 0x47, 0x08, 0xB6.toByte(),
        0x74, 0xC1.toByte(), 0x3E, 0x82.toByte(), 0x55, 0xDA.toByte(), 0x6C, 0x27,
    )

    fun reveal(encoded: String): String {
        if (encoded.isEmpty()) return ""
        return try {
            val raw = Base64.decode(encoded.reversed(), Base64.DEFAULT)
            val out = ByteArray(raw.size)
            for (i in raw.indices) {
                out[i] = ((raw[i].toInt() and 0xFF) xor (PAD[i % PAD.size].toInt() and 0xFF)).toByte()
            }
            String(out, Charsets.UTF_8)
        } catch (e: Exception) {
            ""
        }
    }
}
