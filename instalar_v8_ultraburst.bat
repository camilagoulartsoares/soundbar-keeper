@echo off
setlocal EnableExtensions
title Instalar Soundbar Keeper V8 UltraBurst
cd /d "%~dp0"

echo.
echo =============================================
echo      SOUNDBAR KEEPER V8 - ULTRABURST
echo =============================================
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON=py"
    for /f "delims=" %%I in ('py -c "import sys; print(sys.executable)"') do set "PYEXE=%%I"
) else (
    where python >nul 2>nul
    if errorlevel 1 (
        echo Python nao foi encontrado.
        echo Instale o Python 3 marcando Add Python to PATH.
        pause
        exit /b 1
    )
    set "PYTHON=python"
    for /f "delims=" %%I in ('python -c "import sys; print(sys.executable)"') do set "PYEXE=%%I"
)

echo Instalando componentes necessarios...
%PYTHON% -m pip install --user --disable-pip-version-check numpy sounddevice pystray pillow
if errorlevel 1 (
    echo.
    echo Falha ao instalar componentes.
    pause
    exit /b 1
)

set "DEST=%LOCALAPPDATA%\SoundbarKeeperV8"
if not exist "%DEST%" mkdir "%DEST%"
copy /Y "%~dp0soundbar_keeper_v8.py" "%DEST%\soundbar_keeper_v8.py" >nul

for %%F in ("%PYEXE%") do set "PYDIR=%%~dpF"
set "PYW=%PYDIR%pythonw.exe"
if not exist "%PYW%" set "PYW=%PYEXE%"

echo Encerrando e removendo tarefas antigas...
schtasks /End /TN "Soundbar Keeper V7 Silent" >nul 2>nul
schtasks /Delete /TN "Soundbar Keeper V7 Silent" /F >nul 2>nul
schtasks /End /TN "Soundbar Keeper V8 UltraBurst" >nul 2>nul
schtasks /Delete /TN "Soundbar Keeper V8 UltraBurst" /F >nul 2>nul
schtasks /Delete /TN "Soundbar Keeper" /F >nul 2>nul

rem Fecha instancias antigas do script sem encerrar todos os programas Python do computador.
wmic process where "name='pythonw.exe' and (CommandLine like '%%soundbar_keeper_v7.py%%' or CommandLine like '%%soundbar_keeper_v8.py%%')" call terminate >nul 2>nul

echo Criando inicializacao automatica...
schtasks /Create /TN "Soundbar Keeper V8 UltraBurst" /SC ONLOGON /RL LIMITED /TR "\"%PYW%\" \"%DEST%\soundbar_keeper_v8.py\"" /F
if errorlevel 1 (
    echo.
    echo Nao foi possivel criar a tarefa automatica.
    echo Execute este arquivo como administrador.
    pause
    exit /b 1
)

echo Iniciando V8 UltraBurst...
start "" "%PYW%" "%DEST%\soundbar_keeper_v8.py"

echo.
echo Instalacao concluida.
echo Procure o icone azul perto do relogio do Windows.
echo Configuracao: %DEST%\config.json
echo.
pause
