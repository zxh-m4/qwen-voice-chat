# -*- coding: utf-8 -*-
"""Tkinter 窗口:状态栏 + 字幕区 + 连接控制。所有 Tk 更新都在主线程(after 轮询)。

界面语言(中/英,默认中文)走 rtchat/strings.py 字典;切换只改界面文字,不重连。
"""
from __future__ import annotations

import base64
import logging
import queue
import time
import tkinter as tk
from tkinter import scrolledtext, ttk


from . import strings, usage
from .audio_io import Microphone, Player, apply_gain
from .config import (
    DEFAULT_MIC_GAIN_LEVEL,
    MIC_GAIN_LEVELS,
    Config,
    load_config,
    mic_gain_factor,
    migrate_credentials_to_wincred,
    normalize_mic_gain_level,
    resolve_credentials_input,
    save_credentials,
    save_mic_gain_level,
    save_ui_language,
)
from .connection import RealtimeConnection
from .gate import SilenceGate
from .session import RealtimeSession

log = logging.getLogger(__name__)


def show_settings_dialog(
    parent, config_path: str, cfg: Config | None = None, lang: str = "zh"
) -> str | None:
    """凭据设置对话框(与 APK 版对齐):Key 与业务空间 ID 均打码且不回填,空输入沿用已存值。
    保存优先写入 Windows 凭据管理器,失败回退 config.local.json;返回存储位置("wincred"/"file"),取消返回 None。

    parent=None 时用作独立主窗口(首次启动场景,保证一定可见);
    parent=窗口 时作为其子窗(app 内「设置」按钮场景)。
    """
    ui = strings.UI[strings.normalize_language(lang)]

    def t(key: str) -> str:
        return ui[key]

    own_root = parent is None
    win = tk.Tk() if own_root else tk.Toplevel(parent)
    win.title(t("settings_title"))
    win.geometry("500x440")  # 内容构建完成后按实际需要自适应高度
    if own_root:
        try:
            win.attributes("-topmost", True)
            win.after(1200, lambda: win.attributes("-topmost", False))
        except Exception:
            pass
    ok = {"v": False}

    body = ttk.Frame(win, padding=16)
    body.pack(fill="both", expand=True)
    ttk.Label(body, text=t("settings_intro"), wraplength=450, justify="left").pack(anchor="w")

    ttk.Label(body, text=t("settings_key_label")).pack(anchor="w", pady=(12, 2))
    entry_key = ttk.Entry(body, show="*")
    entry_key.pack(fill="x")
    if cfg is not None and cfg.api_key:
        ttk.Label(body, text=t("settings_key_saved"), foreground="#888888").pack(
            anchor="w", pady=(2, 0)
        )

    ttk.Label(body, text=t("settings_ws_label")).pack(anchor="w", pady=(10, 2))
    entry_ws = ttk.Entry(body, show="*")  # 与 Key 同样打码:打开时不回填明文
    entry_ws.pack(fill="x")
    if cfg is not None and cfg.workspace_id:
        ttk.Label(body, text=t("settings_ws_saved"), foreground="#888888").pack(
            anchor="w", pady=(2, 0)
        )

    # ── 麦克风灵敏度:整体压低上传音量(端侧增益;配合"靠近麦克风 + 大声说")──
    ttk.Separator(body).pack(fill="x", pady=(14, 0))
    ttk.Label(body, text=t("settings_mic_label")).pack(anchor="w", pady=(10, 2))
    cur_level = (
        normalize_mic_gain_level(cfg.mic_gain_level) if cfg is not None else DEFAULT_MIC_GAIN_LEVEL
    )
    mic_var = tk.IntVar(value=cur_level)
    for lv in sorted(MIC_GAIN_LEVELS):
        ttk.Radiobutton(body, text=t(f"settings_mic_{lv}"), value=lv, variable=mic_var).pack(
            anchor="w", pady=1
        )
    ttk.Label(
        body, text=t("settings_mic_note"), foreground="#888888", wraplength=450, justify="left"
    ).pack(anchor="w", pady=(6, 0))

    msg = ttk.Label(body, text="", foreground="#c62828")
    msg.pack(anchor="w", pady=(6, 0))

    def on_save():
        key, ws, err = resolve_credentials_input(entry_key.get(), entry_ws.get(), cfg)
        if err:
            msg.config(text=t(f"settings_err_{err}"))
            return
        ok["loc"] = save_credentials(config_path, key, ws)
        save_mic_gain_level(config_path, mic_var.get())
        ok["v"] = True
        win.destroy()

    def on_cancel():
        win.destroy()

    btns = ttk.Frame(body)
    btns.pack(fill="x", pady=(14, 0))
    ttk.Button(btns, text=t("btn_save"), command=on_save).pack(side="right")
    ttk.Button(btns, text=t("btn_cancel"), command=on_cancel).pack(side="right", padx=(0, 8))

    # 内容增多(凭据 + 麦克风灵敏度七档):按实际所需高度自适应,并限制在屏幕内
    win.update_idletasks()
    max_h = int(win.winfo_screenheight() * 0.9)
    win.geometry(f"500x{min(max(win.winfo_reqheight(), 440), max_h)}")

    try:
        win.lift()
        win.focus_force()
    except Exception:
        pass
    if own_root:
        win.mainloop()
    else:
        parent.wait_window(win)
    return ok.get("loc")  # 保存成功返回存储位置("wincred"/"file"),取消返回 None


class ChatApp:
    POLL_MS = 50
    USAGE_REFRESH_S = 2.0

    def __init__(self, cfg: Config, config_path: str | None = None):
        self.config_path = config_path
        self.cfg = cfg
        self.lang = strings.normalize_language(cfg.ui_language)
        self.ui_q: queue.Queue = queue.Queue()
        self.player = Player(cfg.output_sample_rate)
        self.mic = Microphone(cfg.input_sample_rate, on_pcm=self._on_mic)
        self.mic_gain = mic_gain_factor(cfg.mic_gain_level)  # 「麦克风灵敏度」端侧增益系数
        self.gate = SilenceGate(
            threshold_rms=cfg.silence_threshold_rms,
            gate_ms=cfg.silence_gate_ms,
            frame_ms=cfg.frame_ms,
            enabled=cfg.silence_gate,
        )
        # 注:回声防护(EchoGuard)已按用户决策移除——保持全双工插话打断;
        # 外放回环由"戴耳机"解决(见使用说明)。代码保留于 rtchat/echo_guard.py 备查。
        self._mic_started = False
        self.meter = usage.UsageMeter()
        self._last_usage_ts = 0.0
        self._last_state = "connecting"

        self._build_session_and_conn()

        self._ai_open = False  # 当前 AI 文字行是否在流式追加
        self._last_stats_log = 0.0
        if self.config_path:
            try:
                migrate_credentials_to_wincred(self.config_path)  # 旧明文档 -> 凭据管理器(不删原文件)
            except Exception:
                log.exception("凭据迁移失败(忽略,不影响使用)")
        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_quit)
        self._connect()

    # ---------- 文案 ----------

    def _t(self, key: str) -> str:
        return strings.UI[self.lang][key]

    # ---------- 会话构建 ----------

    def _build_session_and_conn(self) -> None:
        """会话不可复用:首次与重连(角色切换/改凭据)统一走这里重建 session/conn。"""
        self.session = RealtimeSession(
            self.cfg,
            on_audio_delta=self._on_audio,
            on_user_transcript=lambda t: self.ui_q.put(("user_text", t)),
            on_assistant_text=lambda d: self.ui_q.put(("ai_delta", d)),
            on_state=self._on_session_state,
            on_error=lambda c, m: self.ui_q.put(("error", c, m)),
        )
        self.conn = RealtimeConnection(
            self.cfg,
            self.session,
            on_ui=lambda e: self.ui_q.put(("conn", e)),
            on_closed=lambda reason: self.ui_q.put(("closed", reason)),
        )

    def _on_audio(self, b64: str) -> None:
        """AI 音频下行:计费统计 + 播放。"""
        pcm = base64.b64decode(b64)
        self.meter.add_downlink(len(pcm), self.cfg.output_sample_rate)
        self.player.write(pcm)

    # ---------- UI 搭建 ----------

    def _build_ui(self) -> None:
        self.root = tk.Tk()
        self.root.title(self._t("app_title"))
        self.root.geometry("460x580")
        self.root.minsize(360, 420)

        top = ttk.Frame(self.root, padding=(10, 8))
        top.pack(fill="x")
        self.state_var = tk.StringVar(value=self._t("state_starting"))
        dot = ttk.Label(top, text="●", foreground="gray")
        dot.pack(side="left")
        ttk.Label(top, textvariable=self.state_var, font=("", 11, "bold")).pack(
            side="left", padx=(6, 0)
        )
        self.btn = ttk.Button(top, text=self._t("btn_disconnect"), command=self._toggle_conn)
        self.btn.pack(side="right")
        self.help_btn = ttk.Button(top, text=self._t("btn_help"), width=3, command=self._show_help)
        self.help_btn.pack(side="right", padx=(0, 4))
        if self.config_path:
            self.settings_btn = ttk.Button(
                top, text=self._t("btn_settings"), width=6, command=self._open_settings
            )
            self.settings_btn.pack(side="right", padx=(0, 4))
        self.lang_btn = ttk.Button(
            top, text=self._t("lang_button"), width=5, command=self._toggle_language
        )
        self.lang_btn.pack(side="right", padx=(0, 4))

        row2 = ttk.Frame(top)
        row2.pack(fill="x", pady=(6, 0))
        self.role_lbl = ttk.Label(row2, text=self._t("lbl_role"))
        self.role_lbl.pack(side="left")
        labels = strings.UI[self.lang]["presets"]
        self.preset_var = tk.StringVar(
            value=labels.get(self.cfg.active_preset, self.cfg.active_preset)
        )
        values = [labels.get(k, k) for k in self.cfg.presets] or [self.preset_var.get()]
        self.preset_combo = ttk.Combobox(
            row2, textvariable=self.preset_var, values=values, state="readonly", width=18
        )
        self.preset_combo.pack(side="left", padx=(4, 0))
        self.preset_combo.bind("<<ComboboxSelected>>", self._on_preset_change)

        self.transcript = scrolledtext.ScrolledText(
            self.root, wrap="word", state="disabled", font=("", 11), padx=10, pady=8
        )
        self.transcript.pack(fill="both", expand=True, padx=10, pady=(0, 6))
        self.transcript.tag_configure("user", foreground="#1a6fb5", spacing3=6)
        self.transcript.tag_configure("ai", foreground="#1f7a3d", spacing3=6)
        self.transcript.tag_configure("sys", foreground="#888888", font=("", 9))

        self.err_var = tk.StringVar(value="")
        ttk.Label(
            self.root, textvariable=self.err_var, foreground="#c62828",
            padding=(10, 0, 10, 4), anchor="w", wraplength=420,
        ).pack(fill="x")

        self.usage_var = tk.StringVar(value="")
        ttk.Label(
            self.root, textvariable=self.usage_var, foreground="#666666",
            padding=(10, 0, 10, 8), anchor="w",
        ).pack(fill="x")

    # ---------- 界面语言 ----------

    def _toggle_language(self) -> None:
        self.lang = "en" if self.lang == "zh" else "zh"
        if self.config_path:
            try:
                save_ui_language(self.config_path, self.lang)
            except Exception:
                log.exception("保存界面语言失败(忽略)")
        self._apply_language()
        self._sys(self._t("sys_language_switched"))

    def _apply_language(self) -> None:
        """切换语言后刷新全部界面文字(不重连、不清对话)。"""
        self.root.title(self._t("app_title"))
        self.state_var.set(strings.UI[self.lang]["states"].get(self._last_state, self._last_state))
        active = self.session.state in ("connecting", "ready", "speaking")
        self.btn.config(text=self._t("btn_disconnect") if active else self._t("btn_connect"))
        self.help_btn.config(text=self._t("btn_help"))
        self.lang_btn.config(text=self._t("lang_button"))
        if self.config_path:
            self.settings_btn.config(text=self._t("btn_settings"))
        self.role_lbl.config(text=self._t("lbl_role"))
        labels = strings.UI[self.lang]["presets"]
        self.preset_combo.config(
            values=[labels.get(k, k) for k in self.cfg.presets] or [self.preset_var.get()]
        )
        name = self.cfg.active_preset
        self.preset_var.set(labels.get(name, name))
        self._refresh_usage(force=True)

    # ---------- 连接控制 ----------

    def _connect(self) -> None:
        self.state_var.set(strings.UI[self.lang]["states"]["connecting"])
        self.err_var.set("")
        try:
            self.conn.connect()
        except Exception as e:
            self.err_var.set(self._t("err_connect_failed").format(e=e))

    def _toggle_conn(self) -> None:
        if self.session.state in ("connecting", "ready", "speaking"):
            self._disconnect()
            self.btn.config(text=self._t("btn_connect"))
        else:
            self._rebuild_connection()
            self._connect()
            self.btn.config(text=self._t("btn_disconnect"))

    def _rebuild_connection(self) -> None:
        """会话不可复用:断开后重建 session/conn(角色切换也走这里,换人设清上下文)。"""
        self._build_session_and_conn()

    def _on_preset_change(self, _event) -> None:
        labels = strings.UI[self.lang]["presets"]
        name = {v: k for k, v in labels.items()}.get(self.preset_var.get())
        if not name or name == self.cfg.active_preset:
            return
        self.cfg.active_preset = name
        self._sys(self._t("sys_preset_switched").format(name=self.preset_var.get()))
        self._disconnect()
        self._rebuild_connection()
        self._connect()
        self.btn.config(text=self._t("btn_disconnect"))

    def _disconnect(self) -> None:
        self._stop_mic()
        self.meter.end_session(time.time())
        self.player.stop()
        self.conn.close()
        self.state_var.set(strings.UI[self.lang]["states"]["closed"])

    def _open_settings(self) -> None:
        if not self.config_path:
            return
        loc = show_settings_dialog(self.root, self.config_path, self.cfg, lang=self.lang)
        if loc:
            self.cfg = load_config(self.config_path)
            self.mic_gain = mic_gain_factor(self.cfg.mic_gain_level)
            loc_text = self._t("loc_wincred") if loc == "wincred" else self._t("loc_file")
            self._sys(self._t("sys_credentials_updated").format(loc=loc_text))
            self._disconnect()
            self._rebuild_connection()
            self._connect()
            self.btn.config(text=self._t("btn_disconnect"))

    def _show_help(self) -> None:
        win = tk.Toplevel(self.root)
        win.title(self._t("help_title"))
        win.geometry("560x640")
        txt = scrolledtext.ScrolledText(win, wrap="word", font=("", 10), padx=14, pady=12)
        txt.pack(fill="both", expand=True)
        txt.insert("1.0", self._t("help"))
        txt.config(state="disabled")
        ttk.Button(win, text=self._t("btn_ok"), command=win.destroy).pack(pady=(0, 10))

    def _on_quit(self) -> None:
        try:
            self._disconnect()
        finally:
            self.conn.wait_closed(2.0)
            self.root.destroy()

    # ---------- 麦克风 / 状态回调(非主线程) ----------

    def _on_mic(self, pcm: bytes) -> None:
        if not self.gate.feed(pcm):  # 静音门:按原始音量判定(不受灵敏度影响),停发期省下输入 token
            return
        self.conn.feed_mic(apply_gain(pcm, self.mic_gain))  # 按灵敏度整体压低后上传

    def _on_session_state(self, state: str) -> None:
        if state == "interrupted":
            self.player.clear()  # 打断:立刻停播清队列
        if state == "ready" and not self._mic_started:
            self._start_mic()  # 握手完成,开麦开播
        self.ui_q.put(("state", state))

    def _start_mic(self) -> None:
        try:
            self.player.start()
            self.mic.start()
            self._mic_started = True
            self.meter.begin_session(time.time())
        except Exception as e:
            self.ui_q.put(("error", "audio", self._t("err_audio_open").format(e=e)))

    def _stop_mic(self) -> None:
        self._mic_started = False
        self.mic.stop()

    # ---------- 费用显示 ----------

    def _refresh_usage(self, force: bool = False) -> None:
        now = time.time()
        if not force and now - self._last_usage_ts < self.USAGE_REFRESH_S:
            return
        self._last_usage_ts = now
        self.usage_var.set(
            self._t("usage_format").format(
                s=self.meter.session_cost(now),
                t=self.meter.total_cost(now),
                mss=usage.format_mss(self.meter.session_secs(now)),
            )
        )

    # ---------- UI 事件循环(主线程) ----------

    def run(self) -> None:
        self.root.after(self.POLL_MS, self._poll)
        self.root.mainloop()

    def _poll(self) -> None:
        try:
            while True:
                self._dispatch(self.ui_q.get_nowait())
        except queue.Empty:
            pass
        self._refresh_usage()
        now = time.time()
        if now - self._last_stats_log >= 5:
            self._last_stats_log = now
            log.info(
                "stats: session=%s mic=%s | gate in=%d sent=%d | player cb=%d underrun=%d empty=%s",
                self.session.state, self._mic_started,
                self.gate.stats["frames_in"], self.gate.stats["frames_sent"],
                self.player.stats["callbacks"], self.player.stats["underrun_samples"],
                self.player.idle,
            )
        self.root.after(self.POLL_MS, self._poll)

    def _dispatch(self, item) -> None:
        kind = item[0]
        log.info("ui_event: %s", item[0])  # 只记事件类型,不把对话内容写进日志
        if kind == "state":
            self._last_state = item[1]
            self.state_var.set(strings.UI[self.lang]["states"].get(item[1], item[1]))
            if item[1] in ("ready", "connecting"):
                self._close_ai_line()
        elif kind == "user_text":
            self.meter.add_text(len(item[1] or ""), 0)
            self._append("user", f"{self._t('prefix_user')}{item[1]}\n")
            self._close_ai_line()
        elif kind == "ai_delta":
            self.meter.add_text(0, len(item[1] or ""))
            self._append_ai_delta(item[1])
        elif kind == "error":
            self.err_var.set(f"[{item[1]}] {item[2]}")
            if item[1] in ("quota", "403", "Authentication"):
                self._disconnect()
                self.btn.config(text=self._t("btn_connect"))
        elif kind == "conn":
            e = item[1]
            if e["type"] == "conn_error":
                self.err_var.set(self._t("err_conn_error").format(e=e["error"]))
            elif e["type"] == "conn_closed":
                self._sys(self._t("sys_conn_closed").format(reason=e["reason"]))
        elif kind == "closed":
            self._stop_mic()
            self.meter.end_session(time.time())
            self._close_ai_line()
            self._last_state = "closed"
            self.state_var.set(strings.UI[self.lang]["states"]["closed"])
            if item[1]:
                self._sys(self._t("sys_session_ended").format(reason=item[1]))
            self.btn.config(text=self._t("btn_connect"))

    def _append(self, tag: str, text: str) -> None:
        self.transcript.config(state="normal")
        self.transcript.insert("end", text, tag)
        self.transcript.see("end")
        self.transcript.config(state="disabled")

    def _append_ai_delta(self, delta: str) -> None:
        self.transcript.config(state="normal")
        if not self._ai_open:
            self.transcript.insert("end", self._t("prefix_ai"), "ai")
            self._ai_open = True
        self.transcript.insert("end", delta, "ai")
        self.transcript.see("end")
        self.transcript.config(state="disabled")

    def _close_ai_line(self) -> None:
        if self._ai_open:
            self._append("ai", "\n")
            self._ai_open = False

    def _sys(self, text: str) -> None:
        self._append("sys", f"— {text} —\n")
