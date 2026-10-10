# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置(桌面版)。

要点:
1. ``icon='app.ico'``  —— 让生成的 exe 内嵌我们的图标。不写这行,PyInstaller
   会塞进 Windows 记事本的默认图标(2026-10-10 的 v1.5-pre 包就是这样)。
2. ``datas`` 里带上 ``app.ico`` —— 程序运行时 rtchat/paths.app_dir() 会在 exe
   同目录找它来设窗口/任务栏图标,不打包进去的话窗口图标是空的。
3. ``datas`` 里带上 ``config.example.json`` —— 程序首次运行会在 exe 同目录找
   它并自动复制成 config.json(见 rtchat/config.py:ensure_config_file)。
   不带的话分发出去的包一启动就弹「配置文件不存在」。
4. 不打包 numpy —— v1.5-pre 起音频处理已改纯 Python(array 模块)实现,
   省掉约 46 MB(numpy.libs 37 MB + numpy 5 MB 及其依赖)。
"""
from PyInstaller.utils.hooks import collect_all

datas = [('app.ico', '.'), ('config.example.json', '.')]
binaries = []
hiddenimports = ['websocket', 'sounddevice']

# sounddevice 需要带上它自带的 PortAudio 运行库
tmp_ret = collect_all('sounddevice')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # numpy 必须显式排除:它是 sounddevice 的可选 extra 依赖,但本项目音频处理
    # 已改纯 Python(array 模块)实现,不 import numpy。不排除的话 collect_all
    # 会把它连 numpy.libs 一起收进来,包体积从 ~28 MB 涨到 ~74 MB。
    excludes=['numpy'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='实时外语对话',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app.ico',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='实时外语对话',
)

# 收尾:PyInstaller 的 datas 在 COLLECT 模式下会落到 _internal/ 里,而
# rtchat/paths.app_dir() 在打包后取的是 exe 所在目录(exe 同级)。所以这里
# 再复制一份到包根 —— 图标供运行时读取,配置模板供首次运行自动生成 config.json。
import shutil as _sh, os as _os
_root = _os.path.join('dist', '实时外语对话')
for _name in ('app.ico', 'config.example.json'):
    if _os.path.exists(_name) and _os.path.isdir(_root):
        _sh.copy2(_name, _os.path.join(_root, _name))
        print('post-build: %s -> %s' % (_name, _os.path.join(_root, _name)))

