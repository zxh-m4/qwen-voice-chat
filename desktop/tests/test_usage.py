# -*- coding: utf-8 -*-
"""费用估算(与安卓版同口径:下行按真实帧折算 + 上行按连接时长 + 文本近似)。"""
import pytest

from rtchat.usage import (
    CHARS_PER_TEXT_TOKEN,
    RATE_AUDIO_IN,
    RATE_AUDIO_OUT,
    RATE_TEXT_IN,
    RATE_TEXT_OUT,
    UsageMeter,
    estimate_cost,
    format_mss,
)


class TestRates:
    def test_rate_constants_match_public_pricing(self):
        # 音频入 7 tok/s × 6 元/百万;出 12.5 tok/s × 12 元/百万
        assert RATE_AUDIO_IN == pytest.approx(7 * 6 / 1_000_000)
        assert RATE_AUDIO_OUT == pytest.approx(12.5 * 12 / 1_000_000)
        # 文本 1.5 / 4.5 元每百万 token
        assert RATE_TEXT_IN == pytest.approx(1.5 / 1_000_000)
        assert RATE_TEXT_OUT == pytest.approx(4.5 / 1_000_000)
        assert CHARS_PER_TEXT_TOKEN == 2.0


class TestEstimateCost:
    def test_zero(self):
        assert estimate_cost(0, 0, 0, 0) == 0.0

    def test_uplink_only(self):
        assert estimate_cost(100, 0, 0, 0) == pytest.approx(100 * 7 * 6 / 1e6)

    def test_downlink_only(self):
        assert estimate_cost(0, 60, 0, 0) == pytest.approx(60 * 12.5 * 12 / 1e6)

    def test_text_chars(self):
        assert estimate_cost(0, 0, 100, 0) == pytest.approx(50 * 1.5 / 1e6)
        assert estimate_cost(0, 0, 0, 100) == pytest.approx(50 * 4.5 / 1e6)

    def test_combined(self):
        got = estimate_cost(10, 20, 40, 60)
        want = (10 * 7 * 6 + 20 * 12.5 * 12 + 20 * 1.5 + 30 * 4.5) / 1e6
        assert got == pytest.approx(want)


class TestUsageMeter:
    def test_initial_zero(self):
        m = UsageMeter()
        assert m.session_cost(now=100.0) == 0.0
        assert m.total_cost(now=100.0) == 0.0
        assert m.session_secs(now=100.0) == 0

    def test_uplink_accrues_with_time(self):
        m = UsageMeter()
        m.begin_session(now=100.0)
        assert m.session_cost(now=110.0) == pytest.approx(10 * 7 * 6 / 1e6)
        assert m.session_secs(now=110.0) == 10

    def test_downlink_bytes_folded_by_real_frames(self):
        m = UsageMeter()
        m.begin_session(now=0.0)
        # 24000Hz PCM16 单声道:48000 字节 = 1 秒
        m.add_downlink(48000, sample_rate=24000)
        assert m.session_cost(now=0.0) == pytest.approx(12.5 * 12 / 1e6)

    def test_text_chars(self):
        m = UsageMeter()
        m.begin_session(now=0.0)
        m.add_text(200, 0)  # 100 token 入
        m.add_text(0, 100)  # 50 token 出
        assert m.session_cost(now=0.0) == pytest.approx((100 * 1.5 + 50 * 4.5) / 1e6)

    def test_end_finalizes_into_total_and_clears_session(self):
        m = UsageMeter()
        m.begin_session(now=0.0)
        m.end_session(now=10.0)
        c1 = 10 * 7 * 6 / 1e6
        assert m.session_cost(now=999.0) == 0.0
        assert m.total_cost(now=999.0) == pytest.approx(c1)
        assert m.session_secs(now=999.0) == 0

    def test_total_spans_sessions(self):
        m = UsageMeter()
        m.begin_session(now=0.0)
        m.end_session(now=10.0)
        m.begin_session(now=100.0)
        assert m.session_cost(now=100.0) == 0.0                      # 本次归零
        assert m.total_cost(now=100.0) == pytest.approx(10 * 7 * 6 / 1e6)  # 累计保留
        assert m.total_cost(now=105.0) == pytest.approx(15 * 7 * 6 / 1e6)  # 累计含进行中会话

    def test_begin_without_end_finalizes_previous(self):
        # 重连/切老师直接再 begin:上一会话先并入累计,不丢账
        m = UsageMeter()
        m.begin_session(now=0.0)
        m.begin_session(now=10.0)
        assert m.total_cost(now=10.0) == pytest.approx(10 * 7 * 6 / 1e6)
        assert m.session_secs(now=10.0) == 0

    def test_end_without_session_is_noop(self):
        m = UsageMeter()
        m.end_session(now=5.0)
        assert m.total_cost(now=5.0) == 0.0

    def test_add_without_active_session_goes_to_total(self):
        # 无活动会话时的迟到数据不许丢
        m = UsageMeter()
        m.add_downlink(48000, sample_rate=24000)
        assert m.total_cost(now=0.0) == pytest.approx(12.5 * 12 / 1e6)


class TestFormatMss:
    def test_basic(self):
        assert format_mss(0) == "0:00"
        assert format_mss(75) == "1:15"
        assert format_mss(3661) == "61:01"
