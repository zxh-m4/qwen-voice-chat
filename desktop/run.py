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


def configure_logging(log_path: str) -> None:
    """日志:1MB 轮转、保留 1 个备份(长会话日志有界;与安卓版"超限清理"同目的)。

    注意:轮转模式为追加,不再像旧版那样每次启动清空——跨启动保留更利于排障,
    上限 2MB(app.log + app.log.1)。
    """
    from logging.handlers import RotatingFileHandler

    handler = RotatingFileHandler(
        log_path, maxBytes=1_000_000, backupCount=1, encoding="utf-8"
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for h in list(root.handlers):
        root.removeHandler(h)
        try:
            h.close()
        except Exception:
            pass
    root.addHandler(handler)


def main() -> int:
    parser = argparse.ArgumentParser(description="实时中英语音对话(Qwen Omni Realtime)")
    parser.add_argument(
        "--config",
        default=os.path.join(app_dir(), "config.json"),
        help="配置文件路径(默认:程序目录 config.json)",
    )
    args = parser.parse_args()

    configure_logging(os.path.join(app_dir(), "app.log"))

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
