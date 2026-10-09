# Realtime Voice Chat · 实时外语对话

Real-time **full-duplex voice chat** powered by Alibaba Cloud Bailian's
**Qwen Omni Realtime** (`qwen3.8-omni-flash-realtime`).
Dual-platform open-source implementation: **desktop (Python/Tkinter)** + **Android (Kotlin)**.

> Talk naturally like on a phone call — interrupt anytime · **8 patient language teachers**
> (English / 日本語 / Русский / 中文 / Español / Français / 한국어 / Deutsch) with slowed speech
> and pronunciation correction · built-in live cost estimate · **no API key bundled — bring your own**.

---

## What this is / 这是什么

A **client-side tool** for real-time voice practice, powered by Alibaba Cloud Bailian's
Qwen Omni Realtime model.

**It is not an AI service.** This project does not distribute AI capability, does not proxy
requests, and holds no API key. You register your own Alibaba Cloud account, create your own
API key and enter it into the app — the AI service is provided by Alibaba Cloud
**directly to you**.

本应用是**客户端工具**，用于通过阿里云百炼的 Qwen Omni Realtime 模型练习实时语音对话。
**它不是 AI 服务**：本项目不分发 AI 能力、不代理请求、不持有任何 API Key；
使用者自行注册阿里云账号、申请自己的 API Key 并填入应用——
AI 服务由**阿里云直接向该使用者本人**提供。

## 📦 No prebuilt binaries / 不提供预编译包

This is a personal, non-commercial learning project. **No prebuilt APK/EXE packages are
distributed here** — please build from source (see [Quick Start](#quick-start--快速开始) below).
Releases are kept as version notes only. Full version history since v1.0: see [CHANGELOG.md](CHANGELOG.md).

本项目为个人业余学习作品，**不对外分发预编译安装包**，请按下方「快速开始」从源码自行构建；
Release 页仅保留版本说明;完整版本历史(自 v1.0 起)见 [CHANGELOG.md](CHANGELOG.md)。

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
- **Live subtitles** for both sides (captions are produced by a separate subtitle model — see the in-app help for why their typos do not affect the conversation).
- **Mic sensitivity** (7 levels, 0 to −40 dB): lowers the uploaded audio volume so surrounding
  voices are less likely to be treated as you speaking — then speak closer to the mic / louder.
- **Bilingual UI** (Chinese / English, default Chinese): switch with the top-right `EN / 中文`
  button; the choice is remembered across launches.
- **Usage estimates**: this-session and process-lifetime totals shown at the bottom while chatting.
- **Credential-free client**: the app contains no keys; on first launch it asks for *your own*
  API Key and Workspace ID, stored locally only (Windows Credential Manager with a local-file fallback).

## Repository Layout / 目录结构

```
qwen-voice-chat/
├── desktop/             Desktop app (Python 3.10+, Tkinter + sounddevice) — Windows / macOS / Linux
│   ├── rtchat/          Core modules (protocol / session state machine / audio / silence gate)
│   ├── tests/           152 unit tests
│   ├── tools/           Dev-only scripts: full-chain dialogue test, connect smoke, UI smoke, playback diagnostics
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
python -m pytest tests/  # 152 unit tests
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
  the key back); app backup is disabled. On Windows the desktop app stores them in the
  **Windows Credential Manager** (system-encrypted; view or delete under Control Panel →
  Credential Manager); only if that fails, or on non-Windows systems, it falls back to
  `config.local.json`, which is excluded by `.gitignore`. They are sent only to Alibaba Cloud's
  auth endpoint.
  凭据仅存于本机。Android 6.0+ 使用**系统 KeyStore 中的 AES 密钥**加密（应用自身也读不回密钥），
  并已关闭应用备份；Windows 桌面端存于 **Windows 凭据管理器**（系统加密，可在「控制面板 → 凭据管理器」
  查看或删除），仅在写入失败或非 Windows 系统上回退到 `config.local.json`（已被 `.gitignore` 排除）。
  仅在向阿里云鉴权时发送。

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

## What this project does NOT do / 本项目不做什么

The statements below are **verifiable from the source code** — not promises:

| Does NOT / 不做 | How to verify / 验证方式 |
|---|---|
| **Provide API keys** / 不提供 API Key | Search the repo for `sk-` — no valid key exists anywhere |
| **Relay or proxy requests** / 不做请求中转 | All of the app's **service traffic** goes **only to Alibaba Cloud** — **Alibaba Cloud's credential endpoint** on `<workspace>.cn-beijing.maas.aliyuncs.com`, plus the relay nodes **assigned by Alibaba Cloud** in that response. **No developer-operated server exists anywhere in the path.** / 客户端的**所有业务通信**只与**阿里云**进行：**阿里云的凭证接口** + **由阿里云分配的中继节点**；**全程不经开发者的任何服务器** |
| **Collect user data** / 不收集用户数据 | No analytics, no tracking SDK, no log upload |
| **Store or upload conversations** / 不保存、不上传对话内容 | Transcripts are **rendered on screen only** — **never written to storage, never uploaded**. Only microphone audio is streamed to Alibaba Cloud for recognition. / 转写**仅渲染在屏幕上**——**从不写入存储、也不上传**；只有麦克风音频会流式传给阿里云做识别 |
| **Charge any fee** / 不收取费用 | No payment channel, no top-up, no key resale |
| **Decide the model for you** / 不替你决定模型 | Model name and system prompts are editable example defaults |

This is a **personal, non-commercial hobby project** — the author derives no revenue from it.
本项目为**个人作品、非经营性**，作者不从中获得任何收益。

---

## Protocol Notes / 接入说明

| | Desktop | Android |
|---|---|---|
| Integration | Qwen **Realtime WebSocket** (direct) | Alibaba **AOQ Client SDK** (WebRTC) |
| Endpoint | `wss://<workspace>.cn-beijing.maas.aliyuncs.com/api-ws/v1/realtime` | Alibaba Cloud's credential endpoint (also returns the assigned relay nodes), then SDK connect |
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
