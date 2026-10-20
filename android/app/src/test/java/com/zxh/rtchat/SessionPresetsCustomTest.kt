package com.zxh.rtchat

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 「自定义语言」预设的纯逻辑(不碰 Android / org.json,可直接跑单测)。
 * 守住三件事:语言名真的进了提示词、锁语规则与其他外语老师一致、
 * 名字为空时不构造空提示词。
 */
class SessionPresetsCustomTest {

    @Test
    fun custom_puts_the_language_name_into_the_instructions() {
        val p = SessionPresets.custom("意大利语")
        assertEquals(SessionPresets.CUSTOM_KEY, p.key)
        assertTrue(p.instructions.contains("意大利语"))
        assertTrue(p.instructions.contains("最重要规则"))
        assertTrue(p.instructions.contains("口语老师"))
        assertTrue(p.voice.isNotBlank())
    }

    @Test
    fun custom_locks_to_the_language_and_keeps_the_chinese_exception() {
        val p = SessionPresets.custom("意大利语")
        assertTrue(p.instructions.contains("都必须用意大利语"))
        assertTrue(p.instructions.contains("翻译成中文"))
        // 锁语规则必须真被参数化 —— 防止哪天被复制粘贴成硬编码的「英语」
        assertFalse(p.instructions.contains("英语"))
    }

    @Test
    fun different_languages_produce_different_instructions() {
        assertNotEquals(
            SessionPresets.custom("意大利语").instructions,
            SessionPresets.custom("泰语").instructions,
        )
    }

    @Test
    fun normalize_trims_collapses_and_caps() {
        assertEquals("意大利语", SessionPresets.normalizeLanguage("  意大利语  "))
        assertEquals("巴西 葡萄牙语", SessionPresets.normalizeLanguage("巴西   葡萄牙语"))
        assertEquals("", SessionPresets.normalizeLanguage("   "))
        assertEquals(
            SessionPresets.CUSTOM_LANGUAGE_MAX,
            SessionPresets.normalizeLanguage("a".repeat(200)).length,
        )
    }

    @Test
    fun resolve_builds_custom_only_when_a_language_name_exists() {
        val custom = SessionPresets.resolve(SessionPresets.CUSTOM_KEY, "泰语")
        assertEquals(SessionPresets.CUSTOM_KEY, custom.key)
        assertTrue(custom.instructions.contains("泰语"))

        // 没填过语言名 -> 回落默认老师,不拿空串去构造提示词
        assertEquals(SessionPresets.default().key, SessionPresets.resolve(SessionPresets.CUSTOM_KEY, "").key)
        assertEquals(SessionPresets.default().key, SessionPresets.resolve(SessionPresets.CUSTOM_KEY, "  ").key)
    }

    @Test
    fun resolve_ignores_the_custom_language_for_built_in_presets() {
        val p = SessionPresets.resolve("english_teacher", "泰语")
        assertEquals("english_teacher", p.key)
        assertFalse(p.instructions.contains("泰语"))
    }

    @Test
    fun resolve_falls_back_to_default_for_unknown_key() {
        assertEquals(SessionPresets.default().key, SessionPresets.resolve("不存在的角色", "").key)
    }

    @Test
    fun built_in_presets_never_collide_with_the_custom_key() {
        assertEquals(8, SessionPresets.ALL.size)
        assertTrue(SessionPresets.ALL.none { it.key == SessionPresets.CUSTOM_KEY })
        assertEquals(8, SessionPresets.ALL.map { it.key }.distinct().size)
    }
}