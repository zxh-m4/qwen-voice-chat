package com.zxh.rtchat

import java.io.File
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

/** 「关于」页文本层的单测(纯逻辑,不依赖 Android)。 */
class AboutTextTest {

    @Test
    fun versionLineCarriesVersionName() {
        assertTrue(AboutText.versionLine(true, "1.6").contains("1.6"))
        assertTrue(AboutText.versionLine(false, "1.6").contains("1.6"))
    }

    @Test
    fun beianLineIsJustTheNumberWithArrow() {
        val no = "粤ICP备2026154313号-1A"
        assertEquals("$no ›", AboutText.beianLine(no))
    }

    /** 备案号未填(空串/纯空白)时整行不出现,不留空白占位。 */
    @Test
    fun beianLineDisappearsWhenUnfilled() {
        assertEquals("", AboutText.beianLine(""))
        assertEquals("", AboutText.beianLine("   "))
    }

    @Test
    fun beianTargetIsTheMiitQuerySite() {
        assertEquals("https://beian.miit.gov.cn", AboutText.BEIAN_URL)
    }

    @Test
    fun ossNoticeListsApacheDepsAndClosedSdk() {
        val zh = AboutText.ossNotice(true)
        assertTrue(zh.contains("Apache-2.0"))
        assertTrue(zh.contains("AoqClientSdk"))
        assertTrue(zh.contains("MIT"))
    }

    @Test
    fun ossNoticeEnglishKeepsLicenseIds() {
        val en = AboutText.ossNotice(false)
        assertTrue(en.contains("Apache-2.0"))
        assertTrue(en.contains("AoqClientSdk"))
        assertTrue(en.contains("MIT"))
    }

    /** 隐私政策四条要点必须齐全(上云识别 / 不保存 / 加密留本机 / 日志不含内容)。 */
    @Test
    fun privacyNoticeIsComplete() {
        val zh = AboutText.privacyNotice(true)
        assertEquals(4, zh.lines().count { it.startsWith("·") })
        assertTrue(zh.contains("阿里云百炼"))
        assertTrue(zh.contains("不保存"))
        assertTrue(zh.contains("本机"))
        assertTrue(zh.contains("日志"))

        val en = AboutText.privacyNotice(false)
        assertEquals(4, en.lines().count { it.startsWith("-") })
        assertTrue(en.contains("Bailian"))
        assertTrue(en.contains("no conversation content"))
        assertTrue(en.contains("this device"))
        assertTrue(en.contains("log"))
    }

    /** 「关于」页已有的内容(隐私说明、备案信息、开源声明)不再在帮助页重复(2026-10-13 去重要求)。 */
    @Test
    fun helpPageNoLongerRepeatsWhatTheAboutPageCovers() {
        val forbidden = mapOf(
            "help_zh.txt" to listOf("【隐私说明】", "备案", "MIT"),
            "help_en.txt" to listOf("[Privacy]", "ICP filing", "MIT"),
        )
        for ((file, markers) in forbidden) {
            val help = File("src/main/res/raw/$file").readText(Charsets.UTF_8)
            for (marker in markers) {
                assertTrue("$file 仍在重复「关于」页已有内容:$marker", !help.contains(marker))
            }
        }
    }

    /** 投诉建议渠道:文案必须给出 GitHub issues 地址,并说明本应用无注册/发布功能。 */
    @Test
    fun feedbackNoticeGivesTheIssueTracker() {
        val zh = AboutText.feedbackNotice(true)
        assertTrue(zh.contains("反馈"))
        assertTrue(zh.contains(AboutText.FEEDBACK_URL))
        assertTrue(zh.contains("违法有害信息"))
        assertTrue(zh.contains("无用户注册"))

        val en = AboutText.feedbackNotice(false)
        assertTrue(en.contains(AboutText.FEEDBACK_URL))
        assertTrue(en.contains("no user registration"))
    }

    @Test
    fun feedbackTargetIsTheGithubIssuePage() {
        assertEquals("https://github.com/zxh-m4/qwen-voice-chat/issues", AboutText.FEEDBACK_URL)
    }

    @Test
    fun copyrightLineNamesTheAuthor() {
        assertTrue(AboutText.copyrightLine(true).contains(AboutText.AUTHOR))
        assertTrue(AboutText.copyrightLine(false).contains(AboutText.AUTHOR))
    }
}
