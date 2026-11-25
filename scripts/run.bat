@echo off
REM Start backend (8000) and frontend (3000 or FRONT_PORT) in two windows.
set ROOT=%~dp0..
if "%FRONT_PORT%"=="" set FRONT_PORT=3000
start "FaceLock API" cmd /k "cd /d %ROOT%\app\backend && set GLOG_minloglevel=2 && .venv\Scripts\uvicorn main:app --host 127.0.0.1 --port 8000"
start "FaceLock Web" cmd /k "cd /d %ROOT%\app\frontend && npx next start -p %FRONT_PORT%"
timeout /t 6 >nul
start http://localhost:%FRONT_PORT%
