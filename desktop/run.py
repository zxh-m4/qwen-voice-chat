# -*- coding: utf-8 -*-
"""实时外语对话窗口入口:python run.py [--config config.json]"""
import argparse
import logging
import os
import sys

from rtchat.paths import app_dir


def _configure_via_dialog(config_path: str, err: str):
    """配置错误时:缺 api_key -> 弹设置窗口(独立主窗口,保证可见)让用户填;其他错误 -> 错误提示。"""
    try:
        import tkinter as tk
        from tkinter import messagebox

        from rtchat.app import show_settings_dialog
        from rtchat.config import ConfigError, load_config

        if "api_key" not in err:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("配置错误", err)
            root.destroy()
            return None
        if not show_settings_dialog(None, config_path):
            return None
        try:
            return load_config(config_path)
        except ConfigError as e2:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("配置错误", str(e2))
            root.destroy()
            return None
    except Exception:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="实时中英语音对话(Qwen Omni Realtime)")
    parser.add_argument(
        "--config",
        default=os.path.join(app_dir(), "config.json"),
        help="配置文件路径(默认:程序目录 config.json)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        filename=os.path.join(app_dir(), "app.log"),
        filemode="w",
    )

    from rtchat.app import ChatApp
    from rtchat.config import ConfigError, load_config

    try:
        cfg = load_config(args.config)
    except ConfigError as e:
        print(f"配置错误: {e}", file=sys.stderr)
        # 缺凭据 -> 弹设置窗口(与 APK 版对齐);其他错误 -> 弹错误提示
        cfg = _configure_via_dialog(args.config, str(e))
        if cfg is None:
            return 3

    app = ChatApp(cfg, config_path=args.config)
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
