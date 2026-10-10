# -*- coding: utf-8 -*-
"""静音门节省时长的统计与显示(2026-10-10)。

需求(用户选 C 方案):界面上显示静音门拦掉了多少音频时长。
注意语义:这个数字**不代表省了钱** —— 显示的费用仍按连接时长估算(见 usage.py),
它只说明"这段时间服务端没收到你的声音"。
"""
import os

import pytest

from rtchat import strings
from rtchat.gate import SilenceGate


# ---------- 1. 统计来源:gate.stats ----------

def test_gate_tracks_frames_in_and_sent():
    """gate 必须记录收帧数与发帧数,节省量由此推导。"""
    g = SilenceGate(threshold_rms=600, gate_ms=1500, frame_ms=100, enabled=True)
    assert "frames_in" in g.stats and "frames_sent" in g.stats


def test_gate_silent_frames_not_sent():
    """持续静音时,发帧数应明显少于收帧数。"""
    g = SilenceGate(threshold_rms=600, gate_ms=1500, frame_ms=100, enabled=True)
    silent = b"\x00\x00" * 1600  # 100ms 静音 (16kHz 单声道 16bit)
    for _ in range(60):          # 6 秒静音
        g.feed(silent)
    assert g.stats["frames_in"] == 60
    # 初始就静音 -> 一帧都不发
    assert g.stats["frames_sent"] == 0


def test_gate_disabled_sends_everything():
    """静音门关闭时收=发,节省量恒为 0。"""
    g = SilenceGate(threshold_rms=600, gate_ms=1500, frame_ms=100, enabled=False)
    silent = b"\x00\x00" * 1600
    for _ in range(30):
        g.feed(silent)
    assert g.stats["frames_in"] == g.stats["frames_sent"] == 30


# ---------- 2. 节省时长换算 ----------

def test_saved_secs_formula():
    """节省秒数 = (收帧 - 发帧) × 帧长。"""
    from rtchat.usage import saved_secs_from_frames

    # 100 帧收、40 帧发、帧长 100ms -> 省 60 帧 × 0.1s = 6 秒
    assert saved_secs_from_frames(100, 40, 100) == pytest.approx(6.0)
    # 收=发 -> 0
    assert saved_secs_from_frames(50, 50, 100) == pytest.approx(0.0)
    # 防御:发帧 > 收帧(不该发生)时不得为负
    assert saved_secs_from_frames(10, 20, 100) == pytest.approx(0.0)


# ---------- 3. 界面文案:中英双语 ----------

def test_usage_saved_string_exists_both_languages():
    """两种语言都要有「静音省」文案,否则切语言会 KeyError。"""
    for lang in ("zh", "en"):
        ui = strings.UI[lang]
        assert "usage_saved" in ui, f"{lang} 缺少 usage_saved 文案"


def test_usage_saved_formats_seconds():
    """文案要能吃下秒数参数。"""
    for lang in ("zh", "en"):
        tpl = strings.UI[lang]["usage_saved"]
        out = tpl.format(secs=18)
        assert "18" in out, f"{lang} 文案未嵌入秒数: {out}"


def test_usage_format_still_has_original_fields():
    """原有费用行格式未被破坏(回归)。"""
    for lang in ("zh", "en"):
        tpl = strings.UI[lang]["usage_format"]
        for field in ("{s:", "{t:", "{mss}"):
            assert field in tpl, f"{lang} usage_format 丢了 {field}"


# ---------- 4. app 层:读 stats、按语言渲染、无节省时不显示 ----------

def test_app_has_saved_seconds_helper():
    """app 里要有个把 gate.stats 换算成节省秒数的方法。"""
    app = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "rtchat", "app.py")
    src = open(app, encoding="utf-8").read()
    assert "saved_secs_from_frames" in src, "app 未使用节省时长换算函数"
    assert "_silence_saved_text" in src or "usage_saved" in src, \
        "app 未把节省时长接进界面文案"
