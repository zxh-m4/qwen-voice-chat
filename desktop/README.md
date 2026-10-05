# 实时中英对话窗口(Qwen Omni Realtime)

独立的全双工实时语音对话桌面应用:持续聆听、随时打断、中英文(含混合)自由对话,
语音进、语音出,窗口内同步字幕。基于阿里云百炼 `qwen3.8-omni-flash-realtime` API,
WebSocket 直连,ASR/LLM/TTS 全部由云端端到端完成,本地只负责采麦、播放和窗口。

> **要在另一台电脑复现?看 [REPRODUCE.md](REPRODUCE.md)**——免安装 exe 打包
> (`dist\实时中英对话\`,双击即用)与源码两条路,含 旧电脑 老机器说明与首跑检查单。

## 运行

```bash
pip install -r requirements.txt   # 已装可跳过
python run.py                     # 启动窗口(自动连接)
```

- 窗口打开后自动握手并开麦,看到「聆听中」即可直接说话。
- **角色切换**:窗口顶部下拉框选「英语老师 / 百科全书 / 风趣幽默」——
  切换即断开重连(换人设自动清对话上下文),同一模型不同提示词人格。
  **三角色全部锁死全程英文**(仅明确说「用中文解释/翻译」才切中文),想让 AI 说
  中文要么提出例外、要么临时改 config 对应预设的语言约定。
  - 英语老师:慢速清晰、纠发音;
  - 百科全书:**开启官方联网搜索**(`enable_search`,带来源),不确定就明说;
  - 风趣幽默:先答有用再抖机灵。
- AI 正在说话时开口,会自动打断它(服务端 VAD + 本地清播放队列)。
- 右上角按钮断开/重连;关闭窗口会发 `session.finish` 优雅结束会话。
- 运行日志写入 `app.log`(排障用:声音/转写/打断事件时间线全在里面)。

## 回声防护(EchoGuard:AI 播放期间停收)

上行链路:麦克风 → 静音门(省钱)→ **回声防护(挡 AI 回环)** → 上传。

**AI 播放期间,麦克风数据直接不上传**(结束后 300ms 残余宽限再恢复)——外放时
AI 不会再"接自己的话",回环物理性消失;你和其他人的声音全程零影响。
代价:AI 说话时插话无效(收音暂停),等它说完再说。

> 备用:声纹门(黑名单制,`voiceprint_enabled` 默认 **false**)。实测结论:CAM++ 对
> 外放失真回环的声纹得分(0.10)与人声(0.01)无判决间隔,故不作主方案;模型保留在
> `models\`,想启用改配置即可。

## 配置(config.json)

首次运行时程序会自动把仓库里的 `config.example.json` 复制为 `config.json`,
你把凭据填进 `config.json` 即可。**`config.json` 已被 `.gitignore` 排除**,
填了真实 API Key 也不会误提交到公开仓库(仓库里只保留不含凭据的模板)。

**推荐直接在程序界面里输入凭据**(点「设置」按钮,或首次启动时按提示填)——凭据会存到
`config.local.json`(同样已被 gitignore 排除,且优先级最高,不会误提交);
手动填进 `config.json` 也安全,两种文件都已被仓库的 .gitignore 排除。

| 字段 | 说明 | 默认 |
|---|---|---|
| `api_key` | 百炼 API Key(`sk-` 开头)。也可用环境变量 `DASHSCOPE_API_KEY` | — |
| `workspace_id` | 业务空间 ID,决定接入域名 | `llm-xxxxxxxx` |
| `model` | 模型名 | `qwen3.8-omni-flash-realtime` |
| `voice` | 音色(56 选 1,如 `Tina`/`Ethan`/`Zane`) | `Tina` |
| `vad_type` | `server_vad` / `semantic_vad` / `null`(手动模式) | `server_vad` |
| `vad_silence_ms` | 静音多久判定说完(200~6000) | `800` |
| `silence_gate` | 静音门:连续静音停发音频,挂机不烧钱 | `true` |
| `silence_gate_ms` | 静音多久才停发(滞回,须 > vad_silence_ms) | `1500` |
| `silence_threshold_rms` | 静音判定阈值;**说话 AI 听不到就调低**,环境吵老接话就调高 | `600` |
| `transcription_model` | 用户语音转写模型 | `gummy-realtime-v1` |
| `presets` | 角色预设集:`{name: {instructions, enable_search, search_source}}` | 三角色见 config.json |
| `active_preset` | 当前角色(窗口下拉框切换时自动改此值并重连) | `english_teacher` |
| `instructions` | 无预设时的旧版单提示词(向后兼容) | 中英友好助手 |

key 类型与域名:`sk-sp-`(Token Plan 订阅)自动走 `token-plan.` 域名;
普通 `sk-` 按量 key 走 `workspace_id` 域名;无 workspace 走公共域名 `dashscope.aliyuncs.com`。

## 测试(TDD,47 项)

```bash
python -m pytest tests/ -q     # 纯逻辑:配置/协议/帧切分/会话状态机(含打断逻辑)
python smoke_connect.py        # 真实握手烟雾测试(不发音频,几乎不产生费用)
python test_dialogue.py        # 全链路:本地 WAV 灌入->VAD->转写->模型语音回复(存 reply_from_model.wav)
```

`test_dialogue.py` 需要同目录 `test_voice.wav`(可用 PowerShell System.Speech 生成)。

## 计费与限制(qwen3.8-omni-flash-realtime)

- 音频:输入 7 token/秒、输出 12.5 token/秒;北京价格 6 / 12 元每百万 token
  → 说话约 0.4 元/小时;**静音门开着时挂机 ≈ 0 元**(真机实测静置发送比 0%)。
- 多轮对话输入 token 逐轮累积(历史重复计入);单会话最长 120 分钟(断开后不计费)。
- 限流 60 RPM / 2M TPM;免费额度仅北京地域、100 万 token、90 天。

## 已知边界

- **外放回环风险**:麦克风在 AI 播放期间持续采集(与官方示例一致),外放音量大时
  服务端 VAD 可能把 AI 自己的话当用户输入,**建议戴耳机**;戴耳机无此问题。
- 播放采样率 24kHz,由 sounddevice 直接按 24000Hz 输出,声卡驱动负责混音。
- 断网/403(额度用尽)会显示在窗口底部红字,点「连接」重试。
- 会话不可复用:重连会重建会话(上下文从头开始)。

## 代码结构

```
run.py                入口
config.example.json    配置模板(首次运行自动复制为 config.json,不含凭据)
rtchat/config.py      配置加载 + 域名推导          [有测试]
rtchat/protocol.py    协议消息构建/解析            [有测试]
rtchat/frames.py      PCM 帧切分 + 播放队列        [有测试]
rtchat/session.py     会话状态机(打断/分发核心)   [有测试]
rtchat/audio_io.py    麦克风采集 + 声卡播放
rtchat/connection.py  WebSocket 连接层(30s 心跳)
rtchat/app.py         Tkinter 窗口(主线程 after 轮询 UI 队列)
smoke_connect.py / test_dialogue.py   联调脚本
```
