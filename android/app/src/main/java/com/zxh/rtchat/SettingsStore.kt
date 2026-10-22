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

    data class Credentials(val apiKey: String, val workspaceId: String, val region: String) {
        val isComplete: Boolean get() = apiKey.isNotBlank() && workspaceId.isNotBlank()
    }

    var apiKey: String
        get() = readCred(KEY_API)
        set(value) = writeCred(KEY_API, value)

    var workspaceId: String
        get() = readCred(KEY_WS)
        set(value) = writeCred(KEY_WS, value)

    /** 接入地域:北京/新加坡。API Key 与业务空间按地域隔离,切换后需填对应地域的凭据。 */
    var region: String
        get() = prefs.getString("region", REGION_BEIJING)
            ?.takeIf { it == REGION_SINGAPORE } ?: REGION_BEIJING
        set(value) {
            prefs.edit().putString(
                "region",
                if (value == REGION_SINGAPORE) REGION_SINGAPORE else REGION_BEIJING,
            ).apply()
        }

    /** 界面语言("en" / "zh"),默认中文。修改后需 recreate() 才生效。 */
    var appLanguage: String
        get() = LocaleHelper.normalize(prefs.getString("app_lang", LocaleHelper.DEFAULT))
        set(value) = prefs.edit().putString("app_lang", LocaleHelper.normalize(value)).apply()

    /** 「麦克风灵敏度」档位(1-7):1=0dB 原样(默认)… 7=-40dB。修改后下次连接生效。 */
    var micGainLevel: Int
        get() = MicGain.normalize(prefs.getInt("mic_gain_level", MicGain.DEFAULT))
        set(value) = prefs.edit().putInt("mic_gain_level", MicGain.normalize(value)).apply()

    /**
     * 使用模式([SessionPresets.MODE_TEACHER] / [SessionPresets.MODE_RESTATE])。
     * 修改后要重建界面(角色下拉的内容随模式变),见 MainActivity 设置保存处。
     */
    var mode: String
        get() = prefs.getString("mode", SessionPresets.MODE_TEACHER)
            ?.takeIf { it == SessionPresets.MODE_RESTATE } ?: SessionPresets.MODE_TEACHER
        set(value) {
            prefs.edit().putString(
                "mode",
                if (value == SessionPresets.MODE_RESTATE) SessionPresets.MODE_RESTATE else SessionPresets.MODE_TEACHER,
            ).apply()
        }

    /** 「自定义语言」的名称(角色选「自定义语言」时生效)。只是语言名,明文即可。 */
    var customLanguage: String
        get() = prefs.getString("custom_language", "") ?: ""
        set(value) = prefs.edit().putString("custom_language", SessionPresets.normalizeLanguage(value)).apply()

    /**
     * 上次选中的角色 key。自定义语言必须靠它才能在重启后继续生效
     * (否则每次启动都回到英语老师,用户填过的语言名就白填了)。
     */
    var presetKey: String
        get() = prefs.getString("preset_key", "") ?: ""
        set(value) = prefs.edit().putString("preset_key", value).apply()

    val credentials: Credentials
        get() {
            val k = apiKey
            val w = workspaceId
            if (k.isNotEmpty() && w.isNotEmpty()) return Credentials(k, w, region)
            // 试用版:回退到内置凭据(加密存储;正式版为空串->仍走首次配置弹窗)
            val builtinKey = SecretVault.reveal(BuildConfig.BUILTIN_KEY_ENC)
            val builtinWs = SecretVault.reveal(BuildConfig.BUILTIN_WS_ENC)
            return Credentials(k.ifEmpty { builtinKey }, w.ifEmpty { builtinWs }, region)
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

    companion object {
        private const val KEY_API = "api_key"
        private const val KEY_WS = "workspace_id"
        const val REGION_BEIJING = "beijing"
        const val REGION_SINGAPORE = "singapore"
    }
}
