#!/bin/zsh
set -e
cd "${0:A:h}"
export PYINSTALLER_CONFIG_DIR="$PWD/.pyinstaller-cache"
python3 -m venv .build-venv
. .build-venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm --clean GoldShop.spec
codesign --force --deep --sign - dist/GoldShop.app
ditto -c -k --sequesterRsrc --keepParent dist/GoldShop.app GoldShop_macOS_AppleSilicon.zip
echo "สร้าง GoldShop_macOS_AppleSilicon.zip สำเร็จ"
