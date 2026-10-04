# -*- coding: utf-8 -*-
"""会话状态机:把服务端事件翻译成动作与回调,不碰网络与设备(可完全单测)。

上层(WebSocket 线程 / 录音线程)的用法:
- 收到服务端消息 -> parse_event -> session.handle_event(msg) -> 得到待发送消息列表
- 采到麦克风数据 -> session.feed_audio(pcm) -> 得到待发送的 append 消息列表
"""
from __future__ import annotations

from typing import Callable, Optional

from .config import Config
from .frames import FrameSplitter
from .protocol import (
    build_append,
    build_response_cancel,
    build_session_finish,
    build_session_update,
)

OnAudio = Callable[[str], None]
OnText = Callable[[str], None]
OnState = Callable[[str], None]
OnError = Callable[[str, str], None]


class RealtimeSession:
    """状态: connecting -> ready <-> speaking;出错走回调,不抛。"""

    def __init__(
        self,
        cfg: Config,
        on_audio_delta: OnAudio,
        on_user_transcript: OnText,
        on_assistant_text: OnText,
        on_state: OnState,
        on_error: OnError,
    ):
        self._cfg = cfg
        self._splitter = FrameSplitter(cfg.frame_bytes)
        self._on_audio = on_audio_delta
        self._on_user_text = on_user_transcript
        self._on_assistant_text = on_assistant_text
        self._on_state = on_state
        self._on_error = on_error
        self._state = "connecting"
        self._active_response = False

    # -- 状态 --

    @property
    def state(self) -> str:
        return self._state

    @property
    def active_response(self) -> bool:
        return self._active_response

    def _set_state(self, state: str) -> None:
        if state != self._state:
            self._state = state
            self._on_state(state)

    # -- 麦克风方向 --

    def feed_audio(self, pcm: bytes) -> list[dict]:
        if self._state not in ("ready", "speaking"):
            raise RuntimeError(f"会话未就绪(当前 {self._state}),不能发送音频")
        return [build_append(f) for f in self._splitter.feed(pcm)]

    # -- 服务端事件 --

    def handle_event(self, msg: dict) -> list[dict]:
        """处理一条服务端事件,返回需要回发的事件列表。"""
        etype = msg.get("type", "")
        if etype == "session.created":
            return [build_session_update(self._cfg)]
        if etype == "session.updated":
            self._set_state("ready")
            return []
        if etype == "input_audio_buffer.speech_started":
            return self._on_speech_started()
        if etype == "response.created":
            self._active_response = True
            self._set_state("speaking")
            return []
        if etype == "response.audio.delta":
            delta = msg.get("delta")
            if delta:
                self._on_audio(delta)
            return []
        if etype == "response.audio_transcript.delta":
            if msg.get("delta"):
                self._on_assistant_text(msg["delta"])
            return []
        if etype == "conversation.item.input_audio_transcription.completed":
            if msg.get("transcript"):
                self._on_user_text(msg["transcript"])
            return []
        if etype == "response.done":
            self._active_response = False
            if self._state == "speaking":
                self._set_state("ready")
            return []
        if etype == "error":
            err = msg.get("error") or {}
            self._on_error(str(err.get("code", "unknown")), str(err.get("message", "")))
            return []
        return []

    def _on_speech_started(self) -> list[dict]:
        """用户开口:清播放(由上层通过 on_state('interrupted') 触发)并取消活动响应。"""
        out: list[dict] = []
        if self._active_response:
            self._active_response = False
            self._on_state("interrupted")  # 上层据此清空播放队列
            out.append(build_response_cancel())
            if self._state == "speaking":
                self._set_state("ready")
        return out

    # -- 结束 --

    def finish(self) -> dict:
        self._splitter.reset()
        return build_session_finish()

    def close(self) -> None:
        self._splitter.reset()
        self._active_response = False
        self._state = "closed"
