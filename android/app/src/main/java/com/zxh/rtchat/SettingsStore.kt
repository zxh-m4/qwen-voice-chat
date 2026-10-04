package com.zxh.rtchat

import android.content.Context

/**
 * 凭据与偏好本地存储(SharedPreferences,app 私有目录)。
 * 用户首次启动时输入自己的 API Key 与业务空间 ID,不在安装包里携带任何凭据。
 *
 * 两类数据分开处理:
 * - 凭据(api_key / workspace_id)经 [SecureStore] 加密(AES + 系统 KeyStore,API 23+)
 * - 界面语言等偏好明文即可(泄露了也只是界面语言)
 */
class SettingsStore(context: Context) {

    private val prefs = context.getSharedPreferences("rtchat_settings", Context.MODE_PRIVATE)

    data class Credentials(val apiKey: String, val workspaceId: String) {
        val isComplete: Boolean get() = apiKey.isNotBlank() && workspaceId.isNotBlank()
    }

    var apiKey: String
        get() = readCred(KEY_API)
        set(value) = writeCred(KEY_API, value)

    var workspaceId: String
        get() = readCred(KEY_WS)
        set(value) = writeCred(KEY_WS, value)

    /** 界面语言("en" / "zh"),默认英文。修改后需 recreate() 才生效。 */
    var appLanguage: String
        get() = LocaleHelper.normalize(prefs.getString("app_lang", LocaleHelper.DEFAULT))
        set(value) = prefs.edit().putString("app_lang", LocaleHelper.normalize(value)).apply()

    val credentials: Credentials
        get() {
            val k = apiKey
            val w = workspaceId
            if (k.isNotEmpty() && w.isNotEmpty()) return Credentials(k, w)
            // 试用版:回退到内置凭据(加密存储;正式版为空串->仍走首次配置弹窗)
            val builtinKey = SecretVault.reveal(BuildConfig.BUILTIN_KEY_ENC)
            val builtinWs = SecretVault.reveal(BuildConfig.BUILTIN_WS_ENC)
            return Credentials(k.ifEmpty { builtinKey }, w.ifEmpty { builtinWs })
        }

    fun save(apiKey: String, workspaceId: String) {
        writeCred(KEY_API, apiKey)
        writeCred(KEY_WS, workspaceId)
    }

    /** 供界面提示:凭据当前是否真的被加密保护着。 */
    fun isCredentialProtected(): Boolean = SecureStore.isProtected()

    // ---------- 凭据读写(带旧版明文自动升级) ----------

    private fun readCred(key: String): String {
        val stored = prefs.getString(key, "") ?: ""
        val plain = SecureStore.decrypt(stored)
        // 旧版本存的是明文:读出来后顺手加密写回,用户无需重新填写
        if (plain.isNotEmpty() && !SecureStore.isEncrypted(stored)) {
            AppLog.w("检测到旧版明文凭据,已自动升级为加密存储")
            prefs.edit().putString(key, SecureStore.encrypt(plain)).apply()
        }
        return plain
    }

    private fun writeCred(key: String, value: String) {
        prefs.edit().putString(key, SecureStore.encrypt(value.trim())).apply()
    }

    private companion object {
        const val KEY_API = "api_key"
        const val KEY_WS = "workspace_id"
    }
}
