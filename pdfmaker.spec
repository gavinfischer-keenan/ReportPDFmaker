# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for PDF Maker
================================
Run with:
    pyinstaller pdfmaker.spec

Output: dist/PDFMaker/PDFMaker.exe  (one-folder bundle)
        dist/PDFMaker-1.0.0.zip     (zipped for distribution)

Requirements before building:
    pip install pyinstaller
    pip install -r requirements.txt
"""

import sys
from pathlib import Path

block_cipher = None

# Collect all data files (CustomTkinter themes, assets)
import customtkinter
ctk_path = Path(customtkinter.__file__).parent

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Include CustomTkinter themes and assets
        (str(ctk_path), 'customtkinter'),
    ],
    hiddenimports=[
        'customtkinter',
        'PIL._tkinter_finder',
        'fitz',
        'reportlab',
        'reportlab.pdfgen',
        'reportlab.lib',
        'reportlab.lib.pagesizes',
        'reportlab.lib.styles',
        'reportlab.lib.units',
        'reportlab.platypus',
        'docx',
        'docx2pdf',
        'pypdf',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'scipy',
        'pandas',
        'numpy',  # exclude unless 3D support needed
        'IPython',
        'jupyter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zfiles, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PDFMaker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # No console window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,              # Add: icon='assets/icon.ico' if you have one
    version_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PDFMaker',
)
