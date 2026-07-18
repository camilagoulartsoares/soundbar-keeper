@echo off
setlocal
title Desinstalar Soundbar Keeper V8 UltraBurst
schtasks /End /TN "Soundbar Keeper V8 UltraBurst" >nul 2>nul
schtasks /Delete /TN "Soundbar Keeper V8 UltraBurst" /F >nul 2>nul
wmic process where "name='pythonw.exe' and CommandLine like '%%soundbar_keeper_v8.py%%'" call terminate >nul 2>nul
rmdir /S /Q "%LOCALAPPDATA%\SoundbarKeeperV8" >nul 2>nul
echo V8 UltraBurst removida.
pause
