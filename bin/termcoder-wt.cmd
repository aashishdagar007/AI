@echo off
setlocal
REM =======================================================
REM TermCoder Direct Terminal Launcher
REM Opens TermCoder directly inside Windows Terminal (wt.exe)
REM with automatic fallback to standard console if wt is missing.
REM =======================================================

set "SCRIPT_DIR=%~dp0"

REM 1. Locate wt.exe (Windows Terminal)
set "WT_EXE="
where wt.exe >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set "WT_EXE=wt.exe"
) else if exist "%LOCALAPPDATA%\Microsoft\WindowsApps\wt.exe" (
    set "WT_EXE=%LOCALAPPDATA%\Microsoft\WindowsApps\wt.exe"
)

REM 2. Determine target working directory
set "WORK_DIR=%CD%"
if "%~1"=="" (
    if exist "%USERPROFILE%" (
        set "WORK_DIR=%USERPROFILE%"
    )
)

REM 3. Launch in Windows Terminal if available, else fallback to standard cmd
if defined WT_EXE (
    if "%~1"=="" (
        REM Interactive mode in Windows Terminal
        "%WT_EXE%" --title "TermCoder AI" -d "%WORK_DIR%" cmd.exe /k ""%SCRIPT_DIR%termcoder.bat""
    ) else (
        REM Command execution mode
        "%WT_EXE%" --title "TermCoder AI" -d "%WORK_DIR%" cmd.exe /c ""%SCRIPT_DIR%termcoder.bat" %* & pause"
    )
) else (
    if "%~1"=="" (
        start "TermCoder AI" /D "%WORK_DIR%" cmd.exe /k ""%SCRIPT_DIR%termcoder.bat""
    ) else (
        start "TermCoder AI" /D "%WORK_DIR%" cmd.exe /c ""%SCRIPT_DIR%termcoder.bat" %* & pause"
    )
)
