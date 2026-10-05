import pytest


@pytest.fixture(autouse=True)
def _isolate_wincred(request, monkeypatch):
    """测试默认禁用 Windows 凭据管理器:绝不读写开发者的真实凭据库。
    test_wincred.py 例外(它用一次性 target 名做真机往返并自清理)。"""
    if request.node.fspath and "test_wincred" in str(request.node.fspath):
        return
    from rtchat import wincred

    monkeypatch.setattr(wincred, "available", lambda: False)
    monkeypatch.setattr(wincred, "load", lambda target=None: None)
    monkeypatch.setattr(wincred, "save", lambda payload, target=None: False)
