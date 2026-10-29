# Builds dist\DMEDoc.exe (PyInstaller) and dist\DMEDoc-Setup-<version>.exe (NSIS).
# Needs Python <= 3.14 (Panda3D has no wheel for newer versions):
#   pip install pyserial pyinstaller panda3d panda3d-gltf pillow
param(
    [string]$Python = "python",
    [string]$Makensis = "C:\Program Files (x86)\NSIS\makensis.exe"
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

& $Python -B tools\make_icon.py
& $Python -B -m unittest discover tests

& $Python -B -m PyInstaller --noconfirm --clean --onefile --windowed --uac-admin `
    --name DMEDoc --icon assets\dmedoc.ico `
    --add-data "assets;assets" `
    --collect-all panda3d --collect-all direct --collect-all gltf `
    --copy-metadata panda3d-gltf --copy-metadata panda3d `
    run_gui.py

& $Makensis /V2 installer.nsi
Get-ChildItem dist
