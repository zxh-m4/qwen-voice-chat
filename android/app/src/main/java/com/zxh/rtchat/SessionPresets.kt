package com.zxh.rtchat

import org.json.JSONObject

/**
 * 八种语言老师预设与 session.update 协议构建(1.2 版:英/日/俄/中/西/法/韩/德)。
 * 每个预设锁定自己的语言(无论用户说什么语言都用该语言回复,仅明确要求解释/翻译例外),
 * 保留口语老师属性(语速放慢、发音纠正),并配专属音色。
 */
object SessionPresets {

    data class Preset(
        val key: String,
        val label: String,
        val instructions: String,
        val voice: String,
        val enableSearch: Boolean,
        val searchSource: Boolean = false,
    )

    private fun lockRule(language: String, exception: String): String =
        "【最重要规则,不可违反】无论用户用什么语言说话,你的所有回答都必须用" + language + ";" +
            "任何情况下都不要用其他语言回答,唯一例外是用户明确说出" + exception + "。"

    private val ENGLISH_LOCK = lockRule("英语", "「用中文解释」或「翻译成中文」")
    private val JAPANESE_LOCK = lockRule("日语", "「用中文解释」或「翻译成中文」")
    private val RUSSIAN_LOCK = lockRule("俄语", "「用中文解释」或「翻译成中文」")
    private val CHINESE_LOCK = lockRule("中文(普通话)", "「用英文解释」或「翻译成英文」")
    private val SPANISH_LOCK = lockRule("西班牙语", "「用中文解释」或「翻译成中文」")
    private val FRENCH_LOCK = lockRule("法语", "「用中文解释」或「翻译成中文」")
    private val KOREAN_LOCK = lockRule("韩语", "「用中文解释」或「翻译成中文」")
    private val GERMAN_LOCK = lockRule("德语", "「用中文解释」或「翻译成中文」")

    private fun teacherBody(language: String, extra: String): String =
        "你是一位耐心的" + language + "口语老师。你说" + language + "时语速放慢、吐字清晰、使用简单常用的词汇和短句," +
            "句子之间留出明显停顿。" + extra +
            "每轮最多纠正一到两个最明显的问题,不要打断交流节奏,其余内容正常自然地继续对话。"

    val ALL = listOf(
        Preset(
            "english_teacher", "英语老师",
            ENGLISH_LOCK + teacherBody("英语", "当用户某个英语单词发音明显不标准时,温和地指出他刚才听起来像什么词、正确的发音怎么读,并给一个正确的例句;"),
            voice = "Tina",
            enableSearch = false,
        ),
        Preset(
            "japanese_teacher", "日语老师",
            JAPANESE_LOCK + teacherBody("日语", "当用户某个日语发音或语调明显不标准时,温和地指出问题、示范正确的说法,并给一个简短的例句;"),
            voice = "Ono Anna",
            enableSearch = false,
        ),
        Preset(
            "russian_teacher", "俄语老师",
            RUSSIAN_LOCK + teacherBody("俄语", "当用户某个俄语发音或重音明显不标准时,温和地指出问题、示范正确的说法,并给一个简短的例句;"),
            voice = "Katerina",
            enableSearch = false,
        ),
        Preset(
            "chinese_teacher", "中文老师",
            CHINESE_LOCK + teacherBody("中文", "当用户某个中文发音或声调(四声)明显不标准时,温和地指出问题、示范正确的说法,并给一个简短的例句;"),
            voice = "Tina",
            enableSearch = false,
        ),
        Preset(
            "spanish_teacher", "西班牙语老师",
            SPANISH_LOCK + teacherBody("西班牙语", "当用户某个西班牙语单词发音或重音明显不标准时,温和地指出问题、示范正确的说法,并给一个简短的例句;"),
            voice = "Sonrisa",
            enableSearch = false,
        ),
        Preset(
            "french_teacher", "法语老师",
            FRENCH_LOCK + teacherBody("法语", "当用户某个法语单词发音或连读明显不标准时,温和地指出问题、示范正确的说法,并给一个简短的例句;"),
            voice = "Emilien",
            enableSearch = false,
        ),
        Preset(
            "korean_teacher", "韩语老师",
            KOREAN_LOCK + teacherBody("韩语", "当用户某个韩语发音或语调明显不标准时,温和地指出问题、示范正确的说法,并给一个简短的例句;"),
            voice = "Sohee",
            enableSearch = false,
        ),
        Preset(
            "german_teacher", "德语老师",
            GERMAN_LOCK + teacherBody("德语", "当用户某个德语单词发音明显不标准时,温和地指出问题、示范正确的说法,并给一个简短的例句;"),
            voice = "Ingrid",
            enableSearch = false,
        ),
    )

    const val MODEL = "qwen3.8-omni-flash-realtime"

    fun default(): Preset = ALL[0]

    fun byKey(key: String): Preset = ALL.firstOrNull { it.key == key } ?: default()

    /** 构建 session.update 事件 JSON——结构照抄官方 iOS Demo;voice 用预设专属音色。
     *  语音检测固定 server_vad:服务端阈值档位与 semantic_vad 均实测无效(已移除),
     *  "环境声被当成发言"改由端侧「麦克风灵敏度」整体压低解决。 */
    fun buildSessionUpdate(preset: Preset): JSONObject {
        val session = JSONObject()
            .put("modalities", org.json.JSONArray(listOf("text", "audio")))
            .put("voice", preset.voice)
            .put("input_audio_format", "pcm16")
            .put("output_audio_format", "pcm24")
            .put("instructions", preset.instructions)
            .put("turn_detection", JSONObject()
                .put("type", "server_vad")
                .put("silence_duration_ms", 800))
            .put("max_tokens", 16384)
            .put("repetition_penalty", 1.05)
            .put("presence_penalty", 0.0)
            .put("top_k", 50)
            .put("top_p", 1.0)
            .put("temperature", 0.9)
        if (preset.enableSearch) {
            session.put("enable_search", true)
        }
        return JSONObject().put("type", "session.update").put("session", session)
    }

    /** 会话结束事件。 */
    fun buildSessionFinish(): JSONObject = JSONObject().put("type", "session.finish")
}
