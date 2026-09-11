# -*- mode: python ; coding: utf-8 -*-
import sys
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules("smartcard") + collect_submodules("bs4") + collect_submodules("PIL") + collect_submodules("qrcode")

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("database/gold_shop.db", "database"),
        ("DATE_FIX_NOTES.txt", "."),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True,
    name="GoldShop", debug=False, bootloader_ignore_signals=False,
    strip=False, upx=False, console=False,
)
bundle = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="GoldShop")

if sys.platform == "darwin":
    app = BUNDLE(
        bundle,
        name="GoldShop.app",
        icon=None,
        bundle_identifier="com.goldshop.desktop",
        info_plist={
            "CFBundleName": "GoldShop",
            "CFBundleDisplayName": "GoldShop",
            "CFBundleShortVersionString": "2.9.0",
            "NSHighResolutionCapable": True,
        },
    )
