# -*- coding: utf-8 -*-
"""PCM 帧切分与播放队列(线程安全)。"""
from __future__ import annotations

import base64
import threading
from collections import deque


class FrameSplitter:
    """把不定长 PCM 字节流切成等长帧,余数暂存到下次喂入。"""

    def __init__(self, frame_bytes: int):
        if frame_bytes <= 0:
            raise ValueError("frame_bytes 必须为正")
        self._frame_bytes = frame_bytes
        self._buf = bytearray()

    @property
    def pending(self) -> int:
        return len(self._buf)

    def feed(self, data: bytes) -> list[bytes]:
        if not data:
            return []
        self._buf.extend(data)
        frames = []
        while len(self._buf) >= self._frame_bytes:
            frames.append(bytes(self._buf[: self._frame_bytes]))
            del self._buf[: self._frame_bytes]
        return frames

    def reset(self) -> None:
        self._buf.clear()


class PlaybackQueue:
    """播放缓冲:write 收 base64 音频,播放线程 drain 取原始 PCM。

    容量上限:网络卡顿时远端可能在一瞬间灌入大量音频,而播放速度跟不上,
    队列会一直涨到把内存吃满。这里设定帧数上限,超出丢弃最旧的音频
    (宁可少听几句,也不能让程序卡死)。按 20ms/帧估算,120 帧≈2.4 秒缓冲,
    足够吸收正常抖动。
    """

    def __init__(self, max_frames: int = 120) -> None:
        self._q: deque[bytes] = deque()
        self._lock = threading.Lock()
        self._max = max(1, max_frames)
        self.dropped = 0

    @property
    def is_empty(self) -> bool:
        with self._lock:
            return not self._q

    def write_b64(self, b64: str) -> None:
        try:
            raw = base64.b64decode(b64)
        except Exception:
            return  # 跳过损坏的音频片,不让播放线程崩
        if raw:
            self.write(raw)

    def write(self, raw: bytes) -> None:
        with self._lock:
            self._q.append(raw)
            while len(self._q) > self._max:
                self._q.popleft()
                self.dropped += 1

    def drain(self) -> list[bytes]:
        with self._lock:
            items = list(self._q)
            self._q.clear()
        return items

    def pop(self) -> bytes | None:
        with self._lock:
            return self._q.popleft() if self._q else None

    def clear(self) -> None:
        with self._lock:
            self._q.clear()
