@echo off
setlocal
cd /d "%~dp0"

set "PYTHON_CMD="
py -3.14 --version >nul 2>&1
if not errorlevel 1 set "PYTHON_CMD=py -3.14"
if not defined PYTHON_CMD (
  py -3.13 --version >nul 2>&1
  if not errorlevel 1 set "PYTHON_CMD=py -3.13"
)
if not defined PYTHON_CMD (
  py -3.12 --version >nul 2>&1
  if not errorlevel 1 set "PYTHON_CMD=py -3.12"
)
if not defined PYTHON_CMD (
  py -3.11 --version >nul 2>&1
  if not errorlevel 1 set "PYTHON_CMD=py -3.11"
)
if not defined PYTHON_CMD (
  py -3.10 --version >nul 2>&1
  if not errorlevel 1 set "PYTHON_CMD=py -3.10"
)
if not defined PYTHON_CMD (
  python -c "import sys; raise SystemExit(0 if (3,10) <= sys.version_info[:2] <= (3,14) else 1)" >nul 2>&1
  if not errorlevel 1 set "PYTHON_CMD=python"
)

if not defined PYTHON_CMD (
  echo OmniFetch needs Python 3.10 through 3.14. Python 3.15 cannot install its Brotli package yet.
  echo Install the 64-bit Python 3.14 release, then run this file again:
  echo https://www.python.org/downloads/release/python-3148/
  pause
  exit /b 1
)

if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -c "import sys; raise SystemExit(0 if (3,10) <= sys.version_info[:2] <= (3,14) else 1)" >nul 2>&1
  if errorlevel 1 (
    echo Replacing the old app environment because it uses an unsupported Python version...
    rmdir /s /q ".venv"
  )
)

if not exist ".venv\Scripts\python.exe" (
  %PYTHON_CMD% -m venv ".venv"
  if errorlevel 1 (
    echo Could not create the Python environment.
    pause
    exit /b 1
  )
)

".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
  echo Could not update pip. Check your internet connection and try again.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo Could not install the Python packages. Check your internet connection and confirm Python 3.10 through 3.14 is installed.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" app.py
pause
