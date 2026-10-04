# -*- coding: utf-8 -*-
"""回声防护门:AI 播放期间麦克风数据不上传,物理性消除外放回环。

实测依据(2026-10-02):声纹黑名单区分度不足——回环经扬声器/空气失真后
声纹得分仅 0.10,与人声(≈0.01)无判决间隔;而"播放中停收"是 100% 可靠的:
回环根本到不了云端,且任何人声零参与、零影响。
宽限期:播放结束后声卡缓冲还有残余声音,默认再静默 300ms。
"""
from __future__ import annotations

import time
from typing import Callable


class EchoGuard:
    def __init__(self, idle_fn: Callable[[], bool], clock: Callable[[], float] = time.monotonic, grace: float = 0.3):
        """
        idle_fn: 播放队列是否已空(True=没在播)。
        clock:   时间源(测试可注入)。
        grace:   播放结束后的残余宽限秒数。
        """
        self._idle_fn = idle_fn
        self._clock = clock
        self._grace = grace
        self._last_active: float | None = None
        self.stats = {"blocked": 0}

    def on_playback(self) -> None:
        """播放数据到达时打点(与 idle_fn 双保险,防队列瞬间为空的误判)。"""
        self._last_active = self._clock()

    def allow(self) -> bool:
        """当前麦克风数据是否允许上传。"""
        if not self._idle_fn():
            self._last_active = self._clock()
            self.stats["blocked"] += 1
            return False
        if self._last_active is not None and (self._clock() - self._last_active) < self._grace:
            self.stats["blocked"] += 1
            return False
        return True
