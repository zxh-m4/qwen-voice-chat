# -*- coding: utf-8 -*-
"""配置加载与接入地址推导。"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field


class ConfigError(Exception):
    """配置缺失或非法。"""


@dataclass
class Preset:
    """一个角色预设:提示词 + 专属音色 + 联网搜索开关。"""

    instructions: str
    voice: str = "Tina"
    enable_search: bool = False
    search_source: bool = False


@dataclass
class Config:
    api_key: str
    model: str = "qwen3.8-omni-flash-realtime"
    workspace_id: str = ""
    voice: str = "Tina"
    instructions: str = (
        "你是一个友好的实时语音助手,用简洁自然的口语回答,中英文都可以,"
        "用户说什么语言你就用什么语言回复。"
    )
    vad_type: str | None = "server_vad"
    vad_silence_ms: int = 800
    transcription_model: str | None = "gummy-realtime-v1"
    input_sample_rate: int = 16000
    output_sample_rate: int = 24000
    frame_ms: int = 100
    region_host: str = "cn-beijing.maas.aliyuncs.com"
    silence_gate: bool = True
    silence_gate_ms: int = 1500
    silence_threshold_rms: int = 600
    voiceprint_enabled: bool = False  # 黑名单制,实测区分度不足默认关(EchoGuard 替代)
    voiceprint_threshold: float = 0.50
    voiceprint_buffer_ms: int = 500
    voiceprint_model: str = ""   # 空 = 程序目录 models/3dspeaker_...onnx
    presets: dict = field(default_factory=dict)  # name -> Preset
    active_preset: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def _active(self) -> Preset | None:
        return self.presets.get(self.active_preset)

    @property
    def active_instructions(self) -> str:
        """选中预设的提示词;无预设时回退单 instructions(旧配置兼容)。"""
        p = self._active
        return p.instructions if p else self.instructions

    @property
    def active_voice(self) -> str:
        """选中预设的专属音色;无预设时回退全局 voice。"""
        p = self._active
        return p.voice if p else self.voice

    @property
    def active_search(self) -> bool:
        p = self._active
        return p.enable_search if p else False

    @property
    def active_search_source(self) -> bool:
        p = self._active
        return p.search_source if p else False

    @property
    def frame_bytes(self) -> int:
        """一个发送帧的字节数(PCM16 单声道)。"""
        return self.input_sample_rate * 2 * self.frame_ms // 1000

    @property
    def ws_url(self) -> str:
        if not self.api_key:
            raise ConfigError("api_key 为空:请在 config.json 或 DASHSCOPE_API_KEY 环境变量中配置")
        if self.api_key.startswith("sk-sp-"):
            # Token Plan 专属 key 固定走 token-plan 业务空间域名
            host = f"token-plan.{self.region_host}"
        elif self.workspace_id:
            host = f"{self.workspace_id}.{self.region_host}"
        else:
            host = "dashscope.aliyuncs.com"
        return f"wss://{host}/api-ws/v1/realtime?model={self.model}"

    @property
    def auth_header(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}"}


LOCAL_CONFIG_FILENAME = "config.local.json"
EXAMPLE_CONFIG_FILENAME = "config.example.json"


def ensure_config_file(path: str) -> None:
    """配置文件不存在时,自动从同目录的 config.example.json 复制一份。

    为什么这么做:仓库里只保留**不含任何凭据的模板**(config.example.json),
    而 config.json 本身被 .gitignore 排除。程序首次运行会生成一份空的
    config.json 让用户填 —— 这样用户填入真实 API Key 后不可能误提交到公开仓库,
    彻底消除「凭据泄露」这一类事故。
    """
    if os.path.isfile(path):
        return
    example = os.path.join(os.path.dirname(os.path.abspath(path)), EXAMPLE_CONFIG_FILENAME)
    try:
        with open(example, encoding="utf-8") as f:
            content = f.read()
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    except OSError as e:
        raise ConfigError(
            f"配置文件不存在,且无法从 {EXAMPLE_CONFIG_FILENAME} 生成: {e};"
            f"请手动把 {EXAMPLE_CONFIG_FILENAME} 复制为 {os.path.basename(path)}"
        ) from e


def local_config_path(config_path: str) -> str:
    """本地凭据文件路径(与 config.json 同目录;不随源码分享)。"""
    return os.path.join(os.path.dirname(os.path.abspath(config_path)), LOCAL_CONFIG_FILENAME)


def save_local_credentials(config_path: str, api_key: str, workspace_id: str) -> None:
    """保存用户输入的凭据到 config.local.json(优先级最高)。"""
    with open(local_config_path(config_path), "w", encoding="utf-8") as f:
        json.dump(
            {"api_key": api_key.strip(), "workspace_id": workspace_id.strip()},
            f, ensure_ascii=False, indent=2,
        )


def load_config(path: str) -> Config:
    """读取 JSON 配置文件;api_key 缺失时回退环境变量 DASHSCOPE_API_KEY。"""
    ensure_config_file(path)
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigError(f"配置文件不是合法 JSON: {path} ({e})") from e
    if not isinstance(data, dict):
        raise ConfigError(f"配置文件顶层必须是 JSON 对象: {path}")

    # 本地凭据文件(用户自己输入的,优先级最高;分享的包里不含它)
    local: dict = {}
    lp = local_config_path(path)
    if os.path.isfile(lp):
        try:
            with open(lp, encoding="utf-8") as lf:
                obj = json.load(lf)
                if isinstance(obj, dict):
                    local = obj
        except (json.JSONDecodeError, OSError):
            local = {}  # 损坏的本地文件忽略,回退 config.json

    api_key = (
        str(local.get("api_key", "")).strip()
        or data.pop("api_key", "")
        or os.environ.get("DASHSCOPE_API_KEY", "")
    )
    if not api_key:
        raise ConfigError("缺少 api_key:请在程序设置中填入你的百炼 API Key")
    if "请填" in api_key:
        raise ConfigError("config.json 里的 api_key 还是占位符,请填入真实 API Key")

    known = {
        "model", "workspace_id", "voice", "instructions", "vad_type",
        "vad_silence_ms", "transcription_model", "input_sample_rate",
        "output_sample_rate", "frame_ms", "region_host",
        "silence_gate", "silence_gate_ms", "silence_threshold_rms",
        "voiceprint_enabled", "voiceprint_threshold", "voiceprint_buffer_ms",
        "voiceprint_model",
        "active_preset",
    }
    ws_local = str(local.get("workspace_id", "")).strip()
    if ws_local:
        data["workspace_id"] = ws_local  # 本地凭据覆盖
    kwargs = {k: v for k, v in data.items() if k in known}
    extra = {k: v for k, v in data.items() if k not in known}

    presets: dict[str, Preset] = {}
    raw_presets = data.get("presets")
    if isinstance(raw_presets, dict):
        for name, spec in raw_presets.items():
            if not isinstance(spec, dict) or "instructions" not in spec:
                raise ConfigError(f"预设 '{name}' 格式错误:必须含 instructions 字段")
            presets[name] = Preset(
                instructions=str(spec["instructions"]),
                voice=str(spec.get("voice", "Tina")),
                enable_search=bool(spec.get("enable_search", False)),
                search_source=bool(spec.get("search_source", False)),
            )
    elif raw_presets is not None:
        raise ConfigError("presets 必须是 JSON 对象")

    active = kwargs.get("active_preset") or (next(iter(presets)) if presets else "")
    if presets and active not in presets:
        raise ConfigError(
            f"active_preset '{active}' 不存在,可选:{sorted(presets)}"
        )
    kwargs["active_preset"] = active

    return Config(api_key=api_key, presets=presets, extra=extra, **kwargs)
