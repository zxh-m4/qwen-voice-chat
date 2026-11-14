package com.zxh.rtchat

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 「口译」模式的纯逻辑(不碰 Android / org.json,可直接跑单测)。
 * 守住:中文不出口译档、三模式互切保同语种(中文切口译回落首档)、
 * 口译提示词双向锁输出且不带教学成分、音色统一 Tina、五种 key 都能 resolve。
 */
class SessionPresetsInterpretTest {

    @Test
    fun keysFor_interpret_lists_seven_built_in_plus_custom() {
        val interpret = SessionPresets.keysFor(SessionPresets.MODE_INTERPRET)
        assertEquals(8, interpret.size)
        assertEquals(SessionPresets.CUSTOM_INTERPRET_KEY, interpret.last())
        assertEquals(SessionPresets.INTERPRET.map { it.key }, interpret.dropLast(1))
        assertEquals(
            listOf(
                "interpret_english", "interpret_japanese", "interpret_russian",
                "interpret_spanish", "interpret_french", "interpret_korean", "interpret_german",
            ),
            interpret.dropLast(1),
        )
    }

    @Test
    fun interpret_excludes_chinese() {
        assertEquals(7, SessionPresets.INTERPRET.size)
        assertFalse(SessionPresets.INTERPRET.any { it.key.contains("chinese") })
    }

    @Test
    fun keyInMode_keeps_the_same_language_across_all_three_modes() {
        assertEquals("interpret_english", SessionPresets.keyInMode("english_teacher", SessionPresets.MODE_INTERPRET))
        assertEquals("interpret_german", SessionPresets.keyInMode("restate_german", SessionPresets.MODE_INTERPRET))
        assertEquals("english_teacher", SessionPresets.keyInMode("interpret_english", SessionPresets.MODE_TEACHER))
        assertEquals("restate_french", SessionPresets.keyInMode("interpret_french", SessionPresets.MODE_RESTATE))
    }

    @Test
    fun keyInMode_chinese_falls_back_to_the_first_interpret_slot() {
        assertEquals("interpret_english", SessionPresets.keyInMode("chinese_teacher", SessionPresets.MODE_INTERPRET))
        assertEquals("interpret_english", SessionPresets.keyInMode("restate_chinese", SessionPresets.MODE_INTERPRET))
    }

    @Test
    fun keyInMode_custom_keys_round_trip_between_all_modes() {
        assertEquals(
            SessionPresets.CUSTOM_INTERPRET_KEY,
            SessionPresets.keyInMode(SessionPresets.CUSTOM_KEY, SessionPresets.MODE_INTERPRET),
        )
        assertEquals(
            SessionPresets.CUSTOM_KEY,
            SessionPresets.keyInMode(SessionPresets.CUSTOM_INTERPRET_KEY, SessionPresets.MODE_TEACHER),
        )
        assertEquals(
            SessionPresets.CUSTOM_RESTATE_KEY,
            SessionPresets.keyInMode(SessionPresets.CUSTOM_INTERPRET_KEY, SessionPresets.MODE_RESTATE),
        )
    }

    @Test
    fun keyInMode_interpret_is_idempotent_and_falls_back_inside_the_mode() {
        assertEquals("interpret_english", SessionPresets.keyInMode("interpret_english", SessionPresets.MODE_INTERPRET))
        val fallback = SessionPresets.keyInMode("不存在的角色", SessionPresets.MODE_INTERPRET)
        assertTrue(SessionPresets.keysFor(SessionPresets.MODE_INTERPRET).contains(fallback))
    }

    @Test
    fun interpreter_locks_its_output_and_translates_both_ways() {
        val p = SessionPresets.interpreter("意大利语")
        assertEquals(SessionPresets.CUSTOM_INTERPRET_KEY, p.key)
        assertTrue(p.instructions.contains("双向口译"))
        assertTrue(p.instructions.contains("只输出译文本身"))
        assertTrue(p.instructions.contains("意大利语"))
        assertTrue(p.instructions.contains("用简洁自然的中文"))
        assertFalse(p.instructions.contains("老师"))
        assertFalse(p.instructions.contains("纠正"))
        assertFalse(p.instructions.contains("转述者"))
    }

    @Test
    fun built_in_interpreters_all_use_tina_and_the_bidirectional_label() {
        val english = SessionPresets.INTERPRET.first()
        assertEquals("interpret_english", english.key)
        assertEquals("英语 ⇄ 中文", english.label)
        assertTrue(english.instructions.contains("英语"))
        assertTrue(SessionPresets.INTERPRET.all { it.voice == "Tina" })
    }

    @Test
    fun resolve_handles_interpret_keys() {
        val builtin = SessionPresets.resolve("interpret_english", "")
        assertEquals("interpret_english", builtin.key)
        assertTrue(builtin.instructions.contains("双向口译"))

        val custom = SessionPresets.resolve(SessionPresets.CUSTOM_INTERPRET_KEY, "泰语")
        assertEquals(SessionPresets.CUSTOM_INTERPRET_KEY, custom.key)
        assertTrue(custom.instructions.contains("泰语"))
        assertTrue(custom.instructions.contains("双向口译"))
    }

    @Test
    fun resolve_interpret_custom_falls_back_when_the_name_is_missing() {
        assertEquals(SessionPresets.default().key, SessionPresets.resolve(SessionPresets.CUSTOM_INTERPRET_KEY, "").key)
        assertEquals(SessionPresets.default().key, SessionPresets.resolve(SessionPresets.CUSTOM_INTERPRET_KEY, "  ").key)
    }
}