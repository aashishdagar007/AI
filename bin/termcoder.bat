@echo off
setlocal
title TermCoder AI

REM 1. Check for bundled virtual environment first
if exist "%~dp0..\venv\Scripts\python.exe" (
    "%~dp0..\venv\Scripts\python.exe" -m termcoder.cli %*
    goto :EOF
)

REM 2. Ensure the TermCoder directory is in PYTHONPATH so imports work seamlessly
set "APP_DIR=%~dp0.."
if defined PYTHONPATH (
    set "PYTHONPATH=%APP_DIR%;%PYTHONPATH%"
) else (
    set "PYTHONPATH=%APP_DIR%"
)

REM 3. Resolve Python executable
set "PY_EXE="
where python.exe >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set "PY_EXE=python.exe"
) else (
    where py.exe >nul 2>&1
    if %ERRORLEVEL% equ 0 (
        set "PY_EXE=py.exe -3"
    )
)

if "%PY_EXE%"=="" (
    echo.
    echo =======================================================
    echo [TermCoder ERROR] Python 3.10+ was not found in PATH.
    echo Please install Python from https://www.python.org/downloads/
    echo and check "Add Python to PATH" during installation.
    echo =======================================================
    echo.
    pause
    goto :EOF
)

REM 4. Quick dependency check (rich, prompt_toolkit, requests)
%PY_EXE% -c "import rich, prompt_toolkit, requests" >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [TermCoder] First-time initialization: Installing required dependencies...
    %PY_EXE% -m pip install -e "%APP_DIR%"
)

REM 5. Launch TermCoder CLI
%PY_EXE% -m termcoder.cli %*
