# -*- coding: utf-8 -*-
"""Tkinter 窗口:状态栏 + 字幕区 + 连接控制。所有 Tk 更新都在主线程(after 轮询)。"""
from __future__ import annotations

import logging
import os
import queue
import time
import tkinter as tk
from tkinter import scrolledtext, ttk


from .audio_io import Microphone, Player
from .config import Config, load_config, save_local_credentials
from .connection import RealtimeConnection
from .gate import SilenceGate
from .paths import app_dir
from .session import RealtimeSession
from .voice_gate import VoicePrintGate, make_embedder

log = logging.getLogger(__name__)

STATE_LABELS = {
    "connecting": "连接中…",
    "ready": "聆听中",
    "speaking": "说话中",
    "interrupted": "已打断 · 聆听中",
    "closed": "已断开",
}

PRESET_LABELS = {
    "english_teacher": "英语老师",
    "japanese_teacher": "日语老师",
    "russian_teacher": "俄语老师",
    "chinese_teacher": "中文老师",
    "spanish_teacher": "西班牙语老师",
    "french_teacher": "法语老师",
    "korean_teacher": "韩语老师",
    "german_teacher": "德语老师",
}
LABELS_PRESET = {v: k for k, v in PRESET_LABELS.items()}


def show_settings_dialog(parent, config_path: str, cfg: Config | None = None) -> bool:
    """凭据设置对话框(与 APK 版对齐):Key 打码且不回填;保存到 config.local.json。

    parent=None 时用作独立主窗口(首次启动场景,保证一定可见);
    parent=窗口 时作为其子窗(app 内「设置」按钮场景)。
    """
    own_root = parent is None
    win = tk.Tk() if own_root else tk.Toplevel(parent)
    win.title("配置百炼凭据")
    win.geometry("500x400")
    if own_root:
        try:
            win.attributes("-topmost", True)
            win.after(1200, lambda: win.attributes("-topmost", False))
        except Exception:
            pass
    ok = {"v": False}

    body = ttk.Frame(win, padding=16)
    body.pack(fill="both", expand=True)
    ttk.Label(
        body,
        text="本应用不含任何 API Key。请填入你自己的阿里云百炼凭据"
             "(仅保存在本机 config.local.json,不会随程序分享):",
        wraplength=450, justify="left",
    ).pack(anchor="w")

    ttk.Label(body, text="API Key(百炼控制台 → API-KEY 管理 → 创建)").pack(anchor="w", pady=(12, 2))
    entry_key = ttk.Entry(body, show="*")
    entry_key.pack(fill="x")
    if cfg is not None and cfg.api_key:
        ttk.Label(body, text="已保存(如需更换,请输入新的 Key)", foreground="#888888").pack(anchor="w", pady=(2, 0))

    ttk.Label(body, text="业务空间 ID(百炼控制台 → 业务空间列表,形如 llm-xxxxxxxx)").pack(anchor="w", pady=(10, 2))
    entry_ws = ttk.Entry(body)
    entry_ws.pack(fill="x")
    if cfg is not None and cfg.workspace_id:
        entry_ws.insert(0, cfg.workspace_id)

    msg = ttk.Label(body, text="", foreground="#c62828")
    msg.pack(anchor="w", pady=(6, 0))

    def on_save():
        key = entry_key.get().strip()
        ws = entry_ws.get().strip()
        if not key and cfg is not None and cfg.api_key:
            key = cfg.api_key  # 未输入则沿用已保存
        if not key:
            msg.config(text="请填写 API Key(sk- 开头)")
            return
        if not key.startswith("sk-"):
            msg.config(text="API Key 应以 sk- 开头")
            return
        if not ws:
            msg.config(text="请填写业务空间 ID(形如 llm-xxxxxxxx)")
            return
        from .config import save_local_credentials as _save

        _save(config_path, key, ws)
        ok["v"] = True
        win.destroy()

    def on_cancel():
        win.destroy()

    btns = ttk.Frame(body)
    btns.pack(fill="x", pady=(14, 0))
    ttk.Button(btns, text="保存", command=on_save).pack(side="right")
    ttk.Button(btns, text="取消", command=on_cancel).pack(side="right", padx=(0, 8))

    try:
        win.lift()
        win.focus_force()
    except Exception:
        pass
    if own_root:
        win.mainloop()
    else:
        parent.wait_window(win)
    return ok["v"]


HELP_TEXT = """本应用是为了创造一个外语学习的语境环境,是本人的业余学习中第一次完成的应用,完全免费分享,如有疏漏之处,敬请见谅。
—— 笑晗

【声明】
本应用为个人业余学习作品,与阿里云及通义官方无关;使用需自备阿里云百炼账号与 API Key,调用费用由使用者自行承担;本应用免费分享、仅供学习交流,请勿用于商业用途;代码以 MIT 许可开源,欢迎自由修改与二次开发;作者预计不再频繁更新,欢迎有兴趣的朋友接力完善。

【快速开始】
1. 双击打开窗口,自动连接,看到「聆听中」直接开口说话
2. 说完话(停约 1 秒)它自动回复;它说话时你开口可以打断
3. 顶部下拉可切换角色,切换即开始新对话(上下文重置)
4. 右上角按钮可断开/重连;关闭窗口即友好结束

【八种语言】(下拉切换,切换即开始新对话;每位老师锁定自己的语言——无论你说什么语言,老师都用该语言回复,仅明确说「用中文解释/翻译」才切中文;中文老师反之,用英文解释)
· 英语老师 Tina · 日语老师 Ono Anna · 俄语老师 Katerina · 中文老师 Tina
· 西班牙语老师 Sonrisa · 法语老师 Emilien · 韩语老师 Sohee · 德语老师 Ingrid
(音色不合口味?百炼官方音色表有试听,换一行配置即可)

【小提示】
· 回环问题:外放时它可能听到自己的声音(甚至打断自己)——请戴耳机使用即可解决(本程序不做自动回声防护,以保证你随时可以插话打断)
· API Key 与业务空间 ID 在程序目录 config.json 中配置
· 运行日志在程序目录 app.log(排障用)
· 计费:约 0.4 元/小时,基本只在说话时产生;关闭窗口即停止计费
"""


class ChatApp:
    POLL_MS = 50
    _PLAYBACK_REF_BYTES = 96000  # ~2s @24kHz PCM16,黑名单基准的提取粒度

    def __init__(self, cfg: Config, config_path: str | None = None):
        self.config_path = config_path
        self.cfg = cfg
        self.ui_q: queue.Queue = queue.Queue()
        self.player = Player(cfg.output_sample_rate)
        self.mic = Microphone(cfg.input_sample_rate, on_pcm=self._on_mic)
        self._playback_buf = bytearray()
        self.gate = SilenceGate(
            threshold_rms=cfg.silence_threshold_rms,
            gate_ms=cfg.silence_gate_ms,
            frame_ms=cfg.frame_ms,
            enabled=cfg.silence_gate,
        )
        self.vp_gate = self._build_voice_gate(cfg)
        # 注:回声防护(EchoGuard)已按用户决策移除——保持全双工插话打断;
        # 外放回环由"戴耳机"解决(见使用说明)。代码保留于 rtchat/echo_guard.py 备查。
        self._mic_started = False

        self.session = RealtimeSession(
            cfg,
            on_audio_delta=self._on_audio,
            on_user_transcript=lambda t: self.ui_q.put(("user_text", t)),
            on_assistant_text=lambda d: self.ui_q.put(("ai_delta", d)),
            on_state=self._on_session_state,
            on_error=lambda c, m: self.ui_q.put(("error", c, m)),
        )
        self.conn = RealtimeConnection(
            cfg,
            self.session,
            on_ui=lambda e: self.ui_q.put(("conn", e)),
            on_closed=lambda reason: self.ui_q.put(("closed", reason)),
        )

        self._ai_open = False  # 当前 AI 文字行是否在流式追加
        self._last_stats_log = 0.0
        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_quit)
        self._connect()

    # ---------- 声纹门(黑名单:只挡 AI 回声) ----------

    @staticmethod
    def _build_voice_gate(cfg: Config) -> VoicePrintGate | None:
        """模型缺失或加载失败时返回 None(直通,fail-open)。"""
        if not cfg.voiceprint_enabled:
            log.info("声纹门:配置关闭,直通")
            return None
        model_path = cfg.voiceprint_model or os.path.join(
            app_dir(), "models", "3dspeaker_speech_campplus_sv_zh-cn_16k-common.onnx"
        )
        if not os.path.isfile(model_path):
            log.info("声纹门:模型缺失(%s),直通", model_path)
            return None
        gate = VoicePrintGate(
            embedder=None,  # 先建壳,模型加载成功后注入
            threshold=cfg.voiceprint_threshold,
            buffer_ms=cfg.voiceprint_buffer_ms,
            frame_ms=cfg.frame_ms,
            threshold_rms=cfg.silence_threshold_rms,
        )
        embedder = make_embedder(model_path)
        if embedder is None:
            return None  # 加载失败,make_embedder 已记日志
        gate._embedder = embedder
        log.info(
            "声纹门 ON(黑名单制):阈值 %.2f,基准来源=AI 播放音频实时提取",
            cfg.voiceprint_threshold,
        )
        return gate

    @staticmethod
    def _resample_int16(pcm: bytes, sr_in: int, sr_out: int) -> bytes:
        """int16 单声道线性重采样(替代 Python 3.13 已移除的 audioop.ratecv)。"""
        import numpy as np

        if sr_in == sr_out or not pcm:
            return pcm
        a = np.frombuffer(pcm, dtype=np.int16).astype(np.float32)
        if a.size == 0:
            return pcm
        n_out = int(a.size * sr_out / sr_in)
        if n_out <= 0:
            return b""
        idx = np.linspace(0.0, a.size - 1, n_out)
        out = np.interp(idx, np.arange(a.size), a)
        return out.astype(np.int16).tobytes()

    def _on_audio(self, b64: str) -> None:
        """AI 音频下行:播放 + 回声打点 + (声纹门开启时)收集黑名单基准。"""
        self.player.write_b64(b64)
        if self.vp_gate is None or not self.vp_gate.enabled:
            return
        try:
            import base64

            self._playback_buf.extend(base64.b64decode(b64))
            if len(self._playback_buf) >= self._PLAYBACK_REF_BYTES:
                pcm24k = bytes(self._playback_buf)
                self._playback_buf.clear()
                pcm16k = self._resample_int16(pcm24k, self.cfg.output_sample_rate, 16000)
                emb = self.vp_gate.embed(pcm16k)
                if emb is not None:
                    self.vp_gate.add_reference(emb)
        except Exception:
            log.exception("提取 AI 音色基准失败(忽略)")

    # ---------- UI 搭建 ----------

    def _build_ui(self) -> None:
        self.root = tk.Tk()
        self.root.title("实时外语对话 · Qwen Omni")
        self.root.geometry("460x560")
        self.root.minsize(360, 400)

        top = ttk.Frame(self.root, padding=(10, 8))
        top.pack(fill="x")
        self.state_var = tk.StringVar(value="启动中…")
        dot = ttk.Label(top, text="●", foreground="gray")
        dot.pack(side="left")
        ttk.Label(top, textvariable=self.state_var, font=("", 11, "bold")).pack(
            side="left", padx=(6, 0)
        )
        self.btn = ttk.Button(top, text="断开", command=self._toggle_conn)
        self.btn.pack(side="right")
        self.help_btn = ttk.Button(top, text="?", width=3, command=self._show_help)
        self.help_btn.pack(side="right", padx=(0, 4))
        if self.config_path:
            self.settings_btn = ttk.Button(top, text="设置", width=5, command=self._open_settings)
            self.settings_btn.pack(side="right", padx=(0, 4))

        row2 = ttk.Frame(top)
        row2.pack(fill="x", pady=(6, 0))
        ttk.Label(row2, text="角色:").pack(side="left")
        self.preset_var = tk.StringVar(
            value=PRESET_LABELS.get(self.cfg.active_preset, self.cfg.active_preset)
        )
        values = [PRESET_LABELS.get(k, k) for k in self.cfg.presets] or [self.preset_var.get()]
        self.preset_combo = ttk.Combobox(
            row2, textvariable=self.preset_var, values=values, state="readonly", width=16
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
            padding=(10, 0, 10, 8), anchor="w", wraplength=420,
        ).pack(fill="x")

    # ---------- 连接控制 ----------

    def _connect(self) -> None:
        self.state_var.set(STATE_LABELS["connecting"])
        self.err_var.set("")
        try:
            self.conn.connect()
        except Exception as e:
            self.err_var.set(f"连接失败:{e}")

    def _toggle_conn(self) -> None:
        if self.session.state in ("connecting", "ready", "speaking"):
            self._disconnect()
            self.btn.config(text="连接")
        else:
            self._rebuild_connection()
            self._connect()
            self.btn.config(text="断开")

    def _rebuild_connection(self) -> None:
        """会话不可复用:断开后重建 session/conn(角色切换也走这里,换人设清上下文)。"""
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

    def _on_preset_change(self, _event) -> None:
        name = LABELS_PRESET.get(self.preset_var.get())
        if not name or name == self.cfg.active_preset:
            return
        self.cfg.active_preset = name
        self._sys(f"已切换角色:{self.preset_var.get()}(开始新对话)")
        self._disconnect()
        self._rebuild_connection()
        self._connect()
        self.btn.config(text="断开")

    def _disconnect(self) -> None:
        self._stop_mic()
        self.player.stop()
        self.conn.close()
        self.state_var.set(STATE_LABELS["closed"])

    def _open_settings(self) -> None:
        if not self.config_path:
            return
        if show_settings_dialog(self.root, self.config_path, self.cfg):
            self.cfg = load_config(self.config_path)
            self._sys("凭据已更新,重新连接")
            self._disconnect()
            self._rebuild_connection()
            self._connect()
            self.btn.config(text="断开")

    def _show_help(self) -> None:
        win = tk.Toplevel(self.root)
        win.title("使用说明")
        win.geometry("540x620")
        txt = scrolledtext.ScrolledText(win, wrap="word", font=("", 10), padx=14, pady=12)
        txt.pack(fill="both", expand=True)
        txt.insert("1.0", HELP_TEXT)
        txt.config(state="disabled")
        ttk.Button(win, text="知道了", command=win.destroy).pack(pady=(0, 10))

    def _on_quit(self) -> None:
        try:
            self._disconnect()
        finally:
            self.conn.wait_closed(2.0)
            self.root.destroy()

    # ---------- 麦克风 / 状态回调(非主线程) ----------

    def _on_mic(self, pcm: bytes) -> None:
        if not self.gate.feed(pcm):  # 静音门:停发期省下输入 token
            return
        if self.vp_gate is not None:  # 声纹门(默认关):黑名单制备用
            for f in self.vp_gate.feed(pcm):
                self.conn.feed_mic(f)
        else:
            self.conn.feed_mic(pcm)

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
        except Exception as e:
            self.ui_q.put(("error", "audio", f"音频设备打开失败:{e}"))

    def _stop_mic(self) -> None:
        self._mic_started = False
        self.mic.stop()

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
            self.state_var.set(STATE_LABELS.get(item[1], item[1]))
            if item[1] in ("ready", "connecting"):
                self._close_ai_line()
        elif kind == "user_text":
            self._append("user", f"你:{item[1]}\n")
            self._close_ai_line()
        elif kind == "ai_delta":
            self._append_ai_delta(item[1])
        elif kind == "error":
            self.err_var.set(f"[{item[1]}] {item[2]}")
            if item[1] in ("quota", "403", "Authentication"):
                self._disconnect()
                self.btn.config(text="连接")
        elif kind == "conn":
            e = item[1]
            if e["type"] == "conn_error":
                self.err_var.set(f"连接错误:{e['error']}")
            elif e["type"] == "conn_closed":
                self._sys(f"连接关闭:{e['reason']}")
        elif kind == "closed":
            self._stop_mic()
            self._close_ai_line()
            self.state_var.set(STATE_LABELS["closed"])
            if item[1]:
                self._sys(f"会话结束:{item[1]}")
            self.btn.config(text="连接")

    def _append(self, tag: str, text: str) -> None:
        self.transcript.config(state="normal")
        self.transcript.insert("end", text, tag)
        self.transcript.see("end")
        self.transcript.config(state="disabled")

    def _append_ai_delta(self, delta: str) -> None:
        self.transcript.config(state="normal")
        if not self._ai_open:
            self.transcript.insert("end", "AI:", "ai")
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
