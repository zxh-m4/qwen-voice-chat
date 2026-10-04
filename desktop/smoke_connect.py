# -*- coding: utf-8 -*-
"""连接烟雾测试:连上 Realtime 端点,完成 session 握手即算通过(不发音频,几乎不产生费用)。"""
import sys

from rtchat.config import ConfigError, load_config
from rtchat.protocol import build_session_update, parse_event

TIMEOUT_S = 20


def main() -> int:
    try:
        cfg = load_config("config.json")
    except ConfigError as e:
        print(f"配置错误: {e}")
        return 2

    print(f"连接: {cfg.ws_url}")
    import websocket

    outcome = {"ok": False, "error": None}

    def on_message(ws, raw):
        try:
            msg = parse_event(raw)
        except Exception as e:
            print(f"解析失败: {e}")
            return
        t = msg.get("type")
        print(f"<< {t}")
        if t == "session.created":
            ws.send(json_dumps(build_session_update(cfg)))
        elif t == "session.updated":
            print("握手成功: session.updated 收到")
            outcome["ok"] = True
            ws.close()
        elif t == "error":
            outcome["error"] = msg.get("error")
            print(f"服务端错误: {msg.get('error')}")
            ws.close()

    def on_error(ws, err):
        outcome["error"] = outcome["error"] or str(err)
        print(f"错误: {err}")

    def json_dumps(obj):
        import json

        return json.dumps(obj, ensure_ascii=False)

    ws = websocket.WebSocketApp(
        cfg.ws_url,
        header=[f"Authorization: Bearer {cfg.api_key}"],
        on_message=on_message,
        on_error=on_error,
    )
    ws.run_forever(ping_interval=10, ping_timeout=5)
    if outcome["ok"]:
        print("SMOKE TEST PASSED")
        return 0
    print(f"SMOKE TEST FAILED: {outcome['error']}")
    return 1


if __name__ == "__main__":
    import threading

    # Windows 无 SIGALRM,用定时器兜底超时
    timer = threading.Timer(TIMEOUT_S, lambda: print("TIMEOUT") or sys.exit(3))
    timer.daemon = True
    timer.start()
    code = main()
    timer.cancel()
    sys.exit(code)
