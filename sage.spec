# sage.spec
# PyInstaller spec file for Sage application

# -*- mode: python ; coding: utf-8 -*-

import sys
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

hidden_imports = collect_submodules('cryptography')
hidden_imports = collect_submodules('openai')
hidden_imports = collect_submodules('rich')
hidden_imports = collect_submodules('prompt_toolkit')
hidden_imports = collect_submodules('psutil')
hidden_imports = collect_submodules('getpass')
hidden_imports = collect_submodules('socket')
hidden_imports = collect_submodules('platform')
hidden_imports = collect_submodules('subprocess')
hidden_imports = collect_submodules('base64')

a = Analysis(
    ['sage.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('Get_API_Key.txt', '.'), 
        ('system_prompt.txt', '.'),  
        ('config.py', '.'),
        ('conversation.py', '.'),
        ('commands.py', '.'),
        ('capture_tool.py', '.'),
        ('config.py', '.'),
        ('conversation.py', '.'),
        ('commands.py', '.'),
        ('capture_tool.py', '.'),   
        ('constants.py', '.'),  
        ('utils.py', '.'),
        ('__pycache__', '.'),
    ],
    hiddenimports=hidden_imports,
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
    name='sage',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Set to False if you don't want a terminal window
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='sage',
)
