package com.zxh.rtchat

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * 「外语转述」模式的纯逻辑(不碰 Android / org.json,可直接跑单测)。
 * 守住:两种模式的档位一一对应、切换模式能折回同语种、
 * 转述提示词锁死输出且不带教学成分、四种 key 都能 resolve。
 */
class SessionPresetsRestateTest {

    @Test
    fun keysFor_lists_eight_built_in_plus_custom_in_both_modes() {
        val teacher = SessionPresets.keysFor(SessionPresets.MODE_TEACHER)
        val restate = SessionPresets.keysFor(SessionPresets.MODE_RESTATE)
        assertEquals(9, teacher.size)
        assertEquals(9, restate.size)
        assertEquals(SessionPresets.CUSTOM_KEY, teacher.last())
        assertEquals(SessionPresets.CUSTOM_RESTATE_KEY, restate.last())
        assertEquals(SessionPresets.ALL.map { it.key }, teacher.dropLast(1))
        assertEquals(SessionPresets.RESTATE.map { it.key }, restate.dropLast(1))
    }

    @Test
    fun unknown_mode_falls_back_to_the_teacher_keys() {
        assertEquals(
            SessionPresets.keysFor(SessionPresets.MODE_TEACHER),
            SessionPresets.keysFor("不认识"),
        )
    }

    @Test
    fun restate_covers_every_built_in_language() {
        assertEquals(SessionPresets.ALL.size, SessionPresets.RESTATE.size)
        assertEquals(SessionPresets.ALL.map { it.key }, SessionPresets.RESTATE.map { it.teacherKey })
    }

    @Test
    fun keyInMode_keeps_the_same_language_when_switching() {
        assertEquals("restate_english", SessionPresets.keyInMode("english_teacher", SessionPresets.MODE_RESTATE))
        assertEquals("restate_german", SessionPresets.keyInMode("german_teacher", SessionPresets.MODE_RESTATE))
        assertEquals("english_teacher", SessionPresets.keyInMode("restate_english", SessionPresets.MODE_TEACHER))
        assertEquals("german_teacher", SessionPresets.keyInMode("restate_german", SessionPresets.MODE_TEACHER))
        assertEquals(
            SessionPresets.CUSTOM_RESTATE_KEY,
            SessionPresets.keyInMode(SessionPresets.CUSTOM_KEY, SessionPresets.MODE_RESTATE),
        )
        assertEquals(
            SessionPresets.CUSTOM_KEY,
            SessionPresets.keyInMode(SessionPresets.CUSTOM_RESTATE_KEY, SessionPresets.MODE_TEACHER),
        )
    }

    @Test
    fun keyInMode_is_idempotent_and_falls_back_inside_the_mode() {
        assertEquals("restate_english", SessionPresets.keyInMode("restate_english", SessionPresets.MODE_RESTATE))
        assertEquals("english_teacher", SessionPresets.keyInMode("english_teacher", SessionPresets.MODE_TEACHER))
        val fallback = SessionPresets.keyInMode("不存在的角色", SessionPresets.MODE_RESTATE)
        assertTrue(SessionPresets.keysFor(SessionPresets.MODE_RESTATE).contains(fallback))
    }

    @Test
    fun restater_locks_its_output_and_carries_no_teaching() {
        val p = SessionPresets.restater("意大利语")
        assertEquals(SessionPresets.CUSTOM_RESTATE_KEY, p.key)
        assertTrue(p.instructions.contains("转述者"))
        assertTrue(p.instructions.contains("只输出转述内容本身"))
        assertTrue(p.instructions.contains("意大利语"))
        assertFalse(p.instructions.contains("老师"))
        assertFalse(p.instructions.contains("纠正"))
    }

    @Test
    fun built_in_restater_uses_its_own_language_and_voice() {
        val english = SessionPresets.restaterFor(SessionPresets.RESTATE.first())
        assertEquals("restate_english", english.key)
        assertTrue(english.instructions.contains("英语"))
        assertEquals("Tina", english.voice)
        assertEquals("英语转述", english.label)
    }

    @Test
    fun resolve_handles_all_four_kinds_of_key() {
        assertEquals("english_teacher", SessionPresets.resolve("english_teacher", "").key)
        assertEquals(SessionPresets.CUSTOM_KEY, SessionPresets.resolve(SessionPresets.CUSTOM_KEY, "泰语").key)

        val restate = SessionPresets.resolve("restate_english", "")
        assertEquals("restate_english", restate.key)
        assertTrue(restate.instructions.contains("转述者"))

        val customRestate = SessionPresets.resolve(SessionPresets.CUSTOM_RESTATE_KEY, "泰语")
        assertEquals(SessionPresets.CUSTOM_RESTATE_KEY, customRestate.key)
        assertTrue(customRestate.instructions.contains("泰语"))
        assertTrue(customRestate.instructions.contains("转述者"))
    }

    @Test
    fun resolve_restate_custom_falls_back_when_the_name_is_missing() {
        assertEquals(SessionPresets.default().key, SessionPresets.resolve(SessionPresets.CUSTOM_RESTATE_KEY, "").key)
        assertEquals(SessionPresets.default().key, SessionPresets.resolve(SessionPresets.CUSTOM_RESTATE_KEY, "  ").key)
    }
}