# -*- coding: utf-8 -*-
"""回声防护门(EchoGuard)测试:AI 播放期间不上传,结束后宽限 300ms 恢复。

这是"挡住 AI 端声音"的物理级方案(2026-10-02 定稿):
声纹黑名单实测区分度不足(回环 vp=0.10 vs 人声 0.01),改为播放期间直接停收——
回环无从产生;任何人声零影响。
"""
from rtchat.echo_guard import EchoGuard


class TestEchoGuard:
    def test_idle_at_start_allows(self):
        """从未播放过:放行。"""
        g = EchoGuard(idle_fn=lambda: True)
        assert g.allow() is True

    def test_blocks_while_playing(self):
        g = EchoGuard(idle_fn=lambda: False)
        assert g.allow() is False

    def test_grace_period_after_playback_ends(self):
        """播放刚结束的宽限期(声卡残余)内仍丢弃。"""
        clock = {"t": 0.0}
        g = EchoGuard(idle_fn=lambda: True, clock=lambda: clock["t"], grace=0.3)
        g.allow()  # 建立基线
        clock["t"] = 0.1
        # 模拟:播放了 5 秒后停止
        g.on_playback()  # 等价于 idle 变 False 的最后时刻
        assert g.allow() is False  # 宽限内

    def test_allows_after_grace(self):
        clock = {"t": 0.0}
        g = EchoGuard(idle_fn=lambda: True, clock=lambda: clock["t"], grace=0.3)
        g.allow()
        g.on_playback()
        clock["t"] = 0.31
        assert g.allow() is True

    def test_reblocks_when_playing_again(self):
        clock = {"t": 0.0}
        g = EchoGuard(idle_fn=lambda: False, clock=lambda: clock["t"], grace=0.3)
        assert g.allow() is False
