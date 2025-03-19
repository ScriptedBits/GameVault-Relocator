# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules

hidden_imports = collect_submodules('PyQt5')

block_cipher = None

a = Analysis(
    ['GameVault-Relocator-1.2.py'],  # Your main script
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=hidden_imports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,     # Whether to bundle everything into a single archive
    cipher=block_cipher,
    optimize=0,          # Optimization level (0: none)
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
    runtime_tmpdir=None,  # Temporary directory
    console=False,        # Hide console window (set to True for console apps)
	version="version_info.rc",  # Embed version info in the .exe
)
