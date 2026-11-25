@echo off
REM One-command setup for Windows.  Usage: scripts\setup.bat
setlocal
set ROOT=%~dp0..
where python >nul 2>nul || (echo Python 3.10-3.12 is required: https://www.python.org/downloads/ & exit /b 1)
where node >nul 2>nul || (echo Node.js 18+ is required: https://nodejs.org & exit /b 1)
python -c "import sys; assert (3,10) <= sys.version_info[:2] <= (3,12), 'Python 3.10-3.12 required'" || exit /b 1

echo ==^> Backend: virtual environment + packages
cd /d "%ROOT%\app\backend"
if not exist .venv python -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip -q
.venv\Scripts\python -m pip install -q -r requirements.txt || exit /b 1
if "%DEV%"=="1" .venv\Scripts\python -m pip install -q -r requirements-dev.txt

echo ==^> Models
.venv\Scripts\python "%ROOT%\scripts\download_models.py" || exit /b 1

echo ==^> Demo assets
if not exist demo\pair\demo.vault .venv\Scripts\python "%ROOT%\scripts\make_demo_assets.py"

echo ==^> Frontend
cd /d "%ROOT%\app\frontend"
if not exist .env.local copy .env.example .env.local >nul
call npm install --no-audit --no-fund || exit /b 1
call npm run build || exit /b 1
echo.
echo Setup complete. Start the demo with: scripts\run.bat
