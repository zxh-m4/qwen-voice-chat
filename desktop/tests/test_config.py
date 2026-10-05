# -*- coding: utf-8 -*-
"""配置加载与接入地址推导的测试。"""
import json
import os

import pytest

from rtchat.config import Config, ConfigError, load_config


def make_cfg_file(tmp_path, **overrides):
    data = {"api_key": "sk-test123"}
    data.update(overrides)
    p = tmp_path / "config.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return p


class TestLoadConfig:
    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(ConfigError):
            load_config(str(tmp_path / "nope.json"))

    def test_missing_api_key_raises(self, tmp_path):
        p = tmp_path / "config.json"
        p.write_text("{}", encoding="utf-8")
        with pytest.raises(ConfigError, match="api_key"):
            load_config(str(p))

    def test_defaults(self, tmp_path):
        cfg = load_config(str(make_cfg_file(tmp_path)))
        assert cfg.model == "qwen3.8-omni-flash-realtime"
        assert cfg.voice == "Tina"
        assert cfg.input_sample_rate == 16000
        assert cfg.output_sample_rate == 24000
        assert cfg.transcription_model == "gummy-realtime-v1"
        assert cfg.vad_type == "server_vad"

    def test_env_key_fallback(self, tmp_path, monkeypatch):
        monkeypatch.setenv("DASHSCOPE_API_KEY", "sk-from-env")
        p = tmp_path / "config.json"
        p.write_text("{}", encoding="utf-8")
        cfg = load_config(str(p))
        assert cfg.api_key == "sk-from-env"

    def test_overrides_applied(self, tmp_path):
        cfg = load_config(str(make_cfg_file(tmp_path, voice="Ethan", model="m2")))
        assert cfg.voice == "Ethan"
        assert cfg.model == "m2"


class TestWsUrl:
    def test_workspace_domain(self):
        cfg = Config(api_key="sk-x", workspace_id="llm-xxxxxxxx")
        assert cfg.ws_url == (
            "wss://llm-xxxxxxxx.cn-beijing.maas.aliyuncs.com"
            "/api-ws/v1/realtime?model=qwen3.8-omni-flash-realtime"
        )

    def test_token_plan_key_uses_token_plan_host(self):
        cfg = Config(api_key="sk-sp-abc", workspace_id="")
        assert cfg.ws_url.startswith(
            "wss://token-plan.cn-beijing.maas.aliyuncs.com/api-ws/v1/realtime?model="
        )

    def test_plain_key_without_workspace_uses_public_host(self):
        cfg = Config(api_key="sk-plain", workspace_id="")
        assert cfg.ws_url.startswith("wss://dashscope.aliyuncs.com/api-ws/v1/realtime?model=")

    def test_model_encoded_in_query(self):
        cfg = Config(api_key="sk-x", model="qwen3.8-omni-flash-realtime")
        assert "model=qwen3.8-omni-flash-realtime" in cfg.ws_url

    def test_empty_key_raises(self):
        with pytest.raises(ConfigError):
            Config(api_key="").ws_url


class TestLocalCredentials:
    """config.local.json:用户自己的凭据(不进分享),优先级最高。"""

    def test_local_file_overrides_config(self, tmp_path):
        from rtchat.config import save_credentials

        p = tmp_path / "config.json"
        p.write_text(json.dumps({"api_key": "", "workspace_id": ""}), encoding="utf-8")
        save_credentials(str(p), "sk-local-key", "llm-local-ws")
        cfg = load_config(str(p))
        assert cfg.api_key == "sk-local-key"
        assert cfg.workspace_id == "llm-local-ws"

    def test_local_overrides_config_existing_key(self, tmp_path):
        from rtchat.config import save_credentials

        p = tmp_path / "config.json"
        p.write_text(json.dumps({"api_key": "sk-from-config", "workspace_id": "ws-a"}), encoding="utf-8")
        save_credentials(str(p), "sk-local", "ws-b")
        cfg = load_config(str(p))
        assert cfg.api_key == "sk-local"          # 本地凭据优先
        assert cfg.workspace_id == "ws-b"

    def test_config_key_used_when_no_local(self, tmp_path):
        cfg = load_config(str(make_cfg_file(tmp_path, api_key="sk-config-only")))
        assert cfg.api_key == "sk-config-only"

    def test_missing_all_raises(self, tmp_path):
        p = tmp_path / "config.json"
        p.write_text(json.dumps({"api_key": ""}), encoding="utf-8")
        with pytest.raises(ConfigError, match="api_key"):
            load_config(str(p))

    def test_save_local_roundtrip_strips(self, tmp_path):
        from rtchat.config import save_credentials

        p = tmp_path / "config.json"
        p.write_text("{}", encoding="utf-8")
        save_credentials(str(p), "  sk-x  ", "  llm-y  ")
        cfg = load_config(str(p))
        assert cfg.api_key == "sk-x"
        assert cfg.workspace_id == "llm-y"

    def test_broken_local_file_ignored(self, tmp_path):
        p = tmp_path / "config.json"
        p.write_text(json.dumps({"api_key": "sk-config"}), encoding="utf-8")
        (tmp_path / "config.local.json").write_text("{broken", encoding="utf-8")
        cfg = load_config(str(p))
        assert cfg.api_key == "sk-config"          # 损坏的本地文件被忽略,回退配置


class TestUiLanguage:
    """界面语言(默认中文,可切英文;非法值回落中文)。"""

    def test_default_zh(self, tmp_path):
        cfg = load_config(str(make_cfg_file(tmp_path)))
        assert cfg.ui_language == "zh"

    def test_load_en(self, tmp_path):
        cfg = load_config(str(make_cfg_file(tmp_path, ui_language="en")))
        assert cfg.ui_language == "en"

    def test_invalid_falls_back_to_zh(self, tmp_path):
        cfg = load_config(str(make_cfg_file(tmp_path, ui_language="fr")))
        assert cfg.ui_language == "zh"

    def test_save_and_reload(self, tmp_path):
        from rtchat.config import save_ui_language

        p = make_cfg_file(tmp_path)
        save_ui_language(str(p), "en")
        data = json.loads(p.read_text(encoding="utf-8"))
        assert data["ui_language"] == "en"
        assert data["api_key"] == "sk-test123"     # 其他字段保留
        assert load_config(str(p)).ui_language == "en"

    def test_save_invalid_normalizes_to_zh(self, tmp_path):
        from rtchat.config import save_ui_language

        p = make_cfg_file(tmp_path)
        save_ui_language(str(p), "fr")
        data = json.loads(p.read_text(encoding="utf-8"))
        assert data["ui_language"] == "zh"


class TestResolveCredentialsInput:
    """设置对话框保存逻辑:双框打码不回填,空输入沿用已存值。"""

    def test_both_provided(self):
        from rtchat.config import resolve_credentials_input

        key, ws, err = resolve_credentials_input("sk-new", "llm-new", None)
        assert (key, ws, err) == ("sk-new", "llm-new", "")

    def test_key_empty_reuses_saved(self):
        from rtchat.config import resolve_credentials_input

        cfg = Config(api_key="sk-old", workspace_id="llm-old")
        key, ws, err = resolve_credentials_input("", "llm-new", cfg)
        assert (key, ws, err) == ("sk-old", "llm-new", "")

    def test_ws_empty_reuses_saved(self):
        from rtchat.config import resolve_credentials_input

        cfg = Config(api_key="sk-old", workspace_id="llm-old")
        key, ws, err = resolve_credentials_input("sk-new", "", cfg)
        assert (key, ws, err) == ("sk-new", "llm-old", "")

    def test_first_run_requires_key(self):
        from rtchat.config import resolve_credentials_input

        _, _, err = resolve_credentials_input("", "", None)
        assert err == "key_required"

    def test_key_prefix_validated(self):
        from rtchat.config import resolve_credentials_input

        _, _, err = resolve_credentials_input("bad-key", "llm-x", None)
        assert err == "key_prefix"

    def test_ws_required(self):
        from rtchat.config import resolve_credentials_input

        _, _, err = resolve_credentials_input("sk-x", "", None)
        assert err == "ws_required"

    def test_whitespace_stripped(self):
        from rtchat.config import resolve_credentials_input

        key, ws, err = resolve_credentials_input("  sk-x  ", "  llm-y  ", None)
        assert (key, ws, err) == ("sk-x", "llm-y", "")
