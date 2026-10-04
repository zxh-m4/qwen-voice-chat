# -*- coding: utf-8 -*-
"""声纹门(黑名单制):只挡 AI 的合成音,任何人声(机主、旁人)都放行。

设计(2026-10-02 用户定稿,替代此前的白名单方案):
- 黑名单基准 = AI 正在播放的音频的嵌入(上层运行时提取后 add_reference 注入);
  基准为空(AI 还没说过话)时一切放行——没有播放就没有回环,逻辑自洽;
- 段嵌入与基准余弦相似度 >= 阈值 → 判为 AI 回声,整段丢弃;否则放行(补发缓冲不吞字);
- 静音超过 silence_timeout_ms 回 idle,下一段重新判定;
- 任何异常/未启用一律降级放行(fail-open),绝不让窗口变哑。
串联位置:静音门(SilenceGate)之后——静音门管"停发省钱",声纹门管"是不是 AI 在说"。
"""
from __future__ import annotations

import logging
from typing import Callable, Optional

import numpy as np

log = logging.getLogger(__name__)


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return float(np.dot(a, b) / (na * nb + 1e-9))


def make_embedder(model_path: str, sample_rate: int = 16000):
    """真声纹嵌入器(sherpa-onnx CAM++);模型加载失败返回 None(门降级直通)。"""
    try:
        import sherpa_onnx

        cfg = sherpa_onnx.SpeakerEmbeddingExtractorConfig(
            model=model_path, num_threads=2
        )
        extractor = sherpa_onnx.SpeakerEmbeddingExtractor(cfg)
    except Exception:
        log.exception("声纹模型加载失败(%s),声纹门降级为直通", model_path)
        return None

    def embed(pcm: bytes) -> np.ndarray:
        samples = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
        st = extractor.create_stream()
        st.accept_waveform(sample_rate, samples)
        st.input_finished()
        return np.asarray(extractor.compute(st), dtype=np.float32)

    return embed


class VoicePrintGate:
    """状态机:idle -> collecting(缓冲) -> pass / blocked ->(静音超时)-> idle。"""

    def __init__(
        self,
        embedder: Optional[Callable[[bytes], np.ndarray]],
        threshold: float = 0.45,
        buffer_ms: int = 500,
        frame_ms: int = 100,
        enabled: bool = True,
        silence_timeout_ms: int = 800,
        threshold_rms: int = 600,
        max_references: int = 5,
    ):
        self._embedder = embedder
        self._threshold = threshold
        self._buffer_frames = max(1, buffer_ms // frame_ms)
        self._frame_ms = frame_ms
        self.enabled = enabled
        self._silence_timeout_ms = silence_timeout_ms
        self._threshold_rms = threshold_rms
        self._max_references = max_references
        self._references: list[np.ndarray] = []
        self.state = "idle"
        self._buffer: list[bytes] = []
        self._silent_ms = 0
        self.stats = {"segments": 0, "blocked": 0, "frames_dropped": 0}

    # ---------- 黑名单基准 ----------

    def add_reference(self, vector: np.ndarray) -> None:
        """注入一条 AI 音色基准(上层从播放音频提取)。超出上限滚动淘汰。"""
        self._references.append(np.asarray(vector, dtype=np.float32))
        if len(self._references) > self._max_references:
            self._references.pop(0)
        log.info("voiceprint: AI 音色基准已更新(%d 条)", len(self._references))

    @property
    def references(self) -> list[np.ndarray]:
        return list(self._references)

    @property
    def has_reference(self) -> bool:
        return bool(self._references)

    def embed(self, pcm: bytes) -> Optional[np.ndarray]:
        """对外提取嵌入(供上层从播放音频生成基准);无模型时返回 None。"""
        if self._embedder is None:
            return None
        return self._embed(pcm)

    # ---------- 内部 ----------

    @staticmethod
    def rms(data: bytes) -> int:
        if not data:
            return 0
        a = np.frombuffer(data, dtype=np.int16).astype(np.float64)
        if a.size == 0:
            return 0
        return int(np.sqrt(np.mean(a * a)))

    def _embed(self, pcm: bytes) -> np.ndarray:
        assert self._embedder is not None
        return self._embedder(pcm)

    def _decide(self, pcm: bytes) -> bool:
        """返回 True=人声(放行);False=AI 回声(丢弃);异常放行(fail-open)。"""
        self.stats["segments"] += 1
        try:
            emb = self._embed(pcm)
            sim = max(cosine(emb, r) for r in self._references)
            is_ai = sim >= self._threshold
            log.info("voiceprint: vp=%.2f -> %s", sim, "AI回声,丢弃" if is_ai else "人声,放行")
            return not is_ai
        except Exception:
            log.exception("voiceprint 判定异常,降级放行")
            return True

    # ---------- 主入口 ----------

    def feed(self, frame: bytes) -> list[bytes]:
        """喂一帧,返回应上传的帧列表(放行时含补发缓冲)。"""
        if not self.enabled or not self._references:
            return [frame]

        loud = self.rms(frame) >= self._threshold_rms

        if self.state == "idle":
            if loud:
                self.state = "collecting"
                self._buffer = [frame]
                return [] if self._buffer_frames > 1 else self._flush()
            return [frame]  # idle 静音帧照传(保住服务端 VAD 时间轴)

        if self.state == "collecting":
            self._buffer.append(frame)
            if len(self._buffer) >= self._buffer_frames:
                return self._flush()
            return []

        # pass / blocked 段内
        if loud:
            self._silent_ms = 0
        else:
            self._silent_ms += self._frame_ms
            if self._silent_ms >= self._silence_timeout_ms:
                self.state = "idle"  # 段结束,下一声重新判定
        if self.state == "idle":
            return [frame]  # 超时转 idle 的这一帧按 idle 规则(照传)
        return [frame] if self.state == "pass" else self._drop(frame)

    def _flush(self) -> list[bytes]:
        """缓冲攒满,判定并放行/丢弃。"""
        buf = self._buffer
        self._buffer = []
        if self._decide(b"".join(buf)):
            self.state = "pass"
            return buf
        self.state = "blocked"
        self.stats["blocked"] += 1
        self.stats["frames_dropped"] += len(buf)
        return []

    def _drop(self, frame: bytes) -> list[bytes]:
        self.stats["frames_dropped"] += 1
        return []
