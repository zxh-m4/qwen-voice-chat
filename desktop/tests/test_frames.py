# -*- coding: utf-8 -*-
"""PCM 帧切分与播放队列的测试。"""
from rtchat.frames import FrameSplitter, PlaybackQueue


class TestFrameSplitter:
    def test_exact_single_frame(self):
        sp = FrameSplitter(frame_bytes=3200)
        assert sp.feed(b"x" * 3200) == [b"x" * 3200]
        assert sp.pending == 0

    def test_multiple_frames_and_remainder(self):
        sp = FrameSplitter(frame_bytes=3200)
        frames = sp.feed(b"y" * 8000)
        assert len(frames) == 2
        assert sp.pending == 1600

    def test_remainder_flushes_after_more_data(self):
        sp = FrameSplitter(frame_bytes=3200)
        assert sp.feed(b"a" * 4000) == [b"a" * 3200]  # 余 800
        # 800 + 5000 = 5800 -> 出 1 帧(800a+2400b),余 2600
        assert sp.feed(b"b" * 5000) == [b"a" * 800 + b"b" * 2400]
        assert sp.pending == 2600

    def test_small_chunk_held_back(self):
        sp = FrameSplitter(frame_bytes=3200)
        assert sp.feed(b"z" * 100) == []
        assert sp.pending == 100

    def test_empty_feed(self):
        sp = FrameSplitter(frame_bytes=3200)
        assert sp.feed(b"") == []

    def test_reset_clears_pending(self):
        sp = FrameSplitter(frame_bytes=3200)
        sp.feed(b"z" * 100)
        sp.reset()
        assert sp.pending == 0


class TestPlaybackQueue:
    def test_put_then_drain_in_order(self):
        q = PlaybackQueue()
        q.write(b"aa")
        q.write(b"bb")
        assert q.drain() == [b"aa", b"bb"]

    def test_drain_empty_returns_empty(self):
        assert PlaybackQueue().drain() == []

    def test_clear_empties_queue(self):
        q = PlaybackQueue()
        q.write(b"aa")
        q.write(b"bb")
        q.clear()
        assert q.drain() == []

    def test_write_decodes_base64(self):
        import base64

        q = PlaybackQueue()
        q.write_b64(base64.b64encode(b"pcm").decode())
        assert q.drain() == [b"pcm"]

    def test_is_empty_property(self):
        q = PlaybackQueue()
        assert q.is_empty
        q.write(b"x")
        assert not q.is_empty
