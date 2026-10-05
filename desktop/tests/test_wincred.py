# -*- coding: utf-8 -*-
"""Windows 凭据管理器模块的测试(仅 Windows 运行;使用一次性 target 名,用毕即删)。"""
import sys
import uuid

import pytest

from rtchat import wincred

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="仅 Windows 有凭据管理器")


def fresh_target() -> str:
    return "QwenVoiceChat/test-" + uuid.uuid4().hex


class TestWinCred:
    def test_roundtrip(self):
        t = fresh_target()
        try:
            assert wincred.save({"api_key": "sk-test-123", "workspace_id": "llm-test"}, target=t)
            got = wincred.load(target=t)
            assert got == {"api_key": "sk-test-123", "workspace_id": "llm-test"}
        finally:
            wincred.delete(target=t)

    def test_missing_returns_none(self):
        assert wincred.load(target=fresh_target()) is None

    def test_delete_removes(self):
        t = fresh_target()
        try:
            wincred.save({"api_key": "x"}, target=t)
            assert wincred.delete(target=t)
            assert wincred.load(target=t) is None
        finally:
            wincred.delete(target=t)

    def test_overwrite(self):
        t = fresh_target()
        try:
            wincred.save({"api_key": "old"}, target=t)
            wincred.save({"api_key": "new"}, target=t)
            assert wincred.load(target=t) == {"api_key": "new"}
        finally:
            wincred.delete(target=t)
