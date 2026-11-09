# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller — installateur autonome NoctisAuth_Setup.exe.

L'application compilée (dist/NoctisAuth.exe) est intégrée comme binaire :
l'utilisateur final ne télécharge donc qu'un seul fichier.
"""

from pathlib import Path
from PyInstaller.utils.hooks import collect_all

ROOT = Path(SPECPATH).resolve().parent
SRC = ROOT / 'src'

datas = [
    (str(ROOT / 'noctis.ico'), '.'),
    (str(ROOT / 'assets' / 'noctis_logo.png'), 'assets'),
    (str(ROOT / 'assets' / 'noctis_background.png'), 'assets'),
]
binaries = [(str(ROOT / 'dist' / 'NoctisAuth.exe'), '.')]
hiddenimports = []

_tmp = collect_all('customtkinter')
datas += _tmp[0]
binaries += _tmp[1]
hiddenimports += _tmp[2]

a = Analysis(
    [str(SRC / 'installer.py')],
    pathex=[str(SRC)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
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
    name='NoctisAuth_Setup',
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
