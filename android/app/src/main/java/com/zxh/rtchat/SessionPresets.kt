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

    /** 使用模式:「语言老师」陪伴对话 / 「外语转述」只把你说的话转述成所选外语 / 「口译」中文 ⇄ 目标语双向互译。 */
    const val MODE_TEACHER = "teacher"
    const val MODE_RESTATE = "restate"
    const val MODE_INTERPRET = "interpret"

    /**
     * 「自定义」档位的 key —— 老师 / 转述 / 口译模式各一个,
     * 三个档位共用用户挑的同一个语种(见 SettingsStore.customLanguage)。
     */
    const val CUSTOM_KEY = "custom_teacher"
    const val CUSTOM_RESTATE_KEY = "custom_restate"
    const val CUSTOM_INTERPRET_KEY = "custom_interpret"

    /** 语言名长度上限:只是不让提示词被塞进超长文本(「巴西葡萄牙语」这类也够写)。 */
    const val CUSTOM_LANGUAGE_MAX = 30

    /** 自定义语言的音色:语种未知,用通用音色(与英语/中文老师一致)。 */
    private const val CUSTOM_VOICE = "Tina"

    /**
     * 按用户输入的语言名构造一个「语言老师」预设,结构与八个内置预设完全一致。
     *
     * 语言名中英文都收(「意大利语」/「Italian」皆可),**不做语种白名单** ——
     * 模型本身就认识语种名,白名单只会挡住用户。锁语规则与其余外语老师一致:
     * 只用该语言回答,仅明确说「用中文解释/翻译」才切中文。
     */
    fun custom(language: String): Preset {
        val lang = normalizeLanguage(language)
        val lock = lockRule(lang, "「用中文解释」或「翻译成中文」")
        return Preset(
            CUSTOM_KEY, lang + "老师",
            lock + teacherBody(lang, "当用户某个" + lang + "发音或语调明显不标准时,温和地指出问题、示范正确的说法,并给一个简短的例句;"),
            voice = CUSTOM_VOICE,
            enableSearch = false,
        )
    }

    /** 语言名清洗:去首尾空白、内部空白折叠成一个空格、截断到 [CUSTOM_LANGUAGE_MAX]。空串=用户没填。 */
    fun normalizeLanguage(raw: String): String =
        raw.trim().replace(Regex("\\s+"), " ").take(CUSTOM_LANGUAGE_MAX)

    /**
     * 转述模式的目标语种档位。teacherKey 用于切换模式时把同语种对应过去,
     * voice 与老师模式同语种保持一致(音色跟语种走,不跟模式走)。
     */
    data class RestateLang(val key: String, val teacherKey: String, val promptLang: String, val voice: String)

    val RESTATE = listOf(
        RestateLang("restate_english", "english_teacher", "英语", "Tina"),
        RestateLang("restate_japanese", "japanese_teacher", "日语", "Ono Anna"),
        RestateLang("restate_russian", "russian_teacher", "俄语", "Katerina"),
        RestateLang("restate_chinese", "chinese_teacher", "中文(普通话)", "Tina"),
        RestateLang("restate_spanish", "spanish_teacher", "西班牙语", "Sonrisa"),
        RestateLang("restate_french", "french_teacher", "法语", "Emilien"),
        RestateLang("restate_korean", "korean_teacher", "韩语", "Sohee"),
        RestateLang("restate_german", "german_teacher", "德语", "Ingrid"),
    )

    /**
     * 转述提示词 —— 与 v1.5-trial 实验版同一套思路:人格换成「转述者」,
     * 用「任何情况下都只输出转述内容本身」把输出锁死,不解释、不寒暄、不教学。
     * 这是它能当实时翻译用的关键,不要往里面加老师的成分。
     */
    private fun restateInstructions(lang: String): String =
        "你是转述者。【最重要规则,不可违反】任何情况下都只输出转述内容本身 —— " +
            "不回答、不提问、不延伸话题,不解释、不寒暄、不加任何前后缀。\n" +
            "用户用中文或其他语言说话时,你用地道自然的" + lang + "把意思说出来;" +
            "用户已经用" + lang + "说话时,你用更地道自然的说法重述一遍。\n" +
            "输出只有转述结果本身,不要出现任何其他文字。"

    /** 内置转述档位 → 预设。 */
    fun restaterFor(l: RestateLang): Preset =
        Preset(l.key, l.promptLang + "转述", restateInstructions(l.promptLang), voice = l.voice, enableSearch = false)

    /** 自定义语种的转述预设。 */
    fun restater(customLanguage: String): Preset {
        val lang = normalizeLanguage(customLanguage)
        return Preset(CUSTOM_RESTATE_KEY, lang + "转述", restateInstructions(lang), voice = CUSTOM_VOICE, enableSearch = false)
    }

    /**
     * 口译提示词 —— 逐字移植自鸿蒙版(安卓 v2.0 新增)。
     * 与「转述」的关键区别:转述是单向的,口译是双向的(对方说外语要翻回中文),
     * 否则对方说完你朋友根本听不懂。数字/时间/价格/地名要求准确保留 ——
     * 旅行场景问路、订房、结账全靠这些。文案是调过的,不要顺手改动。
     */
    private fun interpretInstructions(lang: String): String =
        "你是一名实时口语译员,在说中文的用户与说" + lang + "的人之间做双向口译。\n" +
            "【最重要规则,不可违反】任何情况下都只输出译文本身 —— " +
            "不回答、不提问、不延伸话题,不解释、不寒暄、不加任何前后缀、不做任何补充。\n" +
            "\n" +
            "按你听到的语言决定译向:\n" +
            "· 听到中文(或除" + lang + "以外的任何语言)时,用地道自然的" + lang + "把意思说出来;\n" +
            "· 听到" + lang + "时,用简洁自然的中文把意思说出来。\n" +
            "\n" +
            "要求:\n" +
            "· 只译意思,保留说话人的语气和礼貌程度,不要逐字直译;\n" +
            "· 数字、时间、价格、地名、人名必须准确保留;\n" +
            "· 对方说得含糊或只说了半句时,只译你听到的部分,不要自己补全、不要猜测;\n" +
            "· 不要把你自己的任何话加进去。"

    /** 内置口译档位 → 预设。key 由转述 key 推导,保证三模式同语种永远对齐。 */
    fun interpreterFor(l: RestateLang): Preset =
        Preset(
            "interpret_" + l.key.removePrefix("restate_"),
            l.promptLang + " ⇄ 中文",
            interpretInstructions(l.promptLang),
            voice = CUSTOM_VOICE,
            enableSearch = false,
        )

    /**
     * 七个内置口译档(除中文 —— 中文 ⇄ 中文没有意义)。
     * 音色统一 Tina:口译一轮里既要说外语又要说中文,专属音色未必覆盖中文;
     * Tina 是唯一确认覆盖「中文 + 28 种外语」的通用音色。
     */
    val INTERPRET: List<Preset> = RESTATE.filter { it.key != "restate_chinese" }.map { interpreterFor(it) }

    /** 自定义语种的口译预设。 */
    fun interpreter(customLanguage: String): Preset {
        val lang = normalizeLanguage(customLanguage)
        return Preset(CUSTOM_INTERPRET_KEY, lang + " ⇄ 中文", interpretInstructions(lang), voice = CUSTOM_VOICE, enableSearch = false)
    }

    /** 某种模式下的档位顺序(下拉用):内置档位 + 末尾的「自定义」。 */
    fun keysFor(mode: String): List<String> = when (mode) {
        MODE_RESTATE -> RESTATE.map { it.key } + CUSTOM_RESTATE_KEY
        MODE_INTERPRET -> INTERPRET.map { it.key } + CUSTOM_INTERPRET_KEY
        else -> ALL.map { it.key } + CUSTOM_KEY
    }

    /** 某种模式下的「自定义」档位 key。 */
    fun customKeyFor(mode: String): String = when (mode) {
        MODE_RESTATE -> CUSTOM_RESTATE_KEY
        MODE_INTERPRET -> CUSTOM_INTERPRET_KEY
        else -> CUSTOM_KEY
    }

    /** key → 语种 id;不认识的 key 返回空串。 */
    private fun langIdOf(key: String): String = when {
        key.endsWith("_teacher") -> key.removeSuffix("_teacher")
        key.startsWith("restate_") -> key.removePrefix("restate_")
        key.startsWith("interpret_") -> key.removePrefix("interpret_")
        else -> ""
    }

    /** 语种 id + 模式 → 该模式的档位 key。 */
    private fun keyOfLang(id: String, mode: String): String = when (mode) {
        MODE_RESTATE -> "restate_" + id
        MODE_INTERPRET -> "interpret_" + id
        else -> id + "_teacher"
    }

    /** 切换模式时尽量保持同一语种;对不上(或 key 不认识)就回该模式的默认档。 */
    fun keyInMode(key: String, mode: String): String {
        val keys = keysFor(mode)
        if (keys.contains(key)) return key
        if (key == CUSTOM_KEY || key == CUSTOM_RESTATE_KEY || key == CUSTOM_INTERPRET_KEY) return customKeyFor(mode)
        val id = langIdOf(key)
        if (id.isNotEmpty()) {
            val mapped = keyOfLang(id, mode)
            if (keys.contains(mapped)) return mapped
        }
        return keys.first()
    }

    /**
     * 角色 key → 预设(五种 key 都认:老师档、老师自定义档、转述档、转述自定义档、口译档/口译自定义档)。
     * 自定义档的语言名为空(没选过)时回落到默认预设,不拿空串去构造提示词。
     */
    fun resolve(key: String, customLanguage: String): Preset {
        if (key == CUSTOM_KEY && customLanguage.isNotBlank()) return custom(customLanguage)
        if (key == CUSTOM_RESTATE_KEY && customLanguage.isNotBlank()) return restater(customLanguage)
        if (key == CUSTOM_INTERPRET_KEY && customLanguage.isNotBlank()) return interpreter(customLanguage)
        INTERPRET.firstOrNull { it.key == key }?.let { return it }
        RESTATE.firstOrNull { it.key == key }?.let { return restaterFor(it) }
        return byKey(key)
    }

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
