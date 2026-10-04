# -*- coding: utf-8 -*-
"""多角色预设的测试:解析、切换、非法名报错、旧字段兼容、交付配置验收。"""
import json
import os

import pytest

from rtchat.config import Config, ConfigError, load_config

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PRESETS = {
    "english_teacher": {
        "instructions": "You are an English teacher. Speak slowly and clearly.",
        "enable_search": False,
    },
    "encyclopedia": {
        "instructions": "你是一本百科全书。",
        "enable_search": True,
        "search_source": True,
    },
    "humorous": {"instructions": "你很风趣幽默。", "enable_search": False},
}


def write_cfg(tmp_path, **overrides):
    data = {"api_key": "sk-t", "presets": PRESETS, "active_preset": "english_teacher"}
    data.update(overrides)
    p = tmp_path / "config.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return p


class TestPresetLoading:
    def test_active_teacher(self, tmp_path):
        cfg = load_config(str(write_cfg(tmp_path)))
        assert cfg.active_preset == "english_teacher"
        assert "English teacher" in cfg.active_instructions
        assert cfg.active_search is False

    def test_switch_to_encyclopedia(self, tmp_path):
        cfg = load_config(str(write_cfg(tmp_path, active_preset="encyclopedia")))
        assert cfg.active_instructions == "你是一本百科全书。"
        assert cfg.active_search is True
        assert cfg.active_search_source is True

    def test_humorous_has_no_search(self, tmp_path):
        cfg = load_config(str(write_cfg(tmp_path, active_preset="humorous")))
        assert cfg.active_search is False
        assert cfg.active_search_source is False

    def test_invalid_active_preset_raises(self, tmp_path):
        with pytest.raises(ConfigError, match="active_preset"):
            load_config(str(write_cfg(tmp_path, active_preset="nonexistent")))

    def test_missing_active_defaults_to_first(self, tmp_path):
        data = {"api_key": "sk-t", "presets": PRESETS}
        p = tmp_path / "config.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        cfg = load_config(str(p))
        assert cfg.active_preset == "english_teacher"

    def test_legacy_single_instructions_still_works(self, tmp_path):
        cfg = load_config(str(write_cfg(tmp_path, presets=None, active_preset=None,
                                        instructions="旧版提示词")))
        # presets=None 会被 JSON 序列化为 null -> 应回退单 instructions
        assert cfg.active_instructions == "旧版提示词"
        assert cfg.active_search is False

    def test_direct_config_without_presets(self):
        cfg = Config(api_key="sk-x")
        assert cfg.active_instructions == cfg.instructions
        assert cfg.active_search is False


class TestShippedConfig:
    """验收随包发布的配置模板:八语老师齐全、各自锁定语言、专属音色。

    注意读的是 config.example.json —— config.json 已改为首次运行自动生成
    (会被填入真实凭据,故不进仓库)。
    """

    def load(self):
        with open(os.path.join(PROJECT_ROOT, "config.example.json"), encoding="utf-8") as f:
            return json.load(f)

    def test_eight_language_presets(self):
        data = self.load()
        assert set(data["presets"]) == {
            "english_teacher", "japanese_teacher", "russian_teacher", "chinese_teacher",
            "spanish_teacher", "french_teacher", "korean_teacher", "german_teacher",
        }

    def test_voice_per_preset(self):
        p = self.load()["presets"]
        assert p["english_teacher"]["voice"] == "Tina"
        assert p["japanese_teacher"]["voice"] == "Ono Anna"
        assert p["russian_teacher"]["voice"] == "Katerina"
        assert p["chinese_teacher"]["voice"] == "Tina"
        assert p["spanish_teacher"]["voice"] == "Sonrisa"
        assert p["french_teacher"]["voice"] == "Emilien"
        assert p["korean_teacher"]["voice"] == "Sohee"
        assert p["german_teacher"]["voice"] == "Ingrid"

    def test_language_locks(self):
        p = self.load()["presets"]
        expect = {
            "english_teacher": "必须用英语",
            "japanese_teacher": "必须用日语",
            "russian_teacher": "必须用俄语",
            "chinese_teacher": "必须用中文",
            "spanish_teacher": "必须用西班牙语",
            "french_teacher": "必须用法语",
            "korean_teacher": "必须用韩语",
            "german_teacher": "必须用德语",
        }
        for name, phrase in expect.items():
            t = p[name]["instructions"]
            assert phrase in t, f"{name} 缺少语言锁定条款"
            assert "不可违反" in t, f"{name} 缺少强化条款"
            assert "就用什么语言" not in t, f"{name} 仍在跟随用户语言"

    def test_teacher_style(self):
        p = self.load()["presets"]
        for name in p:
            t = p[name]["instructions"]
            assert "语速放慢" in t, f"{name} 缺少慢速要求"
            assert "发音" in t, f"{name} 缺少纠音要求"
