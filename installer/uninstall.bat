@echo off
setlocal

cd /d "%~dp0\.."
call :detect_python
if errorlevel 1 goto :done

echo Removendo inicializacao automatica...
%PYTHON_CMD% -m soundbar_keeper --uninstall-startup

echo Removendo pacote instalado...
%PYTHON_CMD% -m pip uninstall -y soundbar-keeper

echo Remocao concluida.
exit /b 0

:detect_python
python --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=python"
    exit /b 0
)

py --version >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_CMD=py"
    exit /b 0
)

echo Python nao encontrado no PATH.

:done
exit /b 0
