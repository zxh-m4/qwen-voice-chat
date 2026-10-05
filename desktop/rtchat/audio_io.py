# -*- coding: utf-8 -*-
"""麦克风采集与扬声器播放(基于 sounddevice/PortAudio,线程安全)。"""
from __future__ import annotations

import logging
import threading

from .frames import PlaybackQueue

log = logging.getLogger(__name__)


class Microphone:
    """把麦克风数据以 PCM bytes 推给 on_pcm 回调(PortAudio 线程)。"""

    def __init__(self, sample_rate: int, on_pcm, device=None, block_ms: int = 100):
        self._sample_rate = sample_rate
        self._on_pcm = on_pcm
        self._device = device
        self._block_ms = block_ms
        self._stream = None
        self._lock = threading.Lock()

    def _callback(self, indata, frames, time_info, status):
        if status:
            log.warning("mic status: %s", status)
        try:
            self._on_pcm(bytes(indata))
        except Exception:
            log.exception("mic on_pcm 回调异常")

    def start(self) -> None:
        import sounddevice as sd

        with self._lock:
            if self._stream is not None:
                return
            self._stream = sd.InputStream(
                samplerate=self._sample_rate,
                channels=1,
                dtype="int16",
                blocksize=self._sample_rate * self._block_ms // 1000,
                device=self._device,
                callback=self._callback,
            )
            self._stream.start()

    def stop(self) -> None:
        with self._lock:
            if self._stream is not None:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception:
                    log.exception("关闭麦克风失败")
                self._stream = None


class Player:
    """播放队列 + 声卡输出流。write_b64 收流式音频,clear 用于打断清空。"""

    def __init__(self, sample_rate: int, device=None):
        self._sample_rate = sample_rate
        self._device = device
        self._queue = PlaybackQueue()
        self._pending = bytearray()  # 跨回调保留的残余字节(不足一帧不许丢)
        self._pending_lock = threading.Lock()  # _pending 会被音频回调线程与主线程(clear)并发访问
        self.stats = {"callbacks": 0, "underrun_samples": 0}
        self._stream = None
        self._lock = threading.Lock()

    def _callback(self, outdata, frames, time_info, status):
        import numpy as np

        self.stats["callbacks"] += 1
        need = frames * 2  # int16 单声道
        with self._pending_lock:
            while len(self._pending) < need:
                chunk = self._queue.pop()
                if chunk is None:
                    break
                self._pending.extend(chunk)
            if len(self._pending) < need:
                # underrun:数据没跟上,补静音并计数(供诊断)
                self.stats["underrun_samples"] += (need - len(self._pending)) // 2
            data = bytes(self._pending[:need])
            usable = len(data) - len(data) % 2  # 奇数字节尾巴留在 pending,下次拼
            del self._pending[:usable]
        flat = outdata.reshape(-1)  # (frames, channels) -> 一维视图,写入即写回 outdata
        if len(data) < need:
            flat.fill(0)
        arr = np.frombuffer(data[:usable], dtype=np.int16)
        flat[: len(arr)] = arr

    def start(self) -> None:
        import sounddevice as sd

        with self._lock:
            if self._stream is not None:
                return
            self._stream = sd.OutputStream(
                samplerate=self._sample_rate,
                channels=1,
                dtype="int16",
                device=self._device,
                callback=self._callback,
            )
            self._stream.start()

    def stop(self) -> None:
        with self._lock:
            if self._stream is not None:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception:
                    log.exception("关闭播放流失败")
                self._stream = None
            self._queue.clear()
            with self._pending_lock:
                self._pending.clear()

    def write_b64(self, b64: str) -> None:
        self._queue.write_b64(b64)

    def write(self, raw: bytes) -> None:
        self._queue.write(raw)

    def clear(self) -> None:
        """打断:清空待播音频与残余。"""
        self._queue.clear()
        with self._pending_lock:
            self._pending.clear()

    @property
    def idle(self) -> bool:
        return self._queue.is_empty
