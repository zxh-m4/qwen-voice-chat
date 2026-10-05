# -*- coding: utf-8 -*-
"""费用估算(与安卓版同口径):下行按真实音频帧折算秒数,上行按连接时长,
文本按字符数近似 token。仅用于界面提示,准确账单以百炼控制台为准。
"""
from __future__ import annotations

# 公开费率(与安卓版 AoqChatManager.Rate 一致):
# 音频入 7 tok/s × 6 元/百万 = 42e-6 元/秒;音频出 12.5 tok/s × 12 元/百万 = 150e-6 元/秒;
# 文本 1.5 / 4.5 元每百万 token
RATE_AUDIO_IN = 7 * 6 / 1_000_000
RATE_AUDIO_OUT = 12.5 * 12 / 1_000_000
RATE_TEXT_IN = 1.5 / 1_000_000
RATE_TEXT_OUT = 4.5 / 1_000_000
CHARS_PER_TEXT_TOKEN = 2.0  # 中文字符数的粗估折算


def estimate_cost(
    uplink_secs: float, downlink_secs: float, text_in_chars: int, text_out_chars: int
) -> float:
    return (
        uplink_secs * RATE_AUDIO_IN
        + downlink_secs * RATE_AUDIO_OUT
        + text_in_chars / CHARS_PER_TEXT_TOKEN * RATE_TEXT_IN
        + text_out_chars / CHARS_PER_TEXT_TOKEN * RATE_TEXT_OUT
    )


def format_mss(secs: int) -> str:
    """秒 -> m:ss(分钟不封顶)。"""
    secs = max(0, int(secs))
    return f"{secs // 60}:{secs % 60:02d}"


class UsageMeter:
    """「本次」= 当前会话;「累计」= 进程级(退出清零,断开/换老师不清零)。

    上行按连接时长实时增长(与安卓版口径一致),下行与文本为累计值。
    """

    def __init__(self) -> None:
        self._total = 0.0            # 已结算的历史会话成本
        self._fixed = 0.0            # 当前会话已累计的下行+文本部分
        self._start: float | None = None
        self._down_secs = 0.0
        self._text_in = 0
        self._text_out = 0

    # ---------- 会话生命周期 ----------

    def begin_session(self, now: float) -> None:
        if self._start is not None:
            self.end_session(now)  # 未结算的上一会话先并入累计,不丢账
        self._start = now
        self._fixed = 0.0
        self._down_secs = 0.0
        self._text_in = 0
        self._text_out = 0

    def end_session(self, now: float) -> None:
        if self._start is None:
            return
        self._total += self.session_cost(now)
        self._start = None
        self._fixed = 0.0
        self._down_secs = 0.0
        self._text_in = 0
        self._text_out = 0

    # ---------- 数据累计 ----------

    def add_downlink(self, nbytes: int, sample_rate: int = 24000) -> None:
        """下行按真实音频帧折算(与安卓版同口径),而不是按帧数假设。"""
        secs = nbytes / 2 / sample_rate
        self._down_secs += secs
        self._add(secs * RATE_AUDIO_OUT)

    def add_text(self, chars_in: int, chars_out: int) -> None:
        self._text_in += chars_in
        self._text_out += chars_out
        self._add(
            chars_in / CHARS_PER_TEXT_TOKEN * RATE_TEXT_IN
            + chars_out / CHARS_PER_TEXT_TOKEN * RATE_TEXT_OUT
        )

    def _add(self, cost: float) -> None:
        if self._start is None:
            self._total += cost  # 无活动会话的迟到数据并入累计,不丢账
        else:
            self._fixed += cost

    # ---------- 查询(显示用,now 由调用方传入便于测试) ----------

    def session_cost(self, now: float) -> float:
        if self._start is None:
            return 0.0
        return self._fixed + (now - self._start) * RATE_AUDIO_IN

    def total_cost(self, now: float) -> float:
        return self._total + self.session_cost(now)

    def session_secs(self, now: float) -> int:
        return 0 if self._start is None else int(now - self._start)
