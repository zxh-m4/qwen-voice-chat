# Version History / 版本历史

Release notes for every version since the first working build (v1.0).

> **Note on v1.0 / v1.1** — these versions **predate this repository** (created on
> 2026-10-04 for the v1.2 open-source release). Their source code is not included here,
> and their build artifacts remain in the author's private archive. **No binaries are
> distributed.** They are recorded in this changelog so that the project history is complete.
>
> 注:v1.0 / v1.1 早于本仓库(仓库随 v1.2 于 2026-10-04 开源时建立),其源码未入库、
> 构建产物保存在作者本地归档,不对外分发;此处补录以保持版本历史完整。

## v1.7 — 2026-10-18
- **APK slimming / 安卓瘦身** — R8 (minify + shrink resources) plus dropping the Material Components dependency cuts the APK from 9.93 MB to 5.92 MB (−40%). The three `.so` files are untouched and now make up roughly 80% of the package — that is the floor for further Android slimming. The theme moves to AppCompat equivalents.
  （开启 R8 混淆与资源压缩、去掉 Material 依赖：APK 9.93 → 5.92 MB。三个 `.so` 未动，现占包体约八成，是安卓端继续瘦身的天花板；主题改用 AppCompat 等价写法。）
- **Custom language tutor / 自定义语言** — a ninth entry in the role dropdown. The model already knows language names, so no whitelist is imposed: whatever the user types becomes the locked language under the same rules as the eight built-in teachers; the voice is fixed to Tina.
  （角色下拉新增第九项；模型本身认识语种名，故不设白名单——填什么语言名就锁什么语言，规则与八位内置老师一致，音色固定 Tina。）
- Android: `versionCode 8` / `versionName 1.7`; no binary is distributed (build from source)

## v1.6 — 2026-10-13
- **App filing compliance / App 备案合规** — the ICP filing number is shown under **Settings → About**: long-press to copy, tap to open the MIIT lookup site (`beian.miit.gov.cn`). That page also carries the app name, version, open-source notices, privacy policy and copyright — and the help page no longer repeats the privacy, filing or open-source sections. The disclaimer wording stays **verbatim** identical to the screenshots submitted with the public-security registration (公安备案).
  （备案号在「设置 → 关于」：长按复制、点击跳转工信部备案查询系统；同页列应用名、版本、开源软件声明、隐私政策与版权；帮助页不再重复隐私/备案/开源声明。）
- **AI-generated content notice** — new in v1.6; **v1.5 shipped without any AI label** (`ai_notice` does not exist in the v1.5 tag). Both platforms now show a persistent, non-dismissible line, every assistant caption carries an `AI:` prefix, and the help page has a dedicated section — in Chinese and English.
- Desktop: window & taskbar icon; layout refresh — 560×560 window, two-row top bar, uniform button widths
- Desktop: persistent AI-notice line above the usage line (follows UI language); help page gains an AI-notice section and a privacy line stating that transcripts are shown on screen only and nothing is stored
- Desktop: **numpy removed from the runtime** — mic capture and playback now use PortAudio raw streams (`RawInputStream` / `RawOutputStream`, cffi buffers) and gain/RMS are done with the stdlib `array`/`math`; the packaged size drops from 26.2 MB to 11.1 MB (extra `--exclude-module numpy`, plus five unused non-Windows PortAudio binaries dropped from the bundle)
- Desktop: packaging fixed — `实时外语对话.spec` with `icon='app.ico'` (the exe used to ship with the Windows default notepad icon) and `config.example.json` bundled so first launch no longer warns about a missing config; usage line gains a `静音省 Ns` / `muted Ns` counter (audio time blocked by the silence gate — **not** a cost reduction, billing still follows connection time)
- Desktop tests: 143 → **175**, all green in an environment **without** numpy
- Android: `versionCode 7` / `versionName 1.6`; no binary is distributed (build from source)

## v1.5 — 2026-10-07
- **Mic sensitivity** — seven levels (0 / −6 / −12 / −18 / −24 / −32 / −40 dB) that lower the uploaded audio volume, so surrounding voices are less likely to be taken as you speaking (speak closer / louder to compensate)
- Removed two settings that real-device testing proved ineffective: server-side VAD threshold levels, and `semantic_vad`
- Fixed a reconnect race that could show a wrong connection status right after changing settings
- Help page: clarified that typos in the caption do not affect the conversation (subtitles come from a separate subtitle model)
- Desktop applies the gain to the captured audio before upload; Android rewrites the uplink frame via the SDK's read-write audio observer

## v1.4 — 2026-10-06
- Code cleanup and repo slimming, arm64-only build (APK 14.2 → 9.8 MB)
- First-launch usage-line fix; prebuilt packages discontinued (source-only releases)
- *(2026-10-07)* Custom launcher icon; default UI language changed to Chinese

## v1.3 — 2026-10-05
- Android: auto-connect on launch; usage shown as session + cumulative; help & privacy notes; log rotation
- Desktop: bilingual UI (Chinese default); usage estimates; credentials stored in Windows Credential Manager

## v1.2 — 2026-10-04
- Eight language tutors (EN / JA / RU / ZH / ES / FR / KO / DE)
- Bilingual UI (English / Chinese); Python 3.13 compatibility (removed `audioop`)
- **First public release — open-sourced on GitHub**

## v1.1 — 2026-10-04
- Three language tutors (English / Japanese / Russian)
- App renamed to 「实时外语对话 / Live Language Chat」; official + trial APK variants

## v1.0 — 2026-10-01
- First working version: Windows desktop full-duplex realtime voice chat (Qwen Omni Realtime), role presets, silence gate
- Android client built on Alibaba AOQ Client SDK (developed 2026-10-02/03)
