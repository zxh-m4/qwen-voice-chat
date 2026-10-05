# -*- coding: utf-8 -*-
"""界面文案字典(中/英)的完整性测试。"""
from rtchat import strings

PRESET_NAMES = {
    "english_teacher", "japanese_teacher", "russian_teacher", "chinese_teacher",
    "spanish_teacher", "french_teacher", "korean_teacher", "german_teacher",
}
STATE_NAMES = {"connecting", "ready", "speaking", "interrupted", "closed"}


class TestKeyParity:
    def test_same_top_level_keys(self):
        assert set(strings.UI["zh"].keys()) == set(strings.UI["en"].keys())

    def test_required_keys(self):
        required = {
            "app_title", "help_title", "btn_ok", "lbl_role",
            "btn_connect", "btn_disconnect", "btn_settings", "btn_help",
            "lang_button", "usage_format", "help",
            "settings_title", "settings_intro", "settings_key_label",
            "settings_key_saved", "settings_ws_label", "settings_ws_saved",
            "settings_err_key_required", "settings_err_key_prefix",
            "settings_err_ws_required", "btn_save", "btn_cancel",
            "sys_preset_switched", "sys_credentials_updated", "sys_conn_closed",
            "sys_session_ended", "err_connect_failed", "err_conn_error",
            "err_audio_open", "prefix_user", "prefix_ai", "state_starting",
        }
        for lang in ("zh", "en"):
            missing = required - set(strings.UI[lang].keys())
            assert not missing, (lang, missing)

    def test_states_and_presets_parity(self):
        for lang in ("zh", "en"):
            assert set(strings.UI[lang]["states"].keys()) == STATE_NAMES, lang
            assert set(strings.UI[lang]["presets"].keys()) == PRESET_NAMES, lang

    def test_no_empty_values(self):
        def walk(node, lang):
            if isinstance(node, dict):
                for k, v in node.items():
                    walk(v, f"{lang}.{k}")
            else:
                assert isinstance(node, str) and node.strip(), (lang, node)

        for lang in ("zh", "en"):
            walk(strings.UI[lang], lang)


class TestHelpSections:
    ZH_MARKERS = ["—— 笑晗", "【关于语音模型】", "【声明】", "【快速开始】",
                  "【费用说明】", "【八种语言】", "【隐私说明】", "【小提示】"]
    EN_MARKERS = ["— Xiaohan", "[About the voice model]", "[Disclaimer]", "[Quick start]",
                  "[Cost]", "[Eight languages]", "[Privacy]", "[Tips]"]

    def test_zh_sections(self):
        for marker in self.ZH_MARKERS:
            assert marker in strings.UI["zh"]["help"], marker

    def test_en_sections(self):
        for marker in self.EN_MARKERS:
            assert marker in strings.UI["en"]["help"], marker

    def test_help_mentions_platform_facts(self):
        # PC 平台事实:凭据存凭据管理器、日志 app.log、耳机防回环
        zh = strings.UI["zh"]["help"]
        assert "凭据管理器" in zh
        assert "app.log" in zh
        assert "耳机" in zh
        en = strings.UI["en"]["help"]
        assert "Credential Manager" in en
        assert "app.log" in en
        assert "headphone" in en.lower()


class TestNormalizeLanguage:
    def test_valid(self):
        assert strings.normalize_language("zh") == "zh"
        assert strings.normalize_language("en") == "en"

    def test_default_zh(self):
        assert strings.normalize_language(None) == "zh"
        assert strings.normalize_language("") == "zh"
        assert strings.normalize_language("fr") == "zh"
