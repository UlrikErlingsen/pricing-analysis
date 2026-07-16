@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
  echo PriceSignal needs Python 3.10 or newer.
  pause
  exit /b 1
)

if not exist .venv py -3 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip --disable-pip-version-check install --prefer-binary -r requirements.txt
set ARROW_DEFAULT_MEMORY_POOL=system
python -m streamlit run app.py --server.headless=true --server.address=127.0.0.1 --server.port=8588 --browser.gatherUsageStats=false

