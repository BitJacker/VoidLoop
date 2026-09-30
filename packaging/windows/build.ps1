# Build the Windows deliverables of VoidLoop (run from the repository root, in PowerShell).
#   packaging\windows\build.ps1            -> out\VoidLoop-<ver>-windows-x64.exe (portable) and out\VoidLoop-<ver>-windows-x64.msi
# Needs: Python 3.8+ with `pip install -r requirements.txt pyinstaller`, and the .NET SDK for WiX (installed here if missing).
$ErrorActionPreference = "Stop"
Set-Location (Resolve-Path "$PSScriptRoot\..\..")
$version = (Select-String -Path "VoidLoop\__init__.py" -Pattern '__version__ = "([^"]+)"').Matches[0].Groups[1].Value
New-Item -ItemType Directory -Force -Path out | Out-Null
Write-Host "Building VoidLoop $version"

# 1) portable single-file exe
$env:VOIDLOOP_ONEFILE = "1"
python -m PyInstaller --noconfirm --clean --distpath dist\onefile --workpath build\onefile packaging\voidloop.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller (onefile) failed" }
Copy-Item dist\onefile\VoidLoop.exe "out\VoidLoop-$version-windows-x64.exe"

# 2) folder build, packaged as MSI
Remove-Item Env:VOIDLOOP_ONEFILE
python -m PyInstaller --noconfirm --clean --distpath dist --workpath build\folder packaging\voidloop.spec
if ($LASTEXITCODE -ne 0) { throw "PyInstaller (folder) failed" }
Copy-Item LICENSE, THIRD_PARTY_NOTICES.md dist\VoidLoop\

if (-not (Get-Command wix -ErrorAction SilentlyContinue)) {
    dotnet tool install --global wix --version 5.0.2
    $env:PATH += ";$env:USERPROFILE\.dotnet\tools"
}
wix extension add -g WixToolset.UI.wixext/5.0.2
wix build -arch x64 -ext WixToolset.UI.wixext `
    -d Version=$version -d AppDir=dist\VoidLoop -d IconPath=packaging\windows\voidloop.ico -d LicensePath=packaging\windows\license.rtf `
    -o "out\VoidLoop-$version-windows-x64.msi" packaging\windows\VoidLoop.wxs
if ($LASTEXITCODE -ne 0) { throw "wix build failed" }
Get-ChildItem out | Format-Table Name, Length
