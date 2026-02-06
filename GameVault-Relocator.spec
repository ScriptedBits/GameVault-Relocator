# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['GameVault-Relocator.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('updater.exe', '.'),         # Include updater.exe
        ('background.jpg', '.'),      # Include background.jpg in the root
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)  # ← fixed: removed cipher=block_cipher

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
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='version_info.txt', 
)