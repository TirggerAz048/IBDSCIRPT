# -*- mode: python ; coding: utf-8 -*-
"""
IBDspider_mac.spec — macOS 打包配置

用法（必须在 macOS 上执行）：
    pyinstaller IBDspider_mac.spec --noconfirm

产物：
    dist/IBD Spider.app

注意：
  1. PyInstaller 不支持跨平台打包，此文件只能在 Mac 上运行
  2. Apple Silicon 与 Intel 通用（target_arch=None 表示跟随当前解释器架构）
     若要打通用二进制，需在对应架构的机器上分别打包，或用 universal2 Python
  3. qframelesswindow / pywin32 等 Windows 专属依赖已排除
"""

import os
import sys

project_root = os.path.dirname(os.path.abspath(SPEC))

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[project_root],
    binaries=[],
    datas=[
        ('mian.ico', '.'),
    ],
    hiddenimports=[
        'PyQt6.QtWebEngineCore',
        'PyQt6.QtWebEngineWidgets',
        'PyQt6.QtWebChannel',
        'PyQt6.QtPrintSupport',
        'PyQt6.QtNetwork',
        # qfluentwidgets 动态引用，静态分析易漏
        'darkdetect',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # ── Windows 专属，macOS 上必须排除 ──
        'win32com',
        'win32com.client',
        'win32com.gen_py',
        'win32com.server',
        'pythoncom',
        'pywintypes',
        'win32',
        'win32api',
        'win32con',
        'win32gui',
        'win32ui',
        'win32print',
        'win32process',
        'win32event',
        'win32trace',
        'win32traceutil',
        'win32comext',
        'pywin',
        # 打包后会因缺失 Windows DLL 直接崩溃的 qframelesswindow 子模块
        'qframelesswindow.utils.win32_utils',
        'qframelesswindow.windows.window_effect',

        # ── 数据分析/科学计算（项目未使用）──
        'pandas',
        'numpy',
        'pyarrow',
        'matplotlib',
        'scipy',

        # ── 模板引擎（项目未使用）──
        'jinja2',
        'markupsafe',

        # ── 构建工具（hook 误拉入）──
        'setuptools',
        'pkg_resources',
        '_distutils_hack',

        # ── 其他无用模块 ──
        'pycparser',
        'pycparser.lextab',
        'pycparser.yacctab',
        'lxml.isoschematron',
        'lxml.objectify',
        'IPython',
        'pytest',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='IBD Spider',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='mian.icns',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='IBD Spider',
)

app = BUNDLE(
    coll,
    name='IBD Spider.app',
    icon='mian.icns',
    bundle_identifier='com.ibdspider.app',
    info_plist={
        'CFBundleName': 'IBD Spider',
        'CFBundleDisplayName': 'IBD Spider',
        'CFBundleShortVersionString': '2.0',
        'CFBundleVersion': '2.0',
        'LSMinimumSystemVersion': '11.0',
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False,
    },
)
