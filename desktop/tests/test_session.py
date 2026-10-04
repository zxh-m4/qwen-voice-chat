# -*- coding: utf-8 -*-
"""会话状态机的测试——打断逻辑、事件分发、状态通知(核心逻辑,无网络依赖)。"""
import pytest

from rtchat.config import Config
from rtchat.session import RealtimeSession


@pytest.fixture
def calls():
    """收集 session 各回调的记录器。"""
    class Rec:
        def __init__(self):
            self.audio = []
            self.user_text = []
            self.assistant_text = []
            self.states = []
            self.errors = []

        def on_audio(self, b64):
            self.audio.append(b64)

        def on_user_transcript(self, text):
            self.user_text.append(text)

        def on_assistant_text(self, text):
            self.assistant_text.append(text)

        def on_state(self, state):
            self.states.append(state)

        def on_error(self, code, message):
            self.errors.append((code, message))

    return Rec()


@pytest.fixture
def session(calls):
    return RealtimeSession(Config(api_key="sk-test"), **{
        "on_audio_delta": calls.on_audio,
        "on_user_transcript": calls.on_user_transcript,
        "on_assistant_text": calls.on_assistant_text,
        "on_state": calls.on_state,
        "on_error": calls.on_error,
    })


class TestHandshake:
    def test_created_replies_session_update(self, session):
        out = session.handle_event({"type": "session.created"})
        assert len(out) == 1
        assert out[0]["type"] == "session.update"

    def test_updated_moves_to_ready(self, session, calls):
        session.handle_event({"type": "session.created"})
        out = session.handle_event({"type": "session.updated"})
        assert out == []
        assert session.state == "ready"
        assert calls.states == ["ready"]

    def test_append_before_ready_raises(self, session):
        with pytest.raises(RuntimeError):
            session.feed_audio(b"\x00" * 3200)


class TestAudioFeeding:
    def test_ready_state_emits_append_per_frame(self, session):
        session.handle_event({"type": "session.created"})
        session.handle_event({"type": "session.updated"})
        out = session.feed_audio(b"\x01" * 3200)
        assert len(out) == 1
        assert out[0]["type"] == "input_audio_buffer.append"

    def test_partial_frames_buffered(self, session):
        session.handle_event({"type": "session.created"})
        session.handle_event({"type": "session.updated"})
        assert session.feed_audio(b"\x01" * 100) == []
        out = session.feed_audio(b"\x01" * 3100)
        assert len(out) == 1


class TestBargeIn:
    def test_speech_started_with_active_response_cancels(self, session, calls):
        session.handle_event({"type": "session.created"})
        session.handle_event({"type": "session.updated"})
        session.handle_event({"type": "response.created"})
        out = session.handle_event({"type": "input_audio_buffer.speech_started"})
        assert any(m["type"] == "response.cancel" for m in out)
        assert "interrupted" in calls.states

    def test_speech_started_without_response_no_cancel(self, session, calls):
        session.handle_event({"type": "session.created"})
        session.handle_event({"type": "session.updated"})
        out = session.handle_event({"type": "input_audio_buffer.speech_started"})
        assert out == []

    def test_cancel_sent_once_per_response(self, session):
        session.handle_event({"type": "session.created"})
        session.handle_event({"type": "session.updated"})
        session.handle_event({"type": "response.created"})
        first = session.handle_event({"type": "input_audio_buffer.speech_started"})
        second = session.handle_event({"type": "input_audio_buffer.speech_started"})
        assert any(m["type"] == "response.cancel" for m in first)
        assert second == []


class TestResponseFlow:
    def test_audio_delta_forwarded(self, session, calls):
        session.handle_event({"type": "response.created"})
        session.handle_event({"type": "response.audio.delta", "delta": "AAA"})
        assert calls.audio == ["AAA"]

    def test_speaking_state_enter_and_exit(self, session, calls):
        session.handle_event({"type": "response.created"})
        assert session.state == "speaking"
        session.handle_event({"type": "response.done"})
        assert session.state == "ready"
        assert "speaking" in calls.states
        assert calls.states[-1] == "ready"

    def test_assistant_transcript_delta(self, session, calls):
        session.handle_event({"type": "response.audio_transcript.delta", "delta": "你"})
        session.handle_event({"type": "response.audio_transcript.delta", "delta": "好"})
        assert "".join(calls.assistant_text) == "你好"

    def test_user_transcript_completed(self, session, calls):
        session.handle_event(
            {"type": "conversation.item.input_audio_transcription.completed",
             "transcript": "hello"}
        )
        assert calls.user_text == ["hello"]

    def test_response_cancelled_resets_active(self, session):
        session.handle_event({"type": "response.created"})
        session.handle_event({"type": "response.done"})
        # 活动响应结束后,再次 speech_started 不应再发 cancel
        assert session.handle_event({"type": "input_audio_buffer.speech_started"}) == []


class TestErrorHandling:
    def test_error_event_reported_not_raised(self, session, calls):
        session.handle_event(
            {"type": "error", "error": {"code": "quota", "message": "no quota"}}
        )
        assert calls.errors == [("quota", "no quota")]

    def test_unknown_event_ignored(self, session):
        assert session.handle_event({"type": "some.future.event"}) == []
