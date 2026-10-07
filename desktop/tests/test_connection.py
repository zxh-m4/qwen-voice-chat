# -*- coding: utf-8 -*-
"""连接层:主动关闭后不得再上报 closed 事件。

复现的真实场景(v1.5 用户实测):设置里改「麦克风灵敏度」→ 保存 → 代码主动断开旧连接
并立即重建、重连;旧连接的 on_close 回调**迟到触发**,若无条件上报,
会把已经 ready 的新连接状态刷成"已断开"(表现为"明明连着却显示断开")。
"""
from rtchat.config import Config
from rtchat.connection import RealtimeConnection


class FakeSession:
    """最小会话替身:只需要能被 close()。"""

    def close(self):
        pass


def make_conn():
    events = {"ui": [], "closed": []}
    conn = RealtimeConnection(
        Config(api_key="sk-test"),
        FakeSession(),
        on_ui=lambda e: events["ui"].append(e),
        on_closed=lambda r: events["closed"].append(r),
    )
    return conn, events


class TestCloseCallback:
    def test_intentional_close_does_not_report(self):
        conn, events = make_conn()
        conn._closed = True  # 模拟 close() 之后旧连接的回调才到达
        conn._handle_close(None, 1000, "normal")
        assert events["closed"] == []
        assert events["ui"] == []

    def test_passive_close_still_reports(self):
        conn, events = make_conn()
        conn._handle_close(None, 1006, "abnormal")
        assert events["closed"] == ["1006 abnormal"]
        assert events["ui"] and events["ui"][0]["type"] == "conn_closed"

    def test_late_messages_ignored_after_close(self):
        conn, events = make_conn()
        conn._closed = True
        conn._handle_message(None, '{"type":"session.updated","session":{}}')
        assert events["ui"] == []
        assert events["closed"] == []
