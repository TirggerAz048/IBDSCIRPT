# -*- mode: python ; coding: utf-8 -*-
"""
IBDspider.spec — PyInstaller 打包配置（精简版）

已排除项目未使用的第三方依赖，仅保留实际用到的库。
生成日期: 2026-06-01

===========================================================================
 项目实际依赖分析
===========================================================================

【实际使用的第三方库】
  ├── PyQt6                    GUI 框架（核心依赖）
  │   ├── PyQt6.QtCore
  │   ├── PyQt6.QtGui
  │   ├── PyQt6.QtWidgets
  │   ├── PyQt6.QtWebEngineWidgets   内嵌浏览器（DeepSeek 交互）
  │   ├── PyQt6.QtWebEngineCore
  │   ├── PyQt6.QtWebChannel
  │   ├── PyQt6.QtNetwork
  │   ├── PyQt6.QtPrintSupport
  │   ├── PyQt6.QtXml
  │   ├── PyQt6.QtSvg
  │   ├── PyQt6.QtPositioning
  │   ├── PyQt6.QtQuick
  │   ├── PyQt6.QtQml
  │   ├── PyQt6.QtOpenGL
  │   └── PyQt6.QtQuickWidgets
  ├── PyQt6-Fluent-Widgets    Fluent Design 风格组件库
  ├── requests                 HTTP 请求（HKEX/SEC/NASDAQ API）
  ├── beautifulsoup4           HTML 解析（HKEX 搜索页/SEC 嵌套链接/招股书章节）
  ├── PyMuPDF (fitz)           PDF 文本提取（港股/美股 PDF 文件）
  ├── openpyxl                 Excel 导出（公众号数据/IPO 数据）
  └── lxml                     被 beautifulsoup4 依赖（html.parser 后端）

【已排除 — 项目代码中未使用的库】
  ├── pandas                   ← 未 import，被 requests/openpyxl 的 hook 误拉入
  ├── numpy                    ← pandas 的依赖，连带排除
  ├── pyarrow                  ← pandas 的可选依赖，连带排除
  ├── cryptography             ← requests 的可选 TLS 后端，本项目用系统默认
  ├── certifi                  ← cryptography 的依赖，排除
  ├── win32com / pythoncom     ← ctypes.windll 已足够，pywin32 非必须
  ├── pywintypes               ← pywin32 组件，非必须
  ├── jinja2                   ← WeasyPrint/babel 等的依赖，项目未使用
  ├── charset_normalizer       ← requests 内部已有，但 PyInstaller 可能过度分析
  ├── urllib3                  ← requests 内部依赖，正常打包
  ├── setuptools               ← PyInstaller hook 自动包含，排除
  └── darkdetect               ← qfluentwidgets 的 import 依赖，不能排除！

【Python 标准库（自动包含，无需额外处理）】
  os, sys, re, json, time, datetime, hashlib, ast,
  subprocess, webbrowser, ctypes, typing, calendar

===========================================================================
"""

import os

# 项目根目录
project_root = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    ['main.py'],
    pathex=[project_root],
    binaries=[],
    datas=[
        ('mian.ico', '.'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # ── 数据分析/科学计算（项目完全未使用）──
        'pandas',
        'numpy',
        'pyarrow',
        'pandas._libs',
        'pandas._typing',
        'pandas.io',
        'pandas.core',
        'pandas.tseries',

        # ── 加密相关（requests 用系统默认 TLS 即可）──
        'cryptography',
        # 'certifi',          # requests 依赖（SSL 证书），不可排除

        # ── Windows COM（qframelesswindow/qfluentwidgets import 依赖，不可排除）──
        # 'win32com',         # qframelesswindow win32_utils 需要
        # 'win32com.client',
        # 'win32com.gen_py',
        # 'pythoncom',        # win32com 的依赖
        # 'pywintypes',       # pythoncom 的依赖

        # ── 模板引擎（项目未使用）──
        'jinja2',
        'markupsafe',

        # ── 打包/构建工具（PyInstaller hook 误拉入）──
        'setuptools',
        'pkg_resources',
        '_distutils_hack',

        # ── 系统主题检测（qfluentwidgets import 依赖，不可排除）──
        # 'darkdetect',  # 虽然项目固定暗黑不需要，但 qfluentwidgets 导入时依赖它

        # ── 其他无用模块 ──
        'pycparser',
        'pycparser.lextab',
        'pycparser.yacctab',
        'tzdata',
        'lxml.isoschematron',
        'lxml.objectify',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='IBDspider',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,       # --windowed: 不显示控制台窗口
    icon='mian.ico',
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
