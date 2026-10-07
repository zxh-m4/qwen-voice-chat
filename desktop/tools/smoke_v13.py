# -*- coding: utf-8 -*-
"""v1.3 PC 冒烟:双语切换 / 费用行 / 设置对话框双打码(自动化检查,不碰真实凭据)。

用法:python smoke_v13.py
用假 key + 临时 config 启动窗口(不发真实网络请求),自动检查后退出。
"""
import json
import os
import sys
import tempfile
import tkinter as tk
from tkinter import ttk

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # desktop/
sys.path.insert(0, BASE_DIR)

from rtchat import connection  # noqa: E402
from rtchat.app import ChatApp, show_settings_dialog  # noqa: E402
from rtchat.config import load_config  # noqa: E402

REAL_CONFIG = os.path.join(BASE_DIR, "config.json")


def all_widgets(w):
    yield w
    for c in w.winfo_children():
        yield from all_widgets(c)


def make_fake_config():
    """临时 config:拷贝真实 presets 段(不含凭据)+ 假 api_key。"""
    presets = {}
    try:
        with open(REAL_CONFIG, encoding="utf-8") as f:
            data = json.load(f)
        presets = data.get("presets", {})
    except Exception:
        pass
    tmp = tempfile.mkdtemp(prefix="smoke_v13_")
    path = os.path.join(tmp, "config.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"api_key": "sk-smoke-not-real", "presets": presets}, f,
                  ensure_ascii=False, indent=2)
    return path


def main() -> int:
    connection.RealtimeConnection.connect = lambda self: None  # 不发真实请求
    cfg_path = make_fake_config()
    cfg = load_config(cfg_path)
    app = ChatApp(cfg, config_path=cfg_path)
    results = []

    def check(tag, value):
        results.append((tag, value))

    def kill_dialog():
        for w in app.root.winfo_children():
            if isinstance(w, tk.Toplevel):
                entries = [x for x in all_widgets(w) if isinstance(x, ttk.Entry)]
                check("dlg_title", w.title())
                check("dlg_entries", len(entries))
                check("dlg_entry_show", [e.cget("show") for e in entries])
                w.destroy()

    def flow():
        # 1) 默认中文
        check("zh_title", app.root.title())
        check("zh_btn", app.btn.cget("text"))
        check("zh_role", app.role_lbl.cget("text"))
        check("zh_usage", app.usage_var.get())
        # 2) 切英文
        app._toggle_language()
        check("en_title", app.root.title())
        check("en_btn", app.btn.cget("text"))
        check("en_role", app.role_lbl.cget("text"))
        check("en_combo", list(app.preset_combo.cget("values"))[:2])
        check("en_usage", app.usage_var.get())
        check("en_lang_btn", app.lang_btn.cget("text"))
        # 3) 英文界面下的设置对话框(600ms 后自动关闭)
        app.root.after(600, kill_dialog)
        loc = show_settings_dialog(app.root, cfg_path, app.cfg, lang="en")
        check("dlg_loc", loc)
        # 4) 切回中文并复查
        app._toggle_language()
        check("back_title", app.root.title())
        check("back_lang_btn", app.lang_btn.cget("text"))
        # 检查帮助文本占位
        check("help_has_cost", "【费用说明】" in app._t("help"))
        check("help_en_ok", "[Cost]" in __import__("rtchat.strings", fromlist=["UI"]).UI["en"]["help"])
        app.root.destroy()

    app.root.after(400, flow)
    app.run()

    print("=" * 56)
    for k, v in results:
        print(f"{k:16} = {v}")
    print("=" * 56)

    ok = (
        results[0][1] == "实时外语对话 · Qwen Omni"          # zh_title
        and "本次" in results[3][1] and "累计" in results[3][1]   # zh_usage
        and results[4][1] == "Realtime Voice Chat · Qwen Omni"   # en_title
        and results[5][1] == "Disconnect"                    # en_btn
        and "English Tutor" in results[7][1]                 # en_combo
        and "This ¥" in results[8][1]                        # en_usage
        and results[9][1] == "中文"                          # en_lang_btn
        and results[10][1] == "Bailian Credentials"          # dlg_title
        and results[11][1] == 2                              # dlg_entries
        and all(s == "*" for s in results[12][1])            # dlg_entry_show
        and results[14][1] == "实时外语对话 · Qwen Omni"      # back_title
        and results[15][1] == "EN"                           # back_lang_btn
        and results[16][1] is True                           # help_has_cost
        and results[17][1] is True                           # help_en_ok
    )
    print("SMOKE:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
