# -*- coding: utf-8 -*-
"""桌面版图标与打包配置的结构断言(源码级,不启动程序)。

背景(2026-10-10):v1.5-pre 自用测试包内嵌的是 Windows 记事本默认图标,
根因是源码仓库既无 app.ico 也无 .spec,打包时未传 icon=。
本测试保证这两样东西在仓库里持续存在且配置正确。
"""
import os

import pytest

DESKTOP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ICO = os.path.join(DESKTOP, "app.ico")


def test_ico_exists():
    """app.ico 必须存在于 desktop 根目录(与 paths.app_dir() 的解析一致)。"""
    assert os.path.exists(ICO), f"缺少图标文件: {ICO}"


def test_ico_is_valid_multisize():
    """ico 必须是含多尺寸的合法 ICO(至少覆盖 256/32/16 三档)。"""
    if not os.path.exists(ICO):
        pytest.skip("app.ico 不存在")
    with open(ICO, "rb") as f:
        data = f.read()
    assert data[:4] == b"\x00\x00\x01\x00", "不是合法 ICO 头"
    count = int.from_bytes(data[4:6], "little")
    assert count >= 3, f"ICO 条目过少({count}),应含多尺寸"
    sizes = set()
    for i in range(count):
        off = 6 + i * 16
        w = data[off] or 256
        h = data[off + 1] or 256
        assert w == h, "ICO 条目应为正方形"
        sizes.add(w)
    for need in (256, 32, 16):
        assert need in sizes, f"缺少 {need}x{need} 尺寸;实有 {sorted(sizes)}"


def test_spec_exists_and_sets_icon():
    """.spec 必须存在且给 EXE 传了 icon=。"""
    spec = None
    for name in os.listdir(DESKTOP):
        if name.endswith(".spec"):
            spec = os.path.join(DESKTOP, name)
            break
    assert spec, "desktop 目录缺少 .spec 打包配置"
    src = open(spec, encoding="utf-8").read()
    assert "icon=" in src, ".spec 未设置 icon=(打包出的 exe 会带记事本默认图标)"
    assert "app.ico" in src, ".spec 的 icon 未指向 app.ico"


def test_spec_bundles_ico_as_data():
    """app.ico 必须作为数据文件打进包,否则 exe 运行时找不到它(窗口图标会空)。"""
    spec = None
    for name in os.listdir(DESKTOP):
        if name.endswith(".spec"):
            spec = os.path.join(DESKTOP, name)
            break
    assert spec, "缺少 .spec"
    src = open(spec, encoding="utf-8").read()
    # datas 里要提到 app.ico（允许 "app.ico" 或 ('app.ico', '.') 形式）
    assert "app.ico" in src.split("EXE(")[0] or "app.ico" in src, "app.ico 未进入打包数据"


def test_spec_bundles_config_example():
    """config.example.json 必须进包。

    程序首次运行会在 exe 同目录找它并自动生成 config.json(见
    rtchat/config.py:ensure_config_file)。不打包的话,分发出去的包一启动
    就弹「配置文件不存在,且无法从 config.example.json 生成」。
    """
    spec = None
    for name in os.listdir(DESKTOP):
        if name.endswith(".spec"):
            spec = os.path.join(DESKTOP, name)
            break
    assert spec, "缺少 .spec"
    src = open(spec, encoding="utf-8").read()
    assert "config.example.json" in src, \
        "config.example.json 未进入打包数据(分发包首启会报配置错误)"

    # 该文件本身也要存在,否则 spec 引用了也没用
    assert os.path.exists(os.path.join(DESKTOP, "config.example.json")), \
        "desktop/config.example.json 不存在"


def test_window_icon_code_present():
    """app.py 仍需在启动时设置窗口图标。"""
    app = os.path.join(DESKTOP, "rtchat", "app.py")
    src = open(app, encoding="utf-8").read()
    assert "_set_window_icon" in src, "窗口图标设置代码丢失"
    assert "iconbitmap" in src, "Windows 分支的 iconbitmap 调用丢失"


def test_no_numpy_dependency():
    """numpy 已移除,requirements 与源码都不得再依赖它(v1.5-pre 瘦身成果)。"""
    req = open(os.path.join(DESKTOP, "requirements.txt"), encoding="utf-8").read()
    active = [ln.strip() for ln in req.splitlines()
              if ln.strip() and not ln.strip().startswith("#")]
    assert not any(ln.lower().startswith("numpy") for ln in active), \
        "requirements 里仍有 numpy(瘦身成果被回退)"
    # 源码里不得 import numpy(注释里提到旧实现是允许的)
    rtchat = os.path.join(DESKTOP, "rtchat")
    for fn in os.listdir(rtchat):
        if not fn.endswith(".py"):
            continue
        text = open(os.path.join(rtchat, fn), encoding="utf-8").read()
        for ln in text.splitlines():
            s = ln.strip()
            if s.startswith("#"):
                continue
            assert "import numpy" not in s, f"{fn} 仍在 import numpy"
