# -*- coding: utf-8 -*-
"""v1.5「麦克风灵敏度」:档位 → 端侧增益系数;上传前整体压低音频(PCM 采样缩放)。"""
import json

import numpy as np
import pytest

from rtchat.audio_io import apply_gain
from rtchat.config import (
    DEFAULT_MIC_GAIN_LEVEL,
    MIC_GAIN_LEVELS,
    Config,
    load_config,
    mic_gain_factor,
    normalize_mic_gain_level,
    save_mic_gain_level,
)
from rtchat.protocol import build_session_update


class TestMapping:
    def test_seven_levels(self):
        assert set(MIC_GAIN_LEVELS) == {1, 2, 3, 4, 5, 6, 7}
        assert MIC_GAIN_LEVELS[1] == 1.0  # 0 dB = 原样

    def test_db_values(self):
        # 系数 = 10^(-dB/20):-6 / -12 / -18 / -24 / -32 / -40 dB
        assert mic_gain_factor(2) == pytest.approx(0.50119, abs=1e-4)
        assert mic_gain_factor(3) == pytest.approx(0.25119, abs=1e-4)
        assert mic_gain_factor(4) == pytest.approx(0.12589, abs=1e-4)
        assert mic_gain_factor(5) == pytest.approx(0.06310, abs=1e-4)
        assert mic_gain_factor(6) == pytest.approx(0.02512, abs=1e-4)
        assert mic_gain_factor(7) == pytest.approx(0.01, abs=1e-9)

    def test_monotonic_decreasing(self):
        vals = [mic_gain_factor(lv) for lv in range(1, 8)]
        assert vals == sorted(vals, reverse=True)

    def test_default_is_original(self):
        assert DEFAULT_MIC_GAIN_LEVEL == 1
        assert mic_gain_factor(DEFAULT_MIC_GAIN_LEVEL) == 1.0


class TestNormalize:
    def test_valid_kept(self):
        for lv in range(1, 8):
            assert normalize_mic_gain_level(lv) == lv

    def test_invalid_falls_back(self):
        for bad in (0, 8, -1, 99, None, "x", ""):
            assert normalize_mic_gain_level(bad) == DEFAULT_MIC_GAIN_LEVEL

    def test_numeric_string_accepted(self):
        assert normalize_mic_gain_level("4") == 4


class TestApplyGain:
    def test_zero_db_returns_same_object(self):
        pcm = b"\x10\x00\x20\x00"
        assert apply_gain(pcm, 1.0) is pcm  # 原样返回,零开销

    def test_halved_samples(self):
        pcm = np.array([1000, -2000, 32767, -32768], dtype=np.int16).tobytes()
        out = np.frombuffer(apply_gain(pcm, 0.5), dtype=np.int16)
        assert list(out) == [500, -1000, 16383, -16384]

    def test_energy_drops_proportionally(self):
        pcm = np.array([8000, -8000] * 50, dtype=np.int16).tobytes()
        before = np.frombuffer(pcm, dtype=np.int16).astype(np.float64)
        after = np.frombuffer(apply_gain(pcm, 0.25), dtype=np.int16).astype(np.float64)
        assert np.sqrt((before**2).mean()) / max(1e-9, np.sqrt((after**2).mean())) == pytest.approx(
            4.0, rel=1e-3
        )


class TestProtocol:
    def test_no_server_threshold(self):
        # v1.5:服务端阈值档位已移除 —— 改为端侧整体压低
        cfg = Config(api_key="sk-test")
        td = build_session_update(cfg)["session"]["turn_detection"]
        assert td["type"] == "server_vad"
        assert "threshold" not in td
        assert td["silence_duration_ms"] == 800


class TestConfigIO:
    def _write(self, tmp_path, obj):
        p = tmp_path / "config.json"
        p.write_text(json.dumps(obj), encoding="utf-8")
        return p

    def test_load_missing_defaults_to_zero_db(self, tmp_path):
        p = self._write(tmp_path, {"api_key": "sk-test"})
        assert load_config(str(p)).mic_gain_level == 1

    def test_load_invalid_normalized(self, tmp_path):
        p = self._write(tmp_path, {"api_key": "sk-test", "mic_gain_level": 9})
        assert load_config(str(p)).mic_gain_level == 1

    def test_save_roundtrip(self, tmp_path):
        p = self._write(tmp_path, {"api_key": "sk-test"})
        save_mic_gain_level(str(p), 3)
        assert load_config(str(p)).mic_gain_level == 3

    def test_save_preserves_other_fields(self, tmp_path):
        p = self._write(tmp_path, {"api_key": "sk-test", "ui_language": "en"})
        save_mic_gain_level(str(p), 5)
        data = json.loads(p.read_text(encoding="utf-8"))
        assert data["ui_language"] == "en"
        assert data["mic_gain_level"] == 5

    def test_save_normalizes_invalid(self, tmp_path):
        p = self._write(tmp_path, {"api_key": "sk-test"})
        save_mic_gain_level(str(p), 9)
        assert load_config(str(p)).mic_gain_level == 1
