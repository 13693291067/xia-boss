# PowerShell launcher for project dashboard (fallback for the .bat).
# Run with: Right-click the file -> "Run with PowerShell".
# Pure-ASCII / UTF-8 with BOM; avoids cmd codepage parse errors entirely.
$ErrorActionPreference = "Stop"

$Port = 8320
$Py = "C:\Users\123\.workbuddy\binaries\python\versions\3.13.12\python.exe"
if (-not (Test-Path $Py)) {
    $Py = "C:\Users\123\.workbuddy\binaries\python\envs\default\Scripts\python.exe"
}
if (-not (Test-Path $Py)) {
    $Py = "python"
}

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ProjectDir

Write-Host "Cleaning up old server on port $Port..."
Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue | ForEach-Object {
    Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 1

if (-not (Test-Path $Py)) {
    Write-Host "[ERROR] python not found." -ForegroundColor Red
    pause
    exit 1
}

Write-Host "Launching project dashboard on http://127.0.0.1:$Port ..."
$env:PYTHONWARNINGS = "ignore"
$env:PYTHONUNBUFFERED = "1"

$proc = Start-Process -FilePath $Py -ArgumentList @("-W","ignore","server.py","$Port") -WorkingDirectory $ProjectDir -PassThru -WindowStyle Hidden

$tries = 0
$opened = $false
while ($tries -lt 15) {
    Start-Sleep -Seconds 1
    $tries++
    $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($conn) { $opened = $true; break }
}

Start-Process "http://127.0.0.1:$Port"
if ($opened) {
    Write-Host "Dashboard started. Browser should open." -ForegroundColor Green
} else {
    Write-Host "[WARN] Server did not become ready in 15s. Please visit http://127.0.0.1:$Port manually." -ForegroundColor Yellow
}
Write-Host "You can close this window; the server will keep running (PID=$($proc.Id))."
pause
