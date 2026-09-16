# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

# This spec is intentionally invoked from the repository root by CI and the
# documented local reproduction command. Avoid SPECPATH here because PyInstaller
# executes spec files with path semantics that can vary with the invocation path.
ROOT = Path.cwd().resolve()
if not (ROOT / "swirphoneos" / "studio.py").is_file():
    raise SystemExit("Run PyInstaller from the SwirPhoneOS repository root.")

a = Analysis(
    [str(ROOT / "packaging" / "studio_entry.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "swirphoneos" / "locales" / "catalogs.json"), "swirphoneos/locales"),
        (str(ROOT / "device_packs"), "device_packs"),
    ],
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
    name="SwirPhoneStudio",
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
