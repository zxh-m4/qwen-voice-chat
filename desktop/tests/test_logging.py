# -*- coding: utf-8 -*-
"""日志配置(1MB 轮转,与安卓版"超限清理"同目的)的测试。"""
import logging
from logging.handlers import RotatingFileHandler

import pytest

from run import configure_logging


@pytest.fixture
def restore_root_handlers():
    """configure_logging 直接改 root handlers,测试后恢复,避免污染 pytest 日志捕获。"""
    root = logging.getLogger()
    saved = list(root.handlers)
    yield
    for h in list(root.handlers):
        if h not in saved:
            root.removeHandler(h)
            h.close()
    for h in saved:
        if h not in root.handlers:
            root.addHandler(h)


def _rotating_handlers():
    return [h for h in logging.getLogger().handlers if isinstance(h, RotatingFileHandler)]


class TestConfigureLogging:
    def test_installs_rotating_handler(self, tmp_path, restore_root_handlers):
        log_path = str(tmp_path / "app.log")
        configure_logging(log_path)
        hs = _rotating_handlers()
        assert len(hs) == 1
        assert hs[0].maxBytes == 1_000_000
        assert hs[0].backupCount == 1
        assert hs[0].baseFilename.endswith("app.log")

    def test_reconfigure_replaces_handler(self, tmp_path, restore_root_handlers):
        configure_logging(str(tmp_path / "a.log"))
        configure_logging(str(tmp_path / "b.log"))
        hs = _rotating_handlers()
        assert len(hs) == 1
        assert hs[0].baseFilename.endswith("b.log")

    def test_rotation_keeps_files_bounded(self, tmp_path, restore_root_handlers):
        configure_logging(str(tmp_path / "app.log"))
        log = logging.getLogger("rot-test")
        for _ in range(2400):
            log.info("x" * 1000)  # 约 2.4MB,必然触发轮转
        for h in _rotating_handlers():
            h.flush()
        assert (tmp_path / "app.log.1").exists()
        assert (tmp_path / "app.log").stat().st_size <= 1_100_000
        assert (tmp_path / "app.log.1").stat().st_size <= 1_100_000
        # backupCount=1:不产生第二个备份
        assert not (tmp_path / "app.log.2").exists()
