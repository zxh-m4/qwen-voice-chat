# -*- coding: utf-8 -*-
"""静音门测试:静音停发省钱,滞回保证服务端 VAD 断句不受影响,有声秒恢复。"""
import struct

from rtchat.gate import SilenceGate


def silence(ms: int, frame_ms: int = 100) -> list[bytes]:
    n = ms // frame_ms
    return [b"\x00\x00" * 1600] * n


def tone(rms_target: int, ms: int, frame_ms: int = 100) -> list[bytes]:
    """生成近似 rms_target 的方波帧(16bit 单声道 16k,100ms=1600 样本)。"""
    n = ms // frame_ms
    frames = []
    for _ in range(n):
        samples = struct.pack("<" + "h" * 1600, *([rms_target, -rms_target] * 800))
        frames.append(samples)
    return frames


class TestRms:
    def test_silence_is_zero(self):
        assert SilenceGate.rms(b"\x00\x00" * 100) == 0

    def test_square_wave_rms_equals_amplitude(self):
        assert abs(SilenceGate.rms(tone(1000, 100)[0]) - 1000) <= 1

    def test_rms_known_value(self):
        data = tone(500, 100)[0]
        assert abs(SilenceGate.rms(data) - 500) <= 1


class TestSilenceGate:
    def make(self, gate_ms=1500, threshold=250):
        return SilenceGate(threshold_rms=threshold, gate_ms=gate_ms, frame_ms=100)

    def test_initial_silence_not_sent(self):
        g = self.make()
        assert all(g.feed(f) is False for f in silence(1000))

    def test_tone_always_sent(self):
        g = self.make()
        assert all(g.feed(f) is True for f in tone(800, 1000))

    def test_hysteresis_keeps_sending_then_stops(self):
        """高能量后转静音:1500ms 内继续发,之后停。"""
        g = self.make(gate_ms=1500)
        for f in tone(800, 200):
            assert g.feed(f)
        silent = silence(3000)
        sent = [g.feed(f) for f in silent]
        assert all(sent[:15])      # 前 1500ms(15 帧)照发 -> VAD 断句不受影响
        assert not any(sent[15:])  # 之后停发,挂机不再烧钱

    def test_recovers_on_voice_immediately(self):
        g = self.make(gate_ms=1500)
        for f in tone(800, 200):
            g.feed(f)
        for f in silence(5000):
            g.feed(f)
        assert g.feed(tone(800, 100)[0]) is True  # 停发后一有声音立即恢复

    def test_short_pause_never_stops(self):
        """说话间隙(短于 gate_ms)不打断发送,时间轴连续。"""
        g = self.make(gate_ms=1500)
        for f in tone(800, 300) + silence(1000) + tone(800, 300):
            assert g.feed(f) is True

    def test_threshold_boundary(self):
        assert self.make(threshold=250).feed(tone(250, 100)[0]) is True   # 等于阈值算有声
        assert self.make(threshold=250).feed(tone(249, 100)[0]) is False   # 初始低于阈值不发
        # 激活后低于阈值走滞回:gate_ms 内仍发(这属于"说话间隙")
        g = self.make(threshold=250)
        g.feed(tone(800, 100)[0])
        assert g.feed(tone(249, 100)[0]) is True

    def test_enabled_false_always_sends(self):
        g = SilenceGate(threshold_rms=250, gate_ms=1500, frame_ms=100, enabled=False)
        assert all(g.feed(f) for f in silence(1000))
