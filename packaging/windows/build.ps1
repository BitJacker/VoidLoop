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

# Harvest the PyInstaller folder into a WiX fragment (every file except the launcher, which carries the shortcuts).
$appDir = (Resolve-Path dist\VoidLoop).Path
New-Item -ItemType Directory -Force build | Out-Null
$frag = "build\AppFiles.wxs"
$script:n = 0
$script:refs = New-Object System.Collections.Generic.List[string]
function Esc($t) { [System.Security.SecurityElement]::Escape($t) }
function Emit-Dir($path, $indent) {
    $sb = New-Object System.Text.StringBuilder
    foreach ($f in Get-ChildItem -LiteralPath $path -File) {
        if ($path -eq $appDir -and $f.Name -eq "VoidLoop.exe") { continue }
        $script:n++
        $id = "C$($script:n)"
        [void]$sb.AppendLine("$indent<Component Id=`"$id`" Guid=`"*`"><File Id=`"F$($script:n)`" Source=`"$(Esc $f.FullName)`" KeyPath=`"yes`" /></Component>")
        $script:refs.Add($id)
    }
    foreach ($d in Get-ChildItem -LiteralPath $path -Directory) {
        $script:n++
        $did = "D$($script:n)"
        $inner = Emit-Dir $d.FullName ($indent + "  ")
        [void]$sb.AppendLine("$indent<Directory Id=`"$did`" Name=`"$(Esc $d.Name)`">")
        [void]$sb.Append($inner)
        [void]$sb.AppendLine("$indent</Directory>")
    }
    return $sb.ToString()
}
$body = Emit-Dir $appDir "      "
$refXml = ($script:refs | ForEach-Object { "      <ComponentRef Id=`"$_`" />" }) -join "`n"
@"
<?xml version="1.0" encoding="utf-8"?>
<Wix xmlns="http://wixtoolset.org/schemas/v4/wxs">
  <Fragment>
    <DirectoryRef Id="INSTALLFOLDER">
$body    </DirectoryRef>
  </Fragment>
  <Fragment>
    <ComponentGroup Id="AppFiles">
$refXml
    </ComponentGroup>
  </Fragment>
</Wix>
"@ | Set-Content -Encoding utf8 $frag
Write-Host "harvested $($script:refs.Count) files into $frag"

wix extension add -g WixToolset.UI.wixext/5.0.2
wix build -arch x64 -ext WixToolset.UI.wixext `
    -d Version=$version -d AppDir=dist\VoidLoop -d IconPath=packaging\windows\voidloop.ico -d LicensePath=packaging\windows\license.rtf `
    -o "out\VoidLoop-$version-windows-x64.msi" packaging\windows\VoidLoop.wxs $frag
if ($LASTEXITCODE -ne 0) { throw "wix build failed" }
Get-ChildItem out | Format-Table Name, Length
