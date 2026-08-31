@echo off
echo ========================================================
echo Smjrifle Desktop Reminder - Windows Standalone Builder
echo ========================================================

echo 1. Installing requirements...
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

echo 2. Compiling Windows executable...
pyinstaller --noconsole --onefile ^
  --name "SmjrifleReminder" ^
  --icon "icon.ico" ^
  --add-data "character.gif;." ^
  --add-data "icon.png;." ^
  --add-data "icon.ico;." ^
  --add-data "assets;assets" ^
  -y --clean ^
  main.py

echo 3. Packaging distribution archive...
powershell Compress-Archive -Force -Path dist/SmjrifleReminder.exe, assets, character.gif, icon.png, icon.ico, README.md, LICENSE -DestinationPath dist/SmjrifleReminder-Windows.zip

echo.
echo ========================================================
echo Build complete! Executable is in: dist/SmjrifleReminder.exe
echo Zip archive is in: dist/SmjrifleReminder-Windows.zip
echo ========================================================
pause
