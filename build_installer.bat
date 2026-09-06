@echo off
REM Double-clickable builder for TermCoder Inno Setup Installer
title TermCoder Installer Builder
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_installer.ps1"
pause
