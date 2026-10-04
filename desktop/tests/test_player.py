# -*- coding: utf-8 -*-
"""播放回调数据完整性的测试:跨回调残余必须保留,不许丢弃。"""
import base64

import numpy as np

from rtchat.audio_io import Player


def make_player() -> Player:
    return Player(24000)  # 不 start(),直接调 _callback,不碰声卡


def outdata(frames: int) -> np.ndarray:
    return np.zeros((frames, 1), dtype=np.int16)


class TestCallbackIntegrity:
    def test_chunk_split_across_callbacks_keeps_tail(self):
        """一条 1920B 的 delta 分两次取(每次 960B):第二次必须拿到后半,而非静音。"""
        p = make_player()
        p.write_b64(base64.b64encode(b"\x01\x02" * 960).decode())  # 1920B
        od1, od2 = outdata(480), outdata(480)
        p._callback(od1, 480, None, None)
        p._callback(od2, 480, None, None)
        assert od1.tobytes() == b"\x01\x02" * 480
        assert od2.tobytes() == b"\x01\x02" * 480  # bug 修复前:全零(后半被丢)

    def test_two_chunks_concatenated_without_loss(self):
        """两个 chunk 顺序播放:总字节数不丢不重(400B = 160+160+80)。"""
        p = make_player()
        p.write(b"\xaa\xbb" * 100)  # 200B
        p.write(b"\xcc\xdd" * 100)  # 200B
        got = bytearray()
        for frames in (80, 80, 40):  # need = 160 + 160 + 80 = 400B
            od = outdata(frames)
            p._callback(od, frames, None, None)
            got.extend(od.tobytes())
        assert bytes(got) == b"\xaa\xbb" * 100 + b"\xcc\xdd" * 100

    def test_underrun_fills_silence_and_counts(self):
        p = make_player()
        od = np.full((480, 1), 0x7F7F, dtype=np.int16)  # 预填垃圾,应被清零
        p._callback(od, 480, None, None)
        assert od.tobytes() == b"\x00" * 960
        assert p.stats["underrun_samples"] == 480

    def test_clear_resets_pending(self):
        p = make_player()
        p.write(b"\x01\x02" * 1000)  # 2000B
        od = outdata(480)
        p._callback(od, 480, None, None)  # 取 960B,残余 1040B 在 pending
        p.clear()
        od2 = outdata(480)
        p._callback(od2, 480, None, None)
        assert od2.tobytes() == b"\x00" * 960  # clear 后不再吐旧数据
