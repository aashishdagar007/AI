@echo off
setlocal
REM =======================================================
REM TermCoder Direct Terminal Launcher
REM Opens TermCoder directly inside Windows Terminal (wt.exe)
REM in a dedicated new window, with automatic fallback.
REM =======================================================

set "SCRIPT_DIR=%~dp0"
set "WORK_DIR=%CD%"

REM Locate wt.exe (Windows Terminal)
set "WT_EXE="
where wt.exe >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set "WT_EXE=wt.exe"
) else if exist "%LOCALAPPDATA%\Microsoft\WindowsApps\wt.exe" (
    set "WT_EXE=%LOCALAPPDATA%\Microsoft\WindowsApps\wt.exe"
)

REM If wt.exe is available, launch inside Windows Terminal in a new window (-w new)
if defined WT_EXE (
    if "%~1"=="" (
        start "" "%WT_EXE%" -w new -d "%WORK_DIR%" cmd.exe /k "%SCRIPT_DIR%termcoder.bat"
        if %ERRORLEVEL% equ 0 goto :EOF
    ) else (
        start "" "%WT_EXE%" -w new -d "%WORK_DIR%" cmd.exe /c "%SCRIPT_DIR%termcoder.bat %* & pause"
        if %ERRORLEVEL% equ 0 goto :EOF
    )
)

REM Fallback: Standard Windows Command Prompt
if "%~1"=="" (
    start "TermCoder AI" /D "%WORK_DIR%" cmd.exe /k "%SCRIPT_DIR%termcoder.bat"
) else (
    start "TermCoder AI" /D "%WORK_DIR%" cmd.exe /c "%SCRIPT_DIR%termcoder.bat %* & pause"
)
