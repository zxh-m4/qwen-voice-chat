# -*- coding: utf-8 -*-
"""声纹门(黑名单制)的段状态机测试——只挡 AI 的合成音,任何人声都放行。

接口:feed(frame) -> list[bytes](本帧应上传的音频,放行时含补发缓冲)。
黑名单基准 = AI 正在播放的音频的嵌入(运行时提取,空则全放行)。
"""
import numpy as np

from rtchat.voice_gate import VoicePrintGate

FRAME = b"\x01\x02" * 1600  # 100ms 帧(3200B)


def frame_at(rms: int) -> bytes:
    import struct

    return struct.pack("<" + "h" * 1600, *([rms, -rms] * 800))


def make(black_sim=0.9, human_sim=0.1, threshold=0.45, buffer_ms=500, **kw):
    """嵌入 mock:按缓冲首帧幅度分档(>500 视为 AI 回声,否则人声)。"""
    gate = VoicePrintGate(
        embedder=None, threshold=threshold, buffer_ms=buffer_ms, frame_ms=100, **kw
    )
    gate.black_sim = black_sim
    gate.human_sim = human_sim

    def embed(pcm: bytes):
        import struct

        samples = struct.unpack("<1600h", pcm[:3200])
        peak = max(abs(s) for s in samples)
        sim = gate.black_sim if peak > 500 else gate.human_sim
        return np.array([sim], dtype=np.float32)

    gate._embed = embed  # 覆盖内部判定用嵌入
    return gate


class TestBypass:
    def test_disabled_always_passes(self):
        g = make(enabled=False)
        assert all(g.feed(FRAME) == [FRAME] for _ in range(20))

    def test_no_blacklist_passes_everything(self):
        """还没建立 AI 音色基准(AI 没说过话)时,一切放行。"""
        g = make()
        assert all(g.feed(FRAME) == [FRAME] for _ in range(20))


class TestAIVoiceBlocked:
    def test_ai_echo_dropped_entire_segment(self):
        """与黑名单基准高度相似(AI 回声)-> 整段丢弃。"""
        g = make()
        g.add_reference(np.array([1.0], dtype=np.float32))
        outs = [g.feed(frame_at(800)) for _ in range(8)]
        assert all(o == [] for o in outs)
        assert g.state == "blocked"

    def test_reference_added_during_playback(self):
        """基准可运行时累积(AI 播放音频边播边提)。"""
        g = make()
        g.add_reference(np.array([1.0], dtype=np.float32))
        g.add_reference(np.array([0.9], dtype=np.float32))
        assert len(g.references) == 2

    def test_reference_capped(self):
        g = make()
        for i in range(20):
            g.add_reference(np.array([float(i)], dtype=np.float32))
        assert len(g.references) <= 5


class TestHumanVoicePasses:
    def test_human_voice_passes_and_replays(self):
        """人声(与黑名单不相似)-> 放行,缓冲补发不吞字。"""
        g = make()
        g.add_reference(np.array([-1.0], dtype=np.float32))  # 与 mock 输出(0.1)反相关
        outs = [g.feed(frame_at(800)) for _ in range(5)]
        assert all(o == [] for o in outs[:4])
        assert outs[4] == [frame_at(800)] * 5
        assert g.feed(frame_at(800)) == [frame_at(800)]

    def test_anyone_passes_not_only_owner(self):
        """不同的人声都放行(黑名单只认 AI 音色)。"""
        g = make()
        g.add_reference(np.array([-1.0], dtype=np.float32))
        for peak in (600, 2000, 8000):  # 轻声/正常/大声,都是"人声"
            g2_state_reset = VoicePrintGate(
                embedder=None, threshold=0.45, buffer_ms=500, frame_ms=100
            )
            g2_state_reset._embed = g._embed
            g2_state_reset.add_reference(np.array([-1.0], dtype=np.float32))
            outs = [g2_state_reset.feed(frame_at(peak)) for _ in range(5)]
            assert outs[4] != []


class TestSegmentLifecycle:
    def test_new_segment_after_silence_rejudges(self):
        g = make()
        g.add_reference(np.array([-1.0], dtype=np.float32))
        for _ in range(5):
            g.feed(frame_at(800))
        for _ in range(8):
            g.feed(frame_at(20))
        assert g.state == "idle"
        outs = [g.feed(frame_at(800)) for _ in range(5)]
        assert outs[4] == [frame_at(800)] * 5

    def test_blocked_segment_stays_blocked_until_silence(self):
        g = make()
        g.add_reference(np.array([1.0], dtype=np.float32))
        for _ in range(6):
            assert g.feed(frame_at(800)) == []
        for _ in range(8):
            g.feed(frame_at(20))
        assert g.state == "idle"


class TestDegradation:
    def test_embedder_error_fails_open(self):
        g = make()
        g.add_reference(np.array([1.0], dtype=np.float32))

        def boom(pcm):
            raise RuntimeError("down")

        g._embed = boom
        outs = [g.feed(frame_at(800)) for _ in range(6)]
        assert outs[4] == [frame_at(800)] * 5
        assert g.feed(frame_at(800)) == [frame_at(800)]
