package com.zxh.rtchat

import android.content.Context
import android.content.res.Configuration
import android.os.Build
import android.os.LocaleList
import java.util.Locale

/**
 * 应用内语言切换(强制指定,不跟随系统语言)。
 *
 * 实现方式:包装 Context 的 Configuration,在 Activity.attachBaseContext 里生效。
 * 相比 AppCompatDelegate.setApplicationLocales 的好处是零额外依赖(appcompat 已引入,
 * 但 delegate 方案在部分国产 ROM 上生效不稳定),且切换后只需 recreate() 立即生效。
 *
 * 默认语言 = 中文:res/values 为中文,res/values-en 为英文。
 */
object LocaleHelper {

    const val LANG_EN = "en"
    const val LANG_ZH = "zh"

    /** 支持的语言,顺序即选择弹窗里的顺序(中文在前)。 */
    val SUPPORTED = listOf(LANG_ZH, LANG_EN)

    /** 未存储过时的默认语言:中文(res/values 为中文,res/values-en 为英文)。 */
    const val DEFAULT = LANG_ZH

    /** 用指定语言包装 Context(在 attachBaseContext 中调用)。 */
    fun wrap(context: Context, lang: String): Context {
        val locale = Locale(lang)
        Locale.setDefault(locale)
        val config = Configuration(context.resources.configuration)
        config.setLocale(locale)
        // API 24+ 还需同步 LocaleList,否则部分系统组件(如拼写检查)仍按旧 locale 走
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            config.setLocales(LocaleList(locale))
        }
        return context.createConfigurationContext(config)
    }

    /** 语言按钮上的短标签资源:EN / 中。返回 resId,由调用方 getString 取,避免硬编码。 */
    fun shortLabelRes(lang: String): Int =
        if (lang == LANG_ZH) R.string.lang_btn_zh else R.string.lang_btn_en

    /** 归一化:未知值回落到默认(中文)。 */
    fun normalize(lang: String?): String =
        if (lang in SUPPORTED) lang!! else DEFAULT
}
