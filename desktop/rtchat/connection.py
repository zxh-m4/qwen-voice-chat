# -*- coding: utf-8 -*-
"""WebSocket 连接层:收消息 -> 会话状态机 -> 回发动作;麦克风数据 -> append。"""
from __future__ import annotations

import json
import logging
import threading

from .config import Config
from .protocol import parse_event
from .session import RealtimeSession

log = logging.getLogger(__name__)


class RealtimeConnection:
    def __init__(self, cfg: Config, session: RealtimeSession, on_ui, on_closed):
        """
        on_ui(event: dict): 会话状态/文本/错误等 UI 事件,由调用方转投 UI 队列。
        on_closed(reason: str): 连接结束原因。
        """
        self._cfg = cfg
        self._session = session
        self._on_ui = on_ui
        self._on_closed = on_closed
        self._ws = None
        self._thread = None
        self._send_lock = threading.Lock()
        self._closed = False

    # -- 生命周期 --

    def connect(self) -> None:
        import websocket

        if self._thread and self._thread.is_alive():
            raise RuntimeError("连接已在进行中")
        self._closed = False
        self._ws = websocket.WebSocketApp(
            self._cfg.ws_url,
            header=[f"Authorization: Bearer {self._cfg.api_key}"],
            on_open=self._handle_open,
            on_message=self._handle_message,
            on_error=self._handle_error,
            on_close=self._handle_close,
        )
        self._thread = threading.Thread(
            target=self._ws.run_forever,
            kwargs={"ping_interval": 30, "ping_timeout": 10},
            daemon=True,
            name="rt-ws",
        )
        self._thread.start()

    def close(self) -> None:
        """主动结束:发 session.finish,关闭连接。可安全重复调用。"""
        if self._closed:
            return
        self._closed = True
        try:
            self._send(self._session.finish())
        except Exception:
            log.debug("发送 session.finish 失败(忽略)", exc_info=True)
        self._session.close()
        if self._ws is not None:
            try:
                self._ws.close()
            except Exception:
                log.debug("关闭 ws 失败(忽略)", exc_info=True)

    def wait_closed(self, timeout: float = 5.0) -> None:
        if self._thread:
            self._thread.join(timeout)

    # -- 麦克风方向 --

    def feed_mic(self, pcm: bytes) -> None:
        try:
            actions = self._session.feed_audio(pcm)
        except RuntimeError:
            return  # 会话未就绪时丢弃,不打断录音回调
        for msg in actions:
            self._send(msg)

    # -- WebSocket 回调(均在 ws 线程) --

    def _handle_open(self, ws):
        log.info("WebSocket 已连接")

    def _handle_message(self, ws, raw):
        try:
            msg = parse_event(raw)
        except Exception as e:
            log.warning("解析失败: %s", e)
            return
        t = msg.get("type")
        if t != "response.audio.delta":  # delta 每 40ms 一条,不进日志
            log.info("<< %s", t)
        try:
            for out in self._session.handle_event(msg):
                log.info(">> %s", out.get("type"))
                self._send(out)
        except Exception:
            log.exception("处理事件失败: %s", t)

    def _handle_error(self, ws, error):
        if not self._closed:
            self._on_ui({"type": "conn_error", "error": str(error)})

    def _handle_close(self, ws, status_code, msg):
        if not self._closed:
            self._on_ui({"type": "conn_closed", "reason": f"{status_code} {msg}".strip()})
        self._on_closed(f"{status_code} {msg}".strip())

    def _send(self, msg: dict) -> None:
        data = json.dumps(msg, ensure_ascii=False)
        with self._send_lock:
            if self._ws is None:
                raise RuntimeError("连接未建立")
            self._ws.send(data)
