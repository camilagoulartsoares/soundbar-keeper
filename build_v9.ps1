param(
    [switch]$SkipVenv
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = "C:\Users\camil\AppData\Local\Programs\Python\Python311\python.exe"
$VenvDir = Join-Path $ProjectRoot ".venv"
$VenvPython = Join-Path $VenvDir "Scripts\python.exe"
$DistExe = Join-Path $ProjectRoot "dist\PhilipsTAB4000KeepAliveV9\PhilipsTAB4000KeepAliveV9.exe"
$FinalExe = Join-Path $ProjectRoot "PhilipsTAB4000KeepAliveV9.exe"
$IssPath = Join-Path $ProjectRoot "PhilipsTAB4000KeepAliveV9.iss"
$SetupExe = Join-Path $ProjectRoot "Output\PhilipsTAB4000KeepAliveV9_Setup.exe"
$FinalSetup = Join-Path $ProjectRoot "PhilipsTAB4000KeepAliveV9_Setup.exe"

if (-not (Test-Path $Python)) {
    throw "Python 3.11 não encontrado em $Python"
}

if (-not $SkipVenv) {
    & $Python -m venv $VenvDir
    & $VenvPython -m pip install --upgrade pip
    & $VenvPython -m pip install -r (Join-Path $ProjectRoot "requirements.txt")
} elseif (-not (Test-Path $VenvPython)) {
    throw "Ambiente virtual ausente. Rode sem -SkipVenv na primeira vez."
}

& $VenvPython -m PyInstaller --noconfirm (Join-Path $ProjectRoot "PhilipsTAB4000KeepAliveV9.spec")
Copy-Item -Force $DistExe $FinalExe

$Iscc = @(
    "C:\Users\camil\AppData\Local\Programs\Inno Setup 6\ISCC.exe",
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $Iscc) {
    winget install --id JRSoftware.InnoSetup --exact --silent --accept-package-agreements --accept-source-agreements
    $Iscc = @(
        "C:\Users\camil\AppData\Local\Programs\Inno Setup 6\ISCC.exe",
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "C:\Program Files\Inno Setup 6\ISCC.exe"
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1
}

if (-not $Iscc) {
    throw "Inno Setup não encontrado após tentativa de instalação."
}

& $Iscc $IssPath
Copy-Item -Force $SetupExe $FinalSetup

Write-Host "Executável final: $FinalExe"
Write-Host "Instalador final: $FinalSetup"
