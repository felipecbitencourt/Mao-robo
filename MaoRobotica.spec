# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all
import os

block_cipher = None

# Dependências estáticas que quebram debaixo do capô
datas = [
    ('models/*', 'models/'),
    ('src/luva/python-project/TestGlove64.exe', 'src/luva/python-project/'),
    ('src/luva/gesture-images/*', 'src/luva/gesture-images/'),
    ('config.json', '.')
]
binaries = []
hiddenimports = [
    'mediapipe',
    'serial',
    'cv2',
    'numpy',
    'pygrabber',
    'pygrabber.dshow_graph',
    'comtypes',
]

# Captura hooks inteiros do PySide6 e MediaPipe
tmp_ret = collect_all('mediapipe')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

a = Analysis(
    ['main.py'],
    pathex=['src'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MaoRobotica',
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
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MaoRobotica',
)
