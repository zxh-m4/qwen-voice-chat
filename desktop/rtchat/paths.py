# -*- coding: utf-8 -*-
"""程序根目录定位:打包成 exe 后取 exe 所在目录,源码运行取项目目录。"""
import os
import sys


def app_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
