@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
  echo Tag Signal needs Python 3.10 or newer.
  pause
  exit /b 1
)

if not exist .venv py -3 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip --disable-pip-version-check install --prefer-binary -r requirements.txt
set ARROW_DEFAULT_MEMORY_POOL=system
if not defined TAGSIGNAL_PORT set TAGSIGNAL_PORT=8588
if not defined TAGSIGNAL_MAX_UPLOAD_MB set TAGSIGNAL_MAX_UPLOAD_MB=10000
python -m streamlit run app.py --server.headless=true --server.address=127.0.0.1 --server.port=%TAGSIGNAL_PORT% --server.maxUploadSize=%TAGSIGNAL_MAX_UPLOAD_MB% --browser.gatherUsageStats=false

