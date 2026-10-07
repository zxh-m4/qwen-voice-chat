# -*- coding: utf-8 -*-
"""界面文案字典(中/英)。默认中文(用户拍板);英文只覆盖界面与帮助文字,
不影响与模型的对话语言(由角色预设锁定)。两端(PC/安卓)措辞保持对齐。
"""
from __future__ import annotations

SUPPORTED_LANGUAGES = ("zh", "en")
DEFAULT_LANGUAGE = "zh"


def normalize_language(lang: str | None) -> str:
    """非法/空值一律回落默认(中文)。"""
    return lang if lang in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


HELP_ZH = """本应用是为了创造一个外语学习的语境环境,是本人的业余学习中第一次完成的应用,完全免费分享,如有疏漏之处,敬请见谅。
—— 笑晗

【关于语音模型】
感谢阿里云通义千问的实时语音大模型——它几乎能秒回,能听出我的发音问题,还能说三十多种语言。这个业余小作品能变成好用的口语陪练,全靠它。

【声明】
本应用为个人业余学习作品,与阿里云及通义官方无关;使用时需自行注册阿里云百炼账号并填写自己的 API Key,调用费用由使用者自行承担;本应用免费分享、仅供学习交流,请勿用于商业用途;代码以 MIT 许可开源,欢迎自由修改与二次开发;作者预计不再频繁更新,欢迎有兴趣的朋友接力完善。

【快速开始】
1. 双击打开窗口,自动连接,看到「聆听中」直接开口说话
2. 说完话(停约 1 秒)它会自动回复;它说话时你开口可以打断
3. 顶部下拉可切换角色,切换即开始新对话(上下文重置)
4. 右上角按钮可断开/重连;关闭窗口即友好结束
5. 首次使用:点右上角「设置」填入你自己的阿里云百炼凭据
   · API Key:百炼控制台 → API-KEY 管理 → 创建
   · 业务空间 ID:百炼控制台 → 业务空间列表(形如 llm-xxxxxxxx)
     注意:每个账号的业务空间 ID 不同,请填自己的,不要照抄别人的
   凭据只保存在本机(Windows 凭据管理器,失败时回退到本地文件),不会上传

【费用说明】
每次对话按你的百炼账号计费,关闭窗口即停止计费。窗口底部显示「本次 / 累计」两个费用数值:
累计从打开程序到退出持续累加(断开、换老师都不清零),退出程序自动归零。这两个数值都是估算值(按音频时长折算),准确账单请登录阿里云百炼控制台,在「账单明细」中查看。
· 常规一来一回约 0.4 元/小时
· 连着不说话也约 0.15 元/小时(静音门开启后会明显低于此值)
· 双方不停说的理论上限约 0.69 元/小时
估算只按声音/文字量与公开费率折算,最终以你的控制台账单为准

【八种语言】
下拉切换,切换即开始新对话;每位老师锁定自己的语言——无论你说什么语言,老师都用该语言回复,仅明确说「用中文解释/翻译」才切中文;中文老师反之,用英文解释。
· 英语老师 Tina · 日语老师 Ono Anna · 俄语老师 Katerina · 中文老师 Tina
· 西班牙语老师 Sonrisa · 法语老师 Emilien · 韩语老师 Sohee · 德语老师 Ingrid
(音色不合口味?百炼官方音色表有试听,换一行配置即可)

【隐私说明】
· 你的语音会实时上传至阿里云百炼进行识别与合成,用于生成对话回复;
· 你的 API Key 与业务空间 ID 仅保存在本机(Windows 凭据管理器),不会上传到任何其他服务器;
· 运行日志只记录事件类型与诊断信息,不记录任何对话内容。

【小提示】
· 回环问题:外放时它可能听到自己的声音(甚至打断自己)——请戴耳机使用即可解决(本程序不做自动回声防护,以保证你随时可以插话打断)
· 字幕有错字不代表没听懂——字幕由一个「字幕模型」生成,遇到发音不标准、有口音或专业词时容易写错,而负责对话的语音模型直接听你的原始声音,识别能力比字幕模型更强
· 没声音?检查系统声音设置里选对输出设备、音量没有静音
· 连接中断就点「连接」重新连上
· 运行日志在程序目录 app.log,只记录事件类型与诊断信息
"""

HELP_EN = """This app creates an immersive environment for practicing a foreign language. It is the first app I completed while learning in my spare time, and it is shared completely free of charge. Please forgive any rough edges.
— Xiaohan

[About the voice model]
Thanks to Alibaba Cloud Qwen realtime voice model — it replies almost instantly, picks up my pronunciation problems, and speaks more than thirty languages. This little hobby project became a usable speaking partner entirely because of it.

[Disclaimer]
This app is a personal hobby project, unaffiliated with Alibaba Cloud or Qwen official. You must register your own Alibaba Cloud Bailian account and enter your own API Key; usage charges are borne by you. This app is shared free of charge, for learning and exchange only — do not use it for commercial purposes. The code is open-sourced under the MIT license; feel free to modify and build upon it. The author does not expect to update it frequently; contributions are welcome.

[Quick start]
1. Double-click to open the window; it connects automatically — once the status shows "Listening", just start speaking
2. It replies automatically after you pause (about 1 second); you can interrupt by speaking while it talks
3. Switch tutors from the dropdown; switching starts a new conversation (context resets)
4. The top-right button disconnects/reconnects; closing the window ends the session gracefully
5. First use: click "Settings" (top-right) and enter your own Bailian credentials
   · API Key: Bailian console → API-KEY management → Create
   · Workspace ID: Bailian console → Workspace list (looks like llm-xxxxxxxx)
     Note: every account has a different workspace ID — use your own, do not copy another one
   Credentials are stored on this machine only (Windows Credential Manager, falling back to a local file), never uploaded

[Cost]
Each conversation is billed to your Bailian account; closing the window stops billing. The bottom bar shows two ESTIMATES: "This" (current session) and "Total" (accumulated from app start until exit — disconnecting or switching tutors does not reset it; closing the app does). For the exact bill, sign in to the Alibaba Cloud Bailian console and check "Billing details".
· A normal back-and-forth: about ¥0.4 / hour
· Staying connected without speaking: about ¥0.15 / hour (noticeably lower with the silence gate on)
· Theoretical ceiling if both sides never stop: about ¥0.69 / hour
The estimate is derived from audio/text volume and public rates; your console bill is authoritative

[Eight languages]
Switch from the dropdown; switching starts a new conversation. Each tutor locks to its own language — whatever language you speak, the tutor replies in that language, and switches to Chinese only when you explicitly say "explain in Chinese" or "translate". The Chinese tutor is the reverse: it explains in English.
· English tutor Tina · Japanese tutor Ono Anna · Russian tutor Katerina · Chinese tutor Tina
· Spanish tutor Sonrisa · French tutor Emilien · Korean tutor Sohee · German tutor Ingrid
(Not a fan of a voice? The official Bailian voice list has samples to audition — just change one line of configuration.)

[Privacy]
- Your voice is streamed to Alibaba Cloud Bailian for recognition and synthesis, to generate replies.
- Your API Key / Workspace ID stay on this machine (Windows Credential Manager) and are never sent anywhere else.
- The run log records event types and diagnostics only — never your conversation content.

[Tips]
· Echo: on speakers this app may hear its own voice (and even interrupt itself) — wearing headphones solves it (this program does no automatic echo protection, so you can interrupt it at any time)
· Typos in the caption do not mean it misunderstood you — the caption comes from a separate "subtitle model" that often mis-spells words with imperfect pronunciation, accents or jargon, while the voice model handling the conversation listens to your raw audio directly and recognizes your speech more accurately than the subtitle model does
· No sound? Check that the correct output device is selected and not muted in your system sound settings
· If the connection drops, click "Connect" to reconnect
· The run log lives in app.log next to the program, recording event types and diagnostics only
"""

UI: dict[str, dict] = {
    "zh": {
        "app_title": "实时外语对话 · Qwen Omni",
        "help_title": "使用说明",
        "btn_ok": "知道了",
        "lbl_role": "角色:",
        "btn_connect": "连接",
        "btn_disconnect": "断开",
        "btn_settings": "设置",
        "btn_help": "?",
        "lang_button": "EN",
        "usage_format": "本次 ¥{s:.3f} · 累计 ¥{t:.3f} · {mss}",
        "state_starting": "启动中…",
        "states": {
            "connecting": "连接中…",
            "ready": "聆听中",
            "speaking": "说话中",
            "interrupted": "已打断 · 聆听中",
            "closed": "已断开",
        },
        "presets": {
            "english_teacher": "英语老师",
            "japanese_teacher": "日语老师",
            "russian_teacher": "俄语老师",
            "chinese_teacher": "中文老师",
            "spanish_teacher": "西班牙语老师",
            "french_teacher": "法语老师",
            "korean_teacher": "韩语老师",
            "german_teacher": "德语老师",
        },
        "settings_title": "配置百炼凭据",
        "settings_intro": (
            "本应用不含任何 API Key。请填入你自己的阿里云百炼凭据"
            "(仅保存在本机:优先 Windows 凭据管理器,失败时回退到本地文件;不会随程序分享):"
        ),
        "settings_key_label": "API Key(百炼控制台 → API-KEY 管理 → 创建)",
        "settings_key_saved": "已保存(如需更换,请输入新的 Key)",
        "settings_ws_label": "业务空间 ID(百炼控制台 → 业务空间列表,形如 llm-xxxxxxxx)",
        "settings_ws_saved": "已保存(如需更换,请输入新的业务空间 ID)",
        "settings_mic_label": "麦克风灵敏度",
        "settings_mic_1": "很高 —— 默认,原样上传",
        "settings_mic_2": "高 —— 整体压低一点(−6 dB)",
        "settings_mic_3": "中 —— 整体压低较多(−12 dB)",
        "settings_mic_4": "低 —— 周围声音基本传不进去(−18 dB)",
        "settings_mic_5": "很低 —— 几乎只剩贴近大声说的声音(−24 dB)",
        "settings_mic_6": "极低 —— 压得更狠,需更靠近说(−32 dB)",
        "settings_mic_7": "极限 —— 压到最低,要贴麦说(−40 dB)",
        "settings_mic_note": (
            "整体压低上传音量:周围的声音更不容易被当成你在说话;"
            "调低后请靠近麦克风、说得清楚一些。更改在下次连接后生效。"
        ),
        "settings_err_key_required": "请填写 API Key(sk- 开头)",
        "settings_err_key_prefix": "API Key 应以 sk- 开头",
        "settings_err_ws_required": "请填写业务空间 ID(形如 llm-xxxxxxxx)",
        "btn_save": "保存",
        "btn_cancel": "取消",
        "sys_preset_switched": "已切换角色:{name}(开始新对话)",
        "sys_credentials_updated": "凭据已更新(已存入{loc}),重新连接",
        "sys_language_switched": "界面语言已切换",
        "loc_wincred": "Windows 凭据管理器",
        "loc_file": "本地文件",
        "sys_conn_closed": "连接关闭:{reason}",
        "sys_session_ended": "会话结束:{reason}",
        "err_connect_failed": "连接失败:{e}",
        "err_conn_error": "连接错误:{e}",
        "err_audio_open": "音频设备打开失败:{e}",
        "prefix_user": "你:",
        "prefix_ai": "AI:",
        "help": HELP_ZH,
    },
    "en": {
        "app_title": "Realtime Voice Chat · Qwen Omni",
        "help_title": "Help",
        "btn_ok": "Got it",
        "lbl_role": "Tutor:",
        "btn_connect": "Connect",
        "btn_disconnect": "Disconnect",
        "btn_settings": "Settings",
        "btn_help": "?",
        "lang_button": "中文",
        "usage_format": "This ¥{s:.3f} · Total ¥{t:.3f} · {mss}",
        "state_starting": "Starting…",
        "states": {
            "connecting": "Connecting…",
            "ready": "Listening",
            "speaking": "Speaking",
            "interrupted": "Interrupted · Listening",
            "closed": "Disconnected",
        },
        "presets": {
            "english_teacher": "English Tutor",
            "japanese_teacher": "Japanese Tutor",
            "russian_teacher": "Russian Tutor",
            "chinese_teacher": "Chinese Tutor",
            "spanish_teacher": "Spanish Tutor",
            "french_teacher": "French Tutor",
            "korean_teacher": "Korean Tutor",
            "german_teacher": "German Tutor",
        },
        "settings_title": "Bailian Credentials",
        "settings_intro": (
            "This app ships without any API Key. Enter your own Alibaba Cloud Bailian credentials"
            " (stored on this machine only: Windows Credential Manager with local-file fallback;"
            " never shared with the program):"
        ),
        "settings_key_label": "API Key (Bailian console → API-KEY management → Create)",
        "settings_key_saved": "Saved (enter a new one only if you want to replace it)",
        "settings_ws_label": "Workspace ID (Bailian console → Workspace list, looks like llm-xxxxxxxx)",
        "settings_ws_saved": "Saved (enter a new one only if you want to replace it)",
        "settings_mic_label": "Mic sensitivity",
        "settings_mic_1": "Very high — default, upload as-is",
        "settings_mic_2": "High — slightly lowered (−6 dB)",
        "settings_mic_3": "Medium — noticeably lowered (−12 dB)",
        "settings_mic_4": "Low — surrounding sounds mostly cut out (−18 dB)",
        "settings_mic_5": "Very low — only close, loud speech gets through (−24 dB)",
        "settings_mic_6": "Extremely low — pressed much harder (−32 dB)",
        "settings_mic_7": "Maximum — pressed to the minimum (−40 dB)",
        "settings_mic_note": (
            "Lowers the overall volume sent to the service: surrounding voices are less likely to"
            " be taken as you speaking. When lowered, speak closer to the mic and clearly."
            " Takes effect on the next connection."
        ),
        "settings_err_key_required": "Please enter your API Key (starts with sk-)",
        "settings_err_key_prefix": "API Key should start with sk-",
        "settings_err_ws_required": "Please enter your Workspace ID (looks like llm-xxxxxxxx)",
        "btn_save": "Save",
        "btn_cancel": "Cancel",
        "sys_preset_switched": "Switched tutor: {name} (new conversation)",
        "sys_credentials_updated": "Credentials updated (stored in {loc}), reconnecting",
        "sys_language_switched": "Interface language switched",
        "loc_wincred": "Windows Credential Manager",
        "loc_file": "local file",
        "sys_conn_closed": "Connection closed: {reason}",
        "sys_session_ended": "Session ended: {reason}",
        "err_connect_failed": "Connect failed: {e}",
        "err_conn_error": "Connection error: {e}",
        "err_audio_open": "Failed to open audio device: {e}",
        "prefix_user": "You: ",
        "prefix_ai": "AI: ",
        "help": HELP_EN,
    },
}
