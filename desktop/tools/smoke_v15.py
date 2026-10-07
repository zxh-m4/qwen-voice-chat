# -*- coding: utf-8 -*-
"""v1.5 PC 冒烟:设置对话框「麦克风灵敏度」五档(自动检查,不碰真实凭据、不发网络请求)。

用法:python tools/smoke_v15.py
用假 key + 临时 config 启动窗口;自动检查五档单选、默认值、保存落盘、重开回读,然后退出。
"""
import json
import os
import sys
import tempfile
import tkinter as tk
from tkinter import ttk

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # desktop/
sys.path.insert(0, BASE_DIR)

from rtchat import app as app_mod  # noqa: E402
from rtchat import connection  # noqa: E402
from rtchat.app import ChatApp, show_settings_dialog  # noqa: E402
from rtchat.config import load_config  # noqa: E402

REAL_CONFIG = os.path.join(BASE_DIR, "config.json")


def all_widgets(w):
    yield w
    for c in w.winfo_children():
        yield from all_widgets(c)


def make_fake_config():
    presets = {}
    try:
        with open(REAL_CONFIG, encoding="utf-8") as f:
            presets = json.load(f).get("presets", {})
    except Exception:
        pass
    tmp = tempfile.mkdtemp(prefix="smoke_v15_")
    path = os.path.join(tmp, "config.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            {"api_key": "sk-smoke-not-real", "workspace_id": "llm-smoke", "presets": presets},
            f,
            ensure_ascii=False,
            indent=2,
        )
    return path


def main() -> int:
    connection.RealtimeConnection.connect = lambda self: None  # 不发真实请求
    app_mod.save_credentials = lambda *a, **k: "file"  # 冒烟不写真实凭据库
    cfg_path = make_fake_config()
    cfg = load_config(cfg_path)
    app = ChatApp(cfg, config_path=cfg_path)
    results = []

    def check(tag, value):
        results.append((tag, value))

    check("app_mic_gain_initial", app.mic_gain)  # 默认档 1 → 系数 1.0(原样)

    def find_dialog():
        for w in app.root.winfo_children():
            if isinstance(w, tk.Toplevel):
                return w
        return None

    def act_select_and_save():
        w = find_dialog()
        if w is None:
            return
        radios = [x for x in all_widgets(w) if isinstance(x, ttk.Radiobutton)]
        check("radios_n", len(radios))
        check("radios_text_zh", [r.cget("text") for r in radios])
        var = radios[0].cget("variable")
        check("initial", str(w.getvar(var)))  # 默认 1
        radios[6].invoke()  # 选「极限」(-40 dB):验证最狠的新档位
        check("after", str(w.getvar(var)))
        save_btn = next(
            b for b in all_widgets(w) if isinstance(b, ttk.Button) and b.cget("text") == "保存"
        )
        save_btn.invoke()

    def act_reopen_check_then_cancel():
        w = find_dialog()
        if w is None:
            return
        radios = [x for x in all_widgets(w) if isinstance(x, ttk.Radiobutton)]
        check("radios_text_en", [r.cget("text") for r in radios])
        var = radios[0].cget("variable")
        check("reopen", str(w.getvar(var)))  # 回读 3
        cancel_btn = next(
            b for b in all_widgets(w) if isinstance(b, ttk.Button) and b.cget("text") == "Cancel"
        )
        cancel_btn.invoke()

    def flow():
        # 第一次:中文界面,默认 1 → 选「中」→ 保存
        app.root.after(500, act_select_and_save)
        loc1 = show_settings_dialog(app.root, cfg_path, app.cfg, lang="zh")
        check("loc1", loc1)
        with open(cfg_path, encoding="utf-8") as f:
            check("saved_level", json.load(f).get("mic_gain_level"))
        app.cfg = load_config(cfg_path)
        # 第二次:英文界面,重开应回读;取消关闭
        app.root.after(500, act_reopen_check_then_cancel)
        loc2 = show_settings_dialog(app.root, cfg_path, app.cfg, lang="en")
        check("loc2", loc2)
        app.root.destroy()

    app.root.after(400, flow)
    app.run()

    print("=" * 56)
    for k, v in results:
        print(f"{k:18} = {v}")
    print("=" * 56)

    def get(key):
        return next(v for k, v in results if k == key)

    zh = get("radios_text_zh")
    en = get("radios_text_en")
    ok = (
        get("app_mic_gain_initial") == 1.0  # 默认 0 dB
        and get("radios_n") == 7
        and any("很高" in x for x in zh)
        and any("极限" in x for x in zh)
        and get("initial") == "1"
        and get("after") == "7"
        and get("loc1") == "file"
        and get("saved_level") == 7
        and any("Very high" in x for x in en)
        and any("Maximum" in x for x in en)
        and get("reopen") == "7"
        and get("loc2") is None
    )
    print("SMOKE:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
