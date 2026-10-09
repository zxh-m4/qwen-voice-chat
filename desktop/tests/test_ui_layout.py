# -*- coding: utf-8 -*-
"""界面比例重构的结构断言(不启动真窗口,只做源码级检查)。

设计目标(2026-10-08「比例改进」):
- 顶栏拆成两行:第一行 = 状态 + 控制按钮;第二行 = 角色选择。避免一行塞不下。
- 所有顶栏按钮统一宽度,不再出现 3/5/6/自适应 混杂。
- 窗口加宽、稍降高度,让字幕区有正常的长宽比。
- 底部费用行与字幕区之间加分隔,尾部不再贴边。
- 功能零改动:连接/重连/语言/设置/帮助/静音门/费用全部保留。
"""
import os
import re

import pytest

APP_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rtchat", "app.py")


@pytest.fixture(scope="module")
def src():
    with open(APP_PATH, encoding="utf-8") as f:
        return f.read()


# ---------- 1. 窗口比例 ----------

def test_window_width_widened(src):
    m = re.search(r'self\.root\.geometry\("(\d+)x(\d+)"\)', src)
    assert m, "未找到主窗口 geometry"
    w, h = int(m.group(1)), int(m.group(2))
    assert w >= 520, f"窗口宽度应至少 520,当前 {w}"
    assert h <= 600, f"窗口高度应不超过 600,当前 {h}"


def test_minsize_allows_narrow(src):
    m = re.search(r'self\.root\.minsize\((\d+),\s*(\d+)\)', src)
    assert m, "未找到 minsize"
    assert int(m.group(1)) >= 360


# ---------- 2. 顶栏拆行 ----------

def test_topbar_buttons_in_own_row(src):
    """控制按钮行与角色选择行必须是两个独立的 Frame。"""
    assert "row_ctrl" in src or "ctrl_row" in src, "未找到独立的控制按钮行"
    frames = re.findall(r'ttk\.Frame\(top[,)]', src)
    assert len(frames) >= 2, f"顶栏应至少有 2 个子行 Frame,实际 {len(frames)}"


def test_buttons_uniform_width(src):
    """顶栏按钮必须统一宽度(不再 3/5/6 混杂)。"""
    # 匹配 self.xxx = ttk.Button(...) 跨行构造里的 width=N
    widths = re.findall(
        r'self\.(?:btn|help_btn|settings_btn|lang_btn)\s*=\s*ttk\.Button\((.*?)\)\s*$',
        src, re.S | re.M,
    )
    got = []
    for block in widths:
        m = re.search(r'width=(\d+)', block)
        if m:
            got.append(m.group(1))
    assert got, "未找到带 width 的顶栏按钮"
    uniq = set(got)
    assert len(uniq) == 1, f"顶栏按钮宽度不统一: {sorted(uniq)}"
    assert len(got) >= 3, f"应至少 3 个按钮带统一宽度,实际 {len(got)}"


# ---------- 3. 字幕区与底部 ----------

def test_transcript_keeps_expand(src):
    assert 'self.transcript.pack(fill="both", expand=True' in src, "字幕区失去纵向扩展"


def test_usage_row_has_top_padding(src):
    """费用行上方应有留白,不再紧贴字幕区。"""
    m = re.search(r'self\.usage_var[^\n]*\n(?:.*\n)*?.*?padding=\(([^)]+)\)', src)
    assert m, "未找到费用行的 padding"
    vals = [v.strip() for v in m.group(1).split(",")]
    top_pad = int(vals[0]) if vals and vals[0].isdigit() else 0
    assert top_pad > 0, f"费用行上方留白应大于 0,当前 padding={m.group(1)}"


# ---------- 4. 功能回归 ----------

def test_core_behaviors_intact(src):
    for token in (
        "def _connect",
        "def _disconnect",
        "def _rebuild_connection",
        "def _toggle_language",
        "def _open_settings",
        "def _show_help",
        "def _on_mic",
        "self.gate.feed",
        "apply_gain",
        "def _refresh_usage",
        "on_user_transcript",
        "on_assistant_text",
        "on_audio_delta",
    ):
        assert token in src, f"功能被破坏: 缺少 {token}"


def test_help_and_settings_dialogs_kept(src):
    assert "def show_settings_dialog" in src
    assert 'win.geometry("560x640")' in src or "560x640" in src, "帮助窗口尺寸被改动"
