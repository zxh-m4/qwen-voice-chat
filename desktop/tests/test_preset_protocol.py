# -*- coding: utf-8 -*-
"""session.update 携带选中预设的 instructions 与联网搜索开关。"""
import pytest

from rtchat.config import Config, Preset
from rtchat.protocol import build_session_update


def cfg_with(preset=None, **kwargs):
    base = dict(
        api_key="sk-t",
        presets={
            "english_teacher": Preset(instructions="全程英语,语速放慢", enable_search=False),
            "encyclopedia": Preset(instructions="百科", enable_search=True, search_source=True),
        },
        active_preset=preset or "english_teacher",
    )
    base.update(kwargs)
    return Config(**base)


class TestPresetInSessionUpdate:
    def test_teacher_instructions_sent(self):
        s = build_session_update(cfg_with())["session"]
        assert s["instructions"] == "全程英语,语速放慢"
        assert s["enable_search"] is False

    def test_encyclopedia_enables_search_with_source(self):
        s = build_session_update(cfg_with("encyclopedia"))["session"]
        assert s["instructions"] == "百科"
        assert s["enable_search"] is True
        assert s["search_options"] == {"enable_source": True}

    def test_no_search_options_when_search_off(self):
        s = build_session_update(cfg_with())["session"]
        assert "search_options" not in s

    def test_legacy_config_still_sends_instructions(self):
        cfg = Config(api_key="sk-t", instructions="旧提示词")
        s = build_session_update(cfg)["session"]
        assert s["instructions"] == "旧提示词"
        assert s["enable_search"] is False


class TestPresetVoice:
    def test_preset_voice_in_session_update(self):
        from rtchat.config import Config, Preset
        from rtchat.protocol import build_session_update

        cfg = Config(
            api_key="sk-t",
            presets={
                "jp": Preset(instructions="日", voice="Ono Anna", enable_search=False),
            },
            active_preset="jp",
        )
        s = build_session_update(cfg)["session"]
        assert s["audio"]["output"]["voice"] == "Ono Anna"

    def test_fallback_global_voice(self):
        from rtchat.config import Config
        from rtchat.protocol import build_session_update

        cfg = Config(api_key="sk-t", voice="Tina")
        s = build_session_update(cfg)["session"]
        assert s["audio"]["output"]["voice"] == "Tina"
