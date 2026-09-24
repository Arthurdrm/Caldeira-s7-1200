# -*- mode: python ; coding: utf-8 -*-
"""Spec do PyInstaller para gerar o Simulador_Caldeira_S7_1200.exe (Windows 10/11).

Gera um único executável standalone (onefile) com janela gráfica (sem console).

Build:
    pyinstaller simulador_caldeira.spec --noconfirm --clean
Saída:
    dist/Simulador_Caldeira_S7_1200.exe
"""

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

hidden = (
    collect_submodules("src")
    + collect_submodules("src.simulador")
)

a = Analysis(
    ["simulador.py"],
    pathex=["src"],
    binaries=[],
    datas=[],
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["PyQt5", "PyQt6", "PySide2", "tkinter", "matplotlib"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="Simulador_Caldeira_S7_1200",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
