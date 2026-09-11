@echo off
setlocal
cd /d "%~dp0"
set PYINSTALLER_CONFIG_DIR=%CD%\.pyinstaller-cache
py -3.12 --version >nul 2>nul
if errorlevel 1 (
  echo กรุณาติดตั้ง Python 3.12 แบบ 64-bit จาก https://www.python.org/downloads/windows/
  pause
  exit /b 1
)
py -3.12 -m venv .build-venv
call .build-venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m PyInstaller --noconfirm --clean GoldShop.spec
where iscc >nul 2>nul
if %errorlevel%==0 (
  iscc GoldShopInstaller.iss
  echo Created installer\GoldShop_Setup_Windows.exe
) else (
  powershell -NoProfile -Command "Compress-Archive -Path 'dist\GoldShop\*' -DestinationPath 'GoldShop_Windows_Portable.zip' -Force"
  echo Inno Setup not found. Created GoldShop_Windows_Portable.zip
)
endlocal
