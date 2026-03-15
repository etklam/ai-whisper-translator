# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, copy_metadata


PROJECT_ROOT = Path(SPECPATH).resolve().parents[1]

hiddenimports = [
    "pysrt",
    "numpy",
    "soundfile",
    "yt_dlp",
]

datas = [
    (str(PROJECT_ROOT / "src" / "translation" / "prompts.json"), "src/translation"),
]
datas += collect_data_files("soundfile")
datas += copy_metadata("yt_dlp")

binaries = []
binaries += collect_dynamic_libs("soundfile")

a = Analysis(
    [str(PROJECT_ROOT / "main.py")],
    pathex=[str(PROJECT_ROOT)],
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
    [],
    exclude_binaries=True,
    name="ai-whisper-translator",
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
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ai-whisper-translator",
)
