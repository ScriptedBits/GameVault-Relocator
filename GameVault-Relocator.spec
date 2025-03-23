# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules

hidden_imports = collect_submodules('PyQt5')

block_cipher = None

a = Analysis(
    ['GameVault-Relocator.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('updater.exe', '.'),         # Include updater.exe
        ('background.jpg', '.'),      # Include background.jpg in the root of the bundle
    ],
    hiddenimports=hidden_imports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
    cipher=block_cipher,
    optimize=0,
)

pyz = PYZ(a.pure, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='GameVault-Relocator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    console=False,
    version='version_info.rc',
)
