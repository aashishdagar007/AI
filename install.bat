@echo off
REM One-click double-clickable installer for TermCoder on Windows
title TermCoder Installer
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
pause
