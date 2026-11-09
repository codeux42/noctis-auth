# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller — application Noctis Auth (onefile, sans console)."""

from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent
SRC = ROOT / 'src'

datas = [
    (str(ROOT / 'assets' / 'noctis_background.png'), 'assets'),
    (str(ROOT / 'assets' / 'noctis_logo.png'), 'assets'),
    (str(ROOT / 'assets' / 'discord.png'), 'assets'),
    (str(ROOT / 'noctis.ico'), '.'),
]

a = Analysis(
    [str(SRC / 'noctis_auth.py')],
    pathex=[str(SRC)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
    name='NoctisAuth',
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
    icon=[str(ROOT / 'noctis.ico')],
)
