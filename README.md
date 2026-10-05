# Realtime Voice Chat · 实时外语对话

Real-time **full-duplex voice chat** powered by Alibaba Cloud Bailian's
**Qwen Omni Realtime** (`qwen3.8-omni-flash-realtime`).
Dual-platform open-source implementation: **desktop (Python/Tkinter)** + **Android (Kotlin)**.

> Talk naturally like on a phone call — interrupt anytime · **8 patient language teachers**
> (English / 日本語 / Русский / 中文 / Español / Français / 한국어 / Deutsch) with slowed speech
> and pronunciation correction · built-in live cost estimate · **no API key bundled — bring your own**.

---

## ⬇️ Download / 下载

Prebuilt packages are attached to the **[Releases](https://github.com/zxh-m4/qwen-voice-chat/releases)** page:

- **Android**: `RealtimeVoiceChat-v1.2.apk` — install on Android 6.0+ (allow "unknown sources")
- **Windows**: `RealtimeVoiceChat-v1.2-Windows.zip` — unzip, then double-click `实时外语对话.exe`

> The clients contain **no API keys**. On first launch you will be asked for *your own*
> Alibaba Cloud Bailian API Key and Workspace ID (see [Getting Your API Key](#getting-your-api-key-alibaba-cloud-bailian) below).
> 客户端不含任何密钥;首次启动需填入你自己的阿里云百炼 API Key 与业务空间 ID(获取方法见下文)。

## Features / 功能

- **Full-duplex**: streaming audio in and out; interrupt the teacher anytime by simply speaking.
- **8 language teachers** (switch via dropdown; switching starts a new conversation):
  each teacher is locked to its language — whatever language you speak, the teacher replies in theirs
  (exceptions only when you explicitly ask for an explanation/translation).
  | Teacher | Voice | Teacher | Voice |
  |---|---|---|---|
  | English | Tina | 中文 | Tina |
  | 日本語 | Ono Anna | Español | Sonrisa |
  | Русский | Katerina | Français | Emilien |
  | 한국어 | Sohee | Deutsch | Ingrid |
- **Live subtitles** for both sides.
- **Usage estimate** shown at the bottom of the UI while chatting.
- **Credential-free client**: the app contains no keys; on first launch it asks for *your own*
  API Key and Workspace ID, stored locally only.

## Repository Layout / 目录结构

```
qwen-voice-chat/
├── desktop/             Desktop app (Python 3.10+, Tkinter + sounddevice) — Windows / macOS / Linux
│   ├── rtchat/          Core modules (protocol / session state machine / audio / silence gate)
│   ├── tests/           99 unit tests
│   ├── run.py           Entry point
│   └── config.example.json  Config template (auto-copied to config.json on first run)
├── android/             Android app (Kotlin, Gradle 8.14 + JDK 17)
│   ├── app/src/main/java/com/zxh/rtchat/
│   └── app/libs/        ← Place the official AOQ SDK here (see its README)
└── docs/
    └── 千问实时语音接入实录.md   Deep-dive notes: pitfalls of both integration routes (Chinese)
```

## Quick Start / 快速开始

### Desktop (Windows / macOS / Linux)

```bash
cd desktop
pip install -r requirements.txt
python run.py            # first launch asks for your Bailian credentials
python -m pytest tests/  # 99 unit tests
```

> **macOS / Linux**: the stack (Tkinter + PortAudio + websocket-client) is cross-platform and the
> code contains no OS-specific APIs. Source-run on macOS/Linux is expected to work but has **not been
> tested by the author** — feedback and PRs welcome. On macOS, grant microphone permission to your
> terminal on first run.

### Android

```bash
cd android
# 1) Download the official AOQ SDK (AAR + Opus plugin) — see app/libs/README.md
# 2) Build (JDK 17 required)
./gradlew assembleOfficialDebug        # Windows: gradlew.bat assembleOfficialDebug
```

Variants: `official` = no bundled credentials (asks on first launch) ·
`trial` = reserved slot for bundled credentials (shipped empty).

**Checksums (SHA-256) / 校验和**

- `RealtimeVoiceChat-v1.2.apk` — `f7ee6d1e7f0f451653d1e828ed20d7e73b48ac79e9b89028ec1dfddc7a1398a9`
- `RealtimeVoiceChat-v1.2-Windows.zip` — `43c8b01acb79be80d4af368481d3b3cebd1a04fa3f4d92797c0ca5f8d4872a82`

## Getting Your API Key (Alibaba Cloud Bailian) / 如何获取 API Key

> ⚠️ The Bailian console is **in Chinese**. Follow these steps:

1. Open **https://bailian.console.aliyun.com** and sign in with an Alibaba Cloud account
   (a phone number + real-name verification is required for new accounts);
2. Click the avatar menu (top-right) → **「API-KEY 管理」** (API-KEY management) → **创建** (Create)
   → copy the key starting with `sk-`;
3. Still in the console, open **「业务空间列表」** (Workspace list) → copy your Workspace ID
   (looks like `llm-xxxxxxxx`). **Every account has its own — do not copy someone else's**;
4. Paste both into the app's settings dialog on first launch. They are stored locally only.

**Billing** (pay-as-you-go, Beijing region): audio input ¥6 / million tokens, audio output ¥12 /
million tokens. Reference costs (derived from 7 input tokens/s and 12.5 output tokens/s):

| Scenario | Cost |
|---|---|
| Normal back-and-forth conversation | ≈ **¥0.4 / hour** |
| Connected but silent (Android: now suppressed by the silence gate) | ≈ ¥0.15 / hour |
| Both sides talking continuously (theoretical ceiling) | ≈ ¥0.69 / hour |

Text tokens (¥1.5 / ¥4.5 per million) add a little on top — note that conversation history is
re-sent as input on every turn, so long sessions drift upward. Closing the window stops billing.
**Always trust the console bill over the in-app estimate**; the estimate is computed from
measured audio duration and published rates, not from actual server-side token counts.

## Privacy / 隐私说明

**What leaves your device / 会离开你设备的东西**

- **Audio / 语音**：microphone audio is streamed to Alibaba Cloud Bailian in real time for
  processing. It is **never written to local storage** by this app.
  语音实时传输至阿里云百炼进行处理，**本应用不会将其写入任何本地文件**。
- **Text / 文字**：transcripts are rendered on screen only. **No conversation content is
  written to logs or files.**
  转写文字仅显示在屏幕上，**任何对话内容都不会写入日志或文件**。
- **Credentials / 凭据**：your API Key and Workspace ID stay on your device. On Android 6.0+
  they are encrypted with an AES key held in the **system KeyStore** (the app itself cannot read
  the key back); app backup is disabled. Desktop keeps them in `config.local.json`, which is
  excluded by `.gitignore`. They are sent only to Alibaba Cloud's auth endpoint.
  凭据仅存于本机。Android 6.0+ 使用**系统 KeyStore 中的 AES 密钥**加密（应用自身也读不回密钥），
  并已关闭应用备份；桌面端存于 `config.local.json`（已被 `.gitignore` 排除）。仅在向阿里云鉴权时发送。

**What is written to storage / 会落盘的东西**

- A technical log (`logs/…txt`) with timestamps, frame counts, volume levels and error codes —
  **no conversation content**. On Android 11+ it sits in app-private storage and other apps
  cannot read it; on older Android versions, apps holding storage permission could.
  技术日志（时间戳、帧数、音量、错误码），**不含对话内容**。Android 11+ 位于应用私有目录，
  其他 App 无法读取；更早的系统上，持有存储权限的 App 可以读取。

**Permissions / 权限**

| Permission | Why |
|---|---|
| `INTERNET`, `ACCESS_NETWORK_STATE` | connect to the service |
| `RECORD_AUDIO` | microphone — requested at runtime, only when you tap Connect |
| `MODIFY_AUDIO_SETTINGS` | call-volume routing and speaker/headset switching |

No location, no contacts, no camera, no screen-recording permission. The screen-sharing
components that Alibaba's SDK ships with are explicitly stripped from the manifest
(this app never uses them).
不含位置、通讯录、相机、录屏权限。阿里云 SDK 自带的屏幕共享组件已被显式移除（本应用不使用）。

**Behaviour worth knowing / 需要知道的行为**

- The app **disconnects automatically when it goes to the background**, so you are never
  charged for a session you thought you had closed.
  应用退到后台会自动断开，不会出现"以为关了其实还在计费"。
- If a Bluetooth or wired headset is connected, audio goes to the headset **instead of the
  speaker** — nearby people cannot overhear your conversation.
  接入耳机时声音走耳机而非外放，旁人听不到对话内容。

---

## Protocol Notes / 接入说明

| | Desktop | Android |
|---|---|---|
| Integration | Qwen **Realtime WebSocket** (direct) | Alibaba **AOQ Client SDK** (WebRTC) |
| Endpoint | `wss://<workspace>.cn-beijing.maas.aliyuncs.com/api-ws/v1/realtime` | HTTP token exchange, then SDK connect |
| Echo handling | local silence gate (+ optional echo guard) | relies on SDK/system AEC |
| Deep-dive notes | `docs/千问实时语音接入实录.md` (Chinese) | same |

**The session-config JSON differs between the two routes — read the notes before integrating.**

## Maintenance / 维护状态

This is a personal hobby project and is **not expected to receive frequent updates**.
Released under the [MIT](LICENSE) license — **you are free to modify, rebuild and redistribute it**
(one small request: keep the license notice). Contributions to continue improving it are welcome.

## Acknowledgements / 致谢

- Voice conversations are powered by **Alibaba Cloud Bailian Qwen Omni Realtime** and its official SDKs
  (© Alibaba Cloud; SDK binaries are intentionally **not** included in this repo — download them from
  the official pages).
- The Android integration follows the interface usage shown in Alibaba's official iOS sample.
- Thanks to all open-source dependencies: websocket-client, sounddevice, androidx, etc.

## Author / 作者

笑晗 (@zxh-m4)

## License / 许可证

[MIT](LICENSE) — for the source code. Model services and third-party SDKs remain subject to their
respective vendors' terms.
