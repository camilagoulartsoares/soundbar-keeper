@echo off
setlocal

cd /d "%~dp0\.."
call :detect_python
if errorlevel 1 goto :error

echo [1/3] Instalando o pacote em modo editavel...
%PYTHON_CMD% -m pip install -e .
if errorlevel 1 goto :error

echo [2/3] Registrando inicializacao automatica...
%PYTHON_CMD% -m soundbar_keeper --install-startup
if errorlevel 1 goto :error

echo [3/3] Instalacao concluida.
echo Execute com: %PYTHON_CMD% -m soundbar_keeper
exit /b 0

:error
echo Falha durante a instalacao.
exit /b 1

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
exit /b 1
