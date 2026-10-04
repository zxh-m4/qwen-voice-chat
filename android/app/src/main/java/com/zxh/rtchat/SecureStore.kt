package com.zxh.rtchat

import android.os.Build
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/**
 * 凭据加密存储（本文件为自行实现，未引入任何第三方加密库）。
 *
 * Android 6.0(API 23) 起可以把 AES 密钥放进**系统 KeyStore**：密钥由系统保管，
 * 应用自己都读不到明文。也就是说，即便别人拿到了 SharedPreferences 文件
 * （root 设备 / USB 调试导出 / 某些换机备份软件），也解不出 API Key。
 *
 * API 21-22 的 KeyStore 不支持这种用法，退回明文存储（这批设备已极罕见）。
 *
 * 存储格式：`enc1:<Base64(iv)>:<Base64(密文)>`。
 * 若读到的值没有 `enc1:` 前缀，说明是旧版本存的明文，调用方负责顺手升级。
 */
object SecureStore {

    private const val ANDROID_KEYSTORE = "AndroidKeyStore"
    private const val KEY_ALIAS = "rtchat_cred_aes"
    private const val PREFIX = "enc1:"
    private const val TRANSFORM = "AES/GCM/NoPadding"
    private const val GCM_TAG_BITS = 128

    private fun supported(): Boolean = Build.VERSION.SDK_INT >= Build.VERSION_CODES.M

    /** 存储值是否已是密文。 */
    fun isEncrypted(stored: String): Boolean = stored.startsWith(PREFIX)

    fun encrypt(plain: String): String {
        if (plain.isEmpty()) return ""
        if (!supported()) return plain
        return try {
            val cipher = Cipher.getInstance(TRANSFORM)
            cipher.init(Cipher.ENCRYPT_MODE, createKey())
            val cipherText = cipher.doFinal(plain.toByteArray(Charsets.UTF_8))
            PREFIX +
                Base64.encodeToString(cipher.iv, Base64.NO_WRAP) + ":" +
                Base64.encodeToString(cipherText, Base64.NO_WRAP)
        } catch (e: Exception) {
            // 加密异常时退回明文，优先保证「能正常对话」而不是崩溃或丢凭据。
            // AppLog 会在调用方记录这件事。
            plain
        }
    }

    /**
     * 解密。非密文（旧版本明文）原样返回，由调用方触发升级。
     * 密钥失效（换机 / 系统安全更新清 Keystore）时返回空串，界面会引导重新填写。
     */
    fun decrypt(stored: String): String {
        if (stored.isEmpty()) return ""
        if (!isEncrypted(stored)) return stored
        if (!supported()) return ""
        return try {
            val parts = stored.removePrefix(PREFIX).split(":")
            if (parts.size != 2) return ""
            val key = existingKey() ?: return ""
            val cipher = Cipher.getInstance(TRANSFORM)
            cipher.init(
                Cipher.DECRYPT_MODE, key,
                GCMParameterSpec(GCM_TAG_BITS, Base64.decode(parts[0], Base64.NO_WRAP))
            )
            String(cipher.doFinal(Base64.decode(parts[1], Base64.NO_WRAP)), Charsets.UTF_8)
        } catch (e: Exception) {
            ""
        }
    }

    /** 密钥是否已就绪（用于界面提示「凭据是否处于加密保护下」）。 */
    fun isProtected(): Boolean = supported() && existingKey() != null

    private fun existingKey(): SecretKey? = try {
        val store = KeyStore.getInstance(ANDROID_KEYSTORE).apply { load(null) }
        (store.getEntry(KEY_ALIAS, null) as? KeyStore.SecretKeyEntry)?.secretKey
    } catch (e: Exception) {
        null
    }

    private fun createKey(): SecretKey {
        existingKey()?.let { return it }
        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, ANDROID_KEYSTORE)
        generator.init(
            KeyGenParameterSpec.Builder(
                KEY_ALIAS,
                KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT
            )
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                .build()
        )
        return generator.generateKey()
    }
}
