# -*- coding: utf-8 -*-
"""静音门:静音超过滞回时长停止上传音频,把挂机成本降到零。

滞回设计:能量掉到阈值以下后,继续发送 gate_ms 的静音(保证服务端
VAD 的断句计时拿到连续时间轴),连续静音超时才停发;一旦检测到
声音立即恢复发送(延迟最多一个麦克风块,默认 100ms)。
"""
from __future__ import annotations

import numpy as np


class SilenceGate:
    def __init__(self, threshold_rms: int, gate_ms: int, frame_ms: int, enabled: bool = True):
        self._threshold = threshold_rms
        self._gate_ms = gate_ms
        self._frame_ms = frame_ms
        self.enabled = enabled
        self._active = False  # 初始静音不发,来声音才开
        self._silent_ms = 0
        self.stats = {"frames_in": 0, "frames_sent": 0}

    @staticmethod
    def rms(data: bytes) -> int:
        """16bit 单声道 PCM 的 RMS 幅度(audioop 已于 Python 3.13 移除,用 numpy 实现)。"""
        if not data:
            return 0
        a = np.frombuffer(data, dtype=np.int16).astype(np.float64)
        if a.size == 0:
            return 0
        return int(np.sqrt(np.mean(a * a)))

    def feed(self, frame: bytes) -> bool:
        """喂一帧麦克风数据,返回这帧是否应该发送。"""
        self.stats["frames_in"] += 1
        if not self.enabled:
            self.stats["frames_sent"] += 1
            return True

        if self.rms(frame) >= self._threshold:
            self._active = True
            self._silent_ms = 0
            self.stats["frames_sent"] += 1
            return True

        # 低于阈值:非激活态直接丢;激活态进入滞回计时
        if not self._active:
            return False
        if self._silent_ms >= self._gate_ms:
            self._active = False
            return False
        self._silent_ms += self._frame_ms
        self.stats["frames_sent"] += 1
        return True

    @property
    def sent_ratio(self) -> float:
        n = self.stats["frames_in"]
        return self.stats["frames_sent"] / n if n else 0.0
