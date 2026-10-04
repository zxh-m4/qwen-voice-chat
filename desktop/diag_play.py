# -*- coding: utf-8 -*-
"""播放质量诊断:真实对话,delta 实时写入声卡播放,统计断流(underrun)。"""
import base64
import json
import sys
import threading
import time
import wave

from rtchat.audio_io import Player
from rtchat.config import ConfigError, load_config
from rtchat.protocol import build_append, build_session_update, parse_event
from test_dialogue import load_pcm16k


def main() -> int:
    try:
        cfg = load_config("config.json")
    except ConfigError as e:
        print(f"配置错误: {e}")
        return 2

    pcm = load_pcm16k("test_voice.wav")
    frame = cfg.frame_bytes
    n_frames = (len(pcm) + frame - 1) // frame

    player = Player(cfg.output_sample_rate)
    ready = threading.Event()
    stats = {"last_feed_t": None, "first_delta_t": None, "last_delta_t": None,
             "underrun_at_first": None, "underrun_at_last": None, "reply": bytearray()}

    def snap_first():
        if stats["underrun_at_first"] is None:
            stats["underrun_at_first"] = player.stats["underrun_samples"]
            stats["first_delta_t"] = time.time()

    def feeder(ws):
        ready.wait(15)
        if not ready.is_set():
            return
        t0 = time.time()
        for i in range(n_frames):
            ws.send(json.dumps(build_append(pcm[i * frame:(i + 1) * frame])))
            target = t0 + (i + 1) * 0.1
            if (d := target - time.time()) > 0:
                time.sleep(d)
        stats["last_feed_t"] = time.time()
        # 等响应播完再关
        time.sleep(6)
        ws.close()

    def on_message(ws, raw):
        try:
            msg = parse_event(raw)
        except Exception:
            return
        t = msg.get("type")
        if t == "session.created":
            ws.send(json.dumps(build_session_update(cfg)))
        elif t == "session.updated":
            ready.set()
        elif t == "response.audio.delta":
            snap_first()
            stats["last_delta_t"] = time.time()
            stats["underrun_at_last"] = player.stats["underrun_samples"]
            if msg.get("delta"):
                player.write_b64(msg["delta"])
                stats["reply"].extend(base64.b64decode(msg["delta"]))
        elif t == "error":
            print("服务端错误:", msg.get("error"))
            ws.close()

    import websocket

    ws = websocket.WebSocketApp(
        cfg.ws_url,
        header=[f"Authorization: Bearer {cfg.api_key}"],
        on_message=on_message,
        on_open=lambda w: threading.Thread(target=feeder, args=(w,), daemon=True).start(),
    )
    threading.Timer(40, ws.close).start()

    print("打开播放流(24kHz)…")
    player.start()
    try:
        ws.run_forever(ping_interval=10, ping_timeout=5)
    finally:
        # 播完剩余
        deadline = time.time() + 5
        while time.time() < deadline and not player.idle:
            time.sleep(0.2)
        time.sleep(1.5)  # 声卡缓冲排空
        player.stop()

    # ---- 报告 ----
    cb = player.stats["callbacks"]
    und = player.stats["underrun_samples"]
    print("\n=== 播放诊断 ===")
    print(f"回调次数: {cb}, 累计 underrun: {und} 采样 ({und / max(cb,1) / 480:.1%} of 回调均值)")
    if stats["underrun_at_first"] is not None and stats["underrun_at_last"] is not None:
        resp_und = stats["underrun_at_last"] - stats["underrun_at_first"]
        span = stats["last_delta_t"] - stats["first_delta_t"]
        resp_samples = span * cfg.output_sample_rate
        pct = resp_und / max(resp_samples, 1)
        print(f"响应音频流期间 underrun: {resp_und} 采样 / {resp_samples:.0f} = {pct:.2%}")
        verdict = "PASS(响应期间几乎无断流)" if pct < 0.03 else "FAIL(断流明显)"
        print(f"判定: {verdict}")
        print(f"响应流时长 {span:.2f}s,音频 {len(stats['reply'])/2/cfg.output_sample_rate:.2f}s")
    if stats["reply"]:
        with wave.open("reply_played.wav", "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(cfg.output_sample_rate)
            w.writeframes(bytes(stats["reply"]))
        print("本次响应已存 reply_played.wav")
    return 0


if __name__ == "__main__":
    sys.exit(main())
