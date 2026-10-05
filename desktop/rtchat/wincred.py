# -*- coding: utf-8 -*-
"""Windows 凭据管理器(Windows Credential Manager)存储——桌面版凭据的首选存放处。

为什么:凭据存进系统 vault 而不是明文文件;用户在「控制面板 → 凭据管理器 → Windows 凭据」
可见可删,不落明文。非 Windows 平台自动不可用(回退原有的 config.local.json 方案)。

实现:ctypes 直接调用 advapi32 的 CredReadW/CredWriteW/CredDeleteW,不引入任何第三方依赖。
注意:能读取当前用户凭据(明文文件同样能读)的本地恶意软件也可解出这里的内容——
这是桌面平台的共同边界;本模块的收益是"不落明文文件 + 用户可见可管理"。
"""
from __future__ import annotations

import ctypes
import json
import logging
import sys
from ctypes import wintypes

log = logging.getLogger(__name__)

CRED_TYPE_GENERIC = 1
CRED_PERSIST_LOCAL_MACHINE = 2
DEFAULT_TARGET = "QwenVoiceChat/credentials"
_USERNAME = "qwen-voice-chat"


class _Credential(ctypes.Structure):
    _fields_ = [
        ("Flags", wintypes.DWORD),
        ("Type", wintypes.DWORD),
        ("TargetName", wintypes.LPWSTR),
        ("Comment", wintypes.LPWSTR),
        ("LastWritten", wintypes.FILETIME),
        ("CredentialBlobSize", wintypes.DWORD),
        ("CredentialBlob", ctypes.POINTER(ctypes.c_byte)),
        ("Persist", wintypes.DWORD),
        ("AttributeCount", wintypes.DWORD),
        ("Attributes", ctypes.c_void_p),
        ("TargetAlias", wintypes.LPWSTR),
        ("UserName", wintypes.LPWSTR),
    ]


def available() -> bool:
    return sys.platform == "win32"


def save(payload: dict, target: str = DEFAULT_TARGET) -> bool:
    """把凭据(JSON)写入凭据管理器;成功返回 True。"""
    if not available():
        return False
    try:
        blob = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        buf = ctypes.create_string_buffer(blob, len(blob))
        cred = _Credential()
        cred.Type = CRED_TYPE_GENERIC
        cred.TargetName = target
        cred.CredentialBlobSize = len(blob)
        cred.CredentialBlob = ctypes.cast(buf, ctypes.POINTER(ctypes.c_byte))
        cred.Persist = CRED_PERSIST_LOCAL_MACHINE
        cred.UserName = _USERNAME
        ok = ctypes.windll.advapi32.CredWriteW(ctypes.byref(cred), 0)
        return bool(ok)
    except Exception:
        log.exception("写入 Windows 凭据管理器失败")
        return False


def load(target: str = DEFAULT_TARGET) -> dict | None:
    """读取凭据;不存在或失败返回 None。"""
    if not available():
        return None
    advapi32 = ctypes.windll.advapi32
    pcred = ctypes.POINTER(_Credential)()
    try:
        if not advapi32.CredReadW(target, CRED_TYPE_GENERIC, 0, ctypes.byref(pcred)):
            return None
        c = pcred.contents
        raw = ctypes.string_at(c.CredentialBlob, c.CredentialBlobSize)
        obj = json.loads(raw.decode("utf-8"))
        return obj if isinstance(obj, dict) else None
    except Exception:
        log.exception("读取 Windows 凭据管理器失败")
        return None
    finally:
        try:
            if pcred:
                advapi32.CredFree(pcred)
        except Exception:
            pass


def delete(target: str = DEFAULT_TARGET) -> bool:
    if not available():
        return False
    try:
        return bool(ctypes.windll.advapi32.CredDeleteW(target, CRED_TYPE_GENERIC, 0))
    except Exception:
        return False
