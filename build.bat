@echo off
echo Installing PyInstaller...
pip install pyinstaller

echo.
echo Building iPhoneSpoofer.exe ...
pyinstaller ^
  --onefile ^
  --add-data "templates;templates" ^
  --uac-admin ^
  --name "iPhoneSpoofer" ^
  --hidden-import=pymobiledevice3 ^
  --hidden-import=flask ^
  main.py

echo.
if exist "dist\iPhoneSpoofer.exe" (
    echo SUCCESS: dist\iPhoneSpoofer.exe is ready.
) else (
    echo BUILD FAILED. Check output above.
)
pause
