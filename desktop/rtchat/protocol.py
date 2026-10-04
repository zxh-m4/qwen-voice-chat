# -*- coding: utf-8 -*-
"""Realtime WebSocket 协议消息构建与解析(依据阿里官方 realtime 文档)。"""
from __future__ import annotations

import base64
import json

from .config import Config


class ProtocolError(Exception):
    """消息不是合法的协议事件。"""


def build_session_update(cfg: Config) -> dict:
    """会话初始化:模态、音色、VAD、用户语音转写、选中预设的提示词与联网开关。"""
    session: dict = {
        "modalities": ["text", "audio"],
        "instructions": cfg.active_instructions,
        "enable_search": cfg.active_search,
        "audio": {
            "input": {
                "format": {
                    "type": "pcm",
                    "sample_rate": cfg.input_sample_rate,
                    "sample_format": "s16le",
                    "channels": 1,
                }
            },
            "output": {
                "voice": cfg.active_voice,
                "format": {"type": "pcm", "sample_rate": cfg.output_sample_rate},
            },
        },
    }
    if cfg.vad_type is None:
        session["turn_detection"] = None
    else:
        session["turn_detection"] = {
            "type": cfg.vad_type,
            "interrupt_response": True,
            "create_response": True,
            "silence_duration_ms": cfg.vad_silence_ms,
        }
    session["input_audio_transcription"] = (
        {"model": cfg.transcription_model} if cfg.transcription_model else None
    )
    if cfg.active_search and cfg.active_search_source:
        session["search_options"] = {"enable_source": True}
    return {"type": "session.update", "session": session}


def build_append(pcm: bytes) -> dict:
    return {
        "type": "input_audio_buffer.append",
        "audio": base64.b64encode(pcm).decode("ascii"),
    }


def build_response_cancel() -> dict:
    return {"type": "response.cancel"}


def build_session_finish() -> dict:
    return {"type": "session.finish"}


def parse_event(raw: str) -> dict:
    """解析服务端事件;非法 JSON 或缺 type 都视为协议错误。"""
    try:
        msg = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as e:
        raise ProtocolError(f"无法解析的服务端消息: {raw[:200]!r}") from e
    if not isinstance(msg, dict) or "type" not in msg:
        raise ProtocolError(f"服务端消息缺少 type 字段: {raw[:200]!r}")
    return msg
