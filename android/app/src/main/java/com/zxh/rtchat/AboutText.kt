package com.zxh.rtchat

/**
 * 「关于」页的文本层。
 *
 * 刻意做成不依赖 Android 的纯函数:备案号、隐私政策、开源声明都是应用商店要逐字核对的合规文案,
 * 能用单测锁住就比截图可靠(AboutTextTest 会核对隐私政策要点是否齐全、并防止帮助页重新长出重复段落)。
 */
object AboutText {

    /** 工信部备案查询系统:进去后选「APP」,输入备案号即可核验真伪。 */
    const val BEIAN_URL = "https://beian.miit.gov.cn"

    /** 与帮助页署名同一人名,版权行使用。 */
    const val AUTHOR = "笑晗"

    fun versionLine(zh: Boolean, versionName: String): String =
        if (zh) "版本:$versionName" else "Version: $versionName"

    /** 备案号未填(空串/纯空白)时返回空串,整行不占位 —— 与帮助页的 BEIAN_NO 约定一致。 */
    fun beianLine(zh: Boolean, beianNo: String): String =
        if (beianNo.isBlank()) ""
        else if (zh) "备案号:$beianNo" else "ICP filing No.: $beianNo"

    /** 隐私政策正文。自 2026-10-13 起这里是唯一真源 —— 帮助页不再重复该段。 */
    fun privacyNotice(zh: Boolean): String = if (zh) PRIVACY_ZH else PRIVACY_EN

    /** 开源软件声明:本应用自身代码 + 开源第三方库 + 闭源第三方组件,分三类列清。 */
    fun ossNotice(zh: Boolean): String = if (zh) OSS_ZH else OSS_EN

    fun copyrightLine(zh: Boolean): String =
        if (zh) "Copyright © 2026 $AUTHOR 保留所有权利。"
        else "Copyright © 2026 $AUTHOR. All rights reserved."

    private val PRIVACY_ZH = listOf(
        "· 你的语音会实时上传至阿里云百炼进行识别与合成,用于生成对话回复;",
        "· 转写文本只在屏幕上显示,本应用不保存任何对话内容;",
        "· 你的 API Key 与业务空间 ID 仅保存在本机(已加密),不会上传到任何其他服务器;",
        "· 运行日志只记录事件类型与诊断信息,不记录任何对话内容。",
    ).joinToString("\n")

    private val PRIVACY_EN = listOf(
        "- Your voice is streamed to Alibaba Cloud Bailian for recognition and synthesis.",
        "- Transcripts are shown on screen only; this app stores no conversation content.",
        "- Your API Key / Workspace ID stay on this device (encrypted) and are never sent anywhere else.",
        "- The run log records event types and diagnostics only — never your conversation content.",
    ).joinToString("\n")

    private val OSS_ZH = listOf(
        "【本应用代码】",
        "· 实时外语对话(qwen-voice-chat)以 MIT 许可开源,",
        "  仓库地址:GitHub zxh-m4/qwen-voice-chat。",
        "",
        "【开源第三方库】",
        "· AndroidX Core(ktx)1.13.1 — Apache-2.0",
        "· AndroidX AppCompat 1.7.0 — Apache-2.0",
        "· Kotlin 标准库 — Apache-2.0",
        "· JUnit 4.13.2 — EPL-1.0(仅用于单元测试,不随应用分发)",
        "",
        "【闭源第三方组件】",
        "· 阿里云百炼 AOQ Client SDK(AoqClientSdk-release.aar)",
        "  与 libPluginOpus.so:由阿里云官方分发,遵循其自身许可条款,",
        "  本应用不对其再分发,仓库中亦不包含其二进制文件。",
        "",
        "上述各组件的完整许可条款,以其原作者发布的 LICENSE 文本为准。",
    ).joinToString("\n")

    private val OSS_EN = listOf(
        "[This app]",
        "· Realtime Voice Chat (qwen-voice-chat) is open-sourced under the MIT license;",
        "  repository: GitHub zxh-m4/qwen-voice-chat.",
        "",
        "[Open-source third-party libraries]",
        "· AndroidX Core (ktx) 1.13.1 — Apache-2.0",
        "· AndroidX AppCompat 1.7.0 — Apache-2.0",
        "· Kotlin standard library — Apache-2.0",
        "· JUnit 4.13.2 — EPL-1.0 (unit tests only, not distributed with the app)",
        "",
        "[Closed-source third-party components]",
        "· Alibaba Cloud Bailian AOQ Client SDK (AoqClientSdk-release.aar) and",
        "  libPluginOpus.so: distributed by Alibaba Cloud under its own terms;",
        "  this app does not redistribute them, and the repository contains no binaries.",
        "",
        "Full license texts are those published by each component's original author.",
    ).joinToString("\n")
}
