# -*- coding: utf-8 -*-
"""全链路对话测试:把本地 WAV 当麦克风数据实时灌入,验证
上行(音频→服务端 VAD→转写)与下行(模型语音+文字)全通。不依赖声卡。"""
import json
import sys
import threading
import time
import wave

from rtchat.config import ConfigError, load_config
from rtchat.protocol import build_append, build_session_update, parse_event

WAV = "test_voice.wav"
FEED_MS = 100       # 按 100ms 片实时速率发送
TOTAL_TIMEOUT = 60


def load_pcm16k(path: str) -> bytes:
    """读取任意 wav,转 16kHz/16bit/单声道 PCM(numpy 实现,不依赖已移除的 audioop)。"""
    import numpy as np

    with wave.open(path, "rb") as w:
        raw = w.readframes(w.getnframes())
        sr, sw, ch = w.getframerate(), w.getsampwidth(), w.getnchannels()
    if sw == 1:
        a = (np.frombuffer(raw, dtype=np.uint8).astype(np.int16) - 128) * 256
    elif sw == 4:
        a = (np.frombuffer(raw, dtype=np.int32) >> 16).astype(np.int16)
    else:
        a = np.frombuffer(raw, dtype=np.int16)
    if ch > 1:
        a = a.reshape(-1, ch).mean(axis=1).astype(np.int16)
    if sr != 16000:
        n = int(a.size * 16000 / sr)
        idx = np.linspace(0, a.size - 1, n)
        a = np.interp(idx, np.arange(a.size), a.astype(np.float32)).astype(np.int16)
    return a.tobytes()


def main() -> int:
    try:
        cfg = load_config("config.json")
    except ConfigError as e:
        print(f"配置错误: {e}")
        return 2

    pcm = load_pcm16k(WAV)
    frame = cfg.frame_bytes  # 100ms
    n_frames = (len(pcm) + frame - 1) // frame
    print(f"测试音频: {len(pcm)} 字节 PCM16/16k, 约 {len(pcm)/32000:.1f}s, {n_frames} 帧")

    events = []
    lock = threading.Lock()
    ready = threading.Event()
    done = threading.Event()
    stats = {"last_feed_t": None, "first_audio_t": None, "sent": 0, "reply": bytearray()}

    def record(etype, extra=None):
        with lock:
            events.append((time.time(), etype, extra))

    def feeder(ws):
        ready.wait(15)
        if not ready.is_set():
            return
        t0 = time.time()
        for i in range(n_frames):
            chunk = pcm[i * frame:(i + 1) * frame]
            ws.send(json.dumps(build_append(chunk)))
            stats["sent"] += 1
            # 实时节奏:相对绝对时间 sleep,避免累积漂移
            target = t0 + (i + 1) * FEED_MS / 1000
            delay = target - time.time()
            if delay > 0:
                time.sleep(delay)
        stats["last_feed_t"] = time.time()
        record("FEED_DONE")
        # 喂完后等服务端 VAD 切轮、出结果;不再主动 commit(server VAD 模式)

    def on_message(ws, raw):
        try:
            msg = parse_event(raw)
        except Exception as e:
            record("PARSE_ERR", str(e))
            return
        t = msg.get("type")
        extra = None
        if t == "session.created":
            ws.send(json.dumps(build_session_update(cfg)))
        elif t == "session.updated":
            ready.set()
        elif t == "conversation.item.input_audio_transcription.completed":
            extra = msg.get("transcript")
        elif t == "response.audio_transcript.delta":
            extra = msg.get("delta")
        elif t == "response.audio.delta":
            if stats["first_audio_t"] is None:
                stats["first_audio_t"] = time.time()
            if msg.get("delta"):
                import base64

                stats["reply"].extend(base64.b64decode(msg["delta"]))
        elif t == "error":
            extra = json.dumps(msg.get("error"), ensure_ascii=False)
            record(t, extra)
            ws.close()
            return
        elif t == "response.done":
            record(t, extra)
            done.set()
            _save_reply(bytes(stats["reply"]), cfg.output_sample_rate)
            ws.close()
            return
        record(t, extra)

    import websocket

    ws = websocket.WebSocketApp(
        cfg.ws_url,
        header=[f"Authorization: Bearer {cfg.api_key}"],
        on_message=on_message,
        on_open=lambda w: threading.Thread(target=feeder, args=(w,), daemon=True).start(),
        on_error=lambda w, e: record("CONN_ERR", str(e)),
    )
    threading.Timer(TOTAL_TIMEOUT, ws.close).start()
    ws.run_forever(ping_interval=10, ping_timeout=5)

    # ---- 报告 ----
    print("\n=== 事件时间线 ===")
    t0 = events[0][0] if events else time.time()
    for ts, etype, extra in events:
        mark = f" | {extra}" if extra else ""
        print(f"+{ts-t0:6.2f}s  {etype}{mark}")

    types = {e for _, e, _ in events}
    transcript = next((x for _, e, x in events if e == "conversation.item.input_audio_transcription.completed"), None)
    ai_text = "".join(x or "" for _, e, x in events if e == "response.audio_transcript.delta")

    print("\n=== 结论 ===")
    ok = True
    def check(name, cond, detail=""):
        global ok
        print(f"  [{'PASS' if cond else 'FAIL'}] {name} {detail}")
        if not cond:
            ok = False

    check("VAD 检测到说话", "input_audio_buffer.speech_started" in types)
    check("用户语音转写", bool(transcript), f"-> {transcript!r}")
    check("模型生成响应", "response.created" in types)
    check("模型语音下行", stats["first_audio_t"] is not None)
    check("模型文字回复", bool(ai_text), f"-> {ai_text[:60]!r}")
    if stats["first_audio_t"] and stats["last_feed_t"]:
        print(f"  (参考:喂完音频到首个音频包 {stats['first_audio_t']-stats['last_feed_t']:.2f}s)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
