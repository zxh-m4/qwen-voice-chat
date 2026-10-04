# -*- coding: utf-8 -*-
"""协议消息构建/解析的测试(依据阿里官方 realtime 文档与 OmniServerVad 示例)。"""
import base64

import pytest

from rtchat.config import Config
from rtchat.protocol import (
    ProtocolError,
    build_append,
    build_response_cancel,
    build_session_finish,
    build_session_update,
    parse_event,
)


@pytest.fixture
def cfg():
    return Config(api_key="sk-test")


class TestSessionUpdate:
    def test_core_fields(self, cfg):
        msg = build_session_update(cfg)
        assert msg["type"] == "session.update"
        s = msg["session"]
        assert s["modalities"] == ["text", "audio"]

    def test_audio_formats(self, cfg):
        s = build_session_update(cfg)["session"]
        assert s["audio"]["input"]["format"]["sample_rate"] == 16000
        assert s["audio"]["input"]["format"]["type"] == "pcm"
        assert s["audio"]["output"]["format"]["sample_rate"] == 24000
        assert s["audio"]["output"]["voice"] == "Tina"

    def test_turn_detection_and_transcription(self, cfg):
        s = build_session_update(cfg)["session"]
        assert s["turn_detection"]["type"] == "server_vad"
        assert s["turn_detection"]["interrupt_response"] is True
        assert s["input_audio_transcription"]["model"] == "gummy-realtime-v1"

    def test_manual_mode_when_vad_none(self):
        cfg = Config(api_key="sk-test", vad_type=None)
        assert build_session_update(cfg)["session"]["turn_detection"] is None

    def test_instructions_included(self):
        cfg = Config(api_key="sk-test", instructions="你好")
        assert build_session_update(cfg)["session"]["instructions"] == "你好"

    def test_custom_voice(self):
        cfg = Config(api_key="sk-test", voice="Ethan")
        s = build_session_update(cfg)["session"]
        assert s["audio"]["output"]["voice"] == "Ethan"


class TestClientEvents:
    def test_append_base64(self):
        pcm = b"\x01\x02\x03\x04"
        msg = build_append(pcm)
        assert msg["type"] == "input_audio_buffer.append"
        assert base64.b64decode(msg["audio"]) == pcm

    def test_cancel_and_finish(self):
        assert build_response_cancel() == {"type": "response.cancel"}
        assert build_session_finish() == {"type": "session.finish"}


class TestParseEvent:
    def test_parses_json_with_type(self):
        ev = parse_event('{"type":"response.done","delta":1}')
        assert ev["type"] == "response.done"
        assert ev["delta"] == 1

    def test_invalid_json_raises(self):
        with pytest.raises(ProtocolError):
            parse_event("{broken")

    def test_missing_type_raises(self):
        with pytest.raises(ProtocolError):
            parse_event('{"no": "type"}')
