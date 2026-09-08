@echo off
REM Project dashboard launcher. ASCII-only (no Chinese, no BOM) to avoid cmd codepage parse errors.
REM Placeholder {{TITLE}} is replaced by the init script with the project title; it is ASCII-safe.

set "PY=C:\Users\123\.workbuddy\binaries\python\versions\3.13.12\python.exe"
if not exist "%PY%" set "PY=C:\Users\123\.workbuddy\binaries\python\envs\default\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

cd /d "%~dp0"

if not exist "%PY%" (
  echo [ERROR] python not found.
  pause
  exit /b 1
)

REM Kill any old server on port 8320
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8320" ^| findstr "LISTENING"') do (
  taskkill /F /PID %%a >nul 2>&1
)
timeout /t 1 /nobreak >nul

echo {{TITLE}} starting on http://127.0.0.1:8320 ...
set PYTHONWARNINGS=ignore
set PYTHONUNBUFFERED=1

REM Start server in background, then wait for port before opening browser.
start "" "%PY%" -W ignore server.py 8320

set /a tries=0
:wait
timeout /t 1 /nobreak >nul
set /a tries+=1
netstat -ano 2>nul | findstr ":8320" | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 goto opened
if %tries% lss 15 goto wait
echo [WARN] server did not become ready in 15s.

:opened
start "" http://127.0.0.1:8320
echo Dashboard started. If browser did not open, visit http://127.0.0.1:8320
echo You can close this window; the server will keep running.
pause
