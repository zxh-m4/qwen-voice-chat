# 复现指南 —— 在任何一台 Windows 电脑上跑起来

实时中英对话窗口 · **纯云端方案,本地零推理**:老机器(如 配置较低的旧电脑)也绰绰有余,
只需要:Windows 10/11 64 位 + 能访问 aliyuncs.com 的网络 + 一个麦克风一副耳机。

二选一:

---

## 方式 A:免安装 exe(推荐,最省事)

1. 把整个 `dist\实时中英对话\` 文件夹拷到目标电脑(任意位置,如桌面);
2. 首次运行 exe,按弹窗填入你自己的凭据(Windows 上会存入**「Windows 凭据管理器」**,系统加密,
   条目名 `QwenVoiceChat/credentials`;写入失败或非 Windows 系统才会退回 exe 旁的 `config.local.json`);
   若想从旧机器迁移凭据,把旧机器的 `config.local.json` 拷到 exe 旁即可(启动时自动迁入凭据管理器,
   原文件保留,用完后建议删除)
   (内含你的 API Key,别外传);
3. 双击 `实时中英对话.exe`,看到「聆听中」即可说话;
4. (可选)右键 exe → 发送到 → 桌面快捷方式。

> exe 用 PyInstaller 打包,内含 Python 运行时和全部依赖,**目标机不需要装 Python**。

## 方式 B:源码运行(便于改代码)

1. 装 Python 3.10+(64 位,python.org 默认安装,勾选 Add to PATH);
2. 拷贝整个 `realtime_chat\` 文件夹到目标机;
3. 在文件夹里执行:
   ```bash
   pip install -r requirements.txt
   ```
4. 确认已在程序设置里填好你自己的 API Key(有额度);
5. 运行:
   ```bash
   python run.py
   ```
6. (可选)创建桌面快捷方式——在**本机**生成一个拷过去即可:
   ```powershell
   $ws = New-Object -ComObject WScript.Shell
   $lnk = $ws.CreateShortcut("$env:USERPROFILE\Desktop\实时中英对话.lnk")
   $lnk.TargetPath = "C:\Program Files\Python311\pythonw.exe"   # 目标机 pythonw 路径
   $lnk.Arguments = '"<程序文件夹>\run.py"'
   $lnk.WorkingDirectory = "<程序文件夹>"
   $lnk.Save()
   ```

---

## 旧电脑(低配置)特别说明

- **硬件没问题**:本项目不做任何本地 AI 推理,语音识别/对话/合音全在阿里云端,
  本地只有采集、播放、窗口,十几年前的 CPU 都带得动;
- 系统要求 Windows 10/11 64 位(若目标机还是 Win7/Win8,方式 B 需改用 Python 3.8
  并用旧版 PyInstaller,不推荐,优先 Win10);
- USB 麦克风/耳机即插即用;窗口用的是 **Windows 系统默认录音设备**,
  在系统声音设置里把默认麦克风选对即可。

## 首次运行检查单

1. 窗口顶部状态 = **聆听中**(不是"连接中…/已断开");
2. 对它说一句话,几秒内字幕出现「你:……」→ 上行通;
3. 它回复且**听得到声音** → 下行通;
4. 听不到声音:检查系统默认输出设备;AI 说话但被秒打断:外放回环,戴耳机;
5. 说话它没反应:系统默认麦克风选错了,或 `config.json` 的
   `silence_threshold_rms`(600)对你那支麦太高 → 调到 300~400;
6. 窗口红字 403/额度:API key 没额度了,换 key 或去百炼控制台充值;
7. 排障日志:程序目录 `app.log`(每次启动覆盖,含全部事件时间线)。

## 费用提醒(两台机器共用一个 key 也一样算)

- 说话约 0.4 元/小时;静音门开着时挂机≈0;单会话挂满 2 小时服务端自动断,
  窗口点「连接」即恢复(会清对话上下文,属正常)。

## 与闲聊窗口的关系

- 两者**完全独立**:独立目录、独立配置,互不影响;
- 可以同时装在一台机器上,互不干扰(但别同时抢同一个麦克风的关键场景混用)。
