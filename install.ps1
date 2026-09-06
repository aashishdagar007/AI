# TermCoder Windows Installer (PowerShell)
# Installs TermCoder and configures the global 'ai' and 'termcoder' commands.

$ErrorActionPreference = "Stop"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "       TermCoder Windows Installer                " -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check Python
Write-Host "[1/4] Checking Python environment..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "Error: Python is not found in PATH. Please install Python 3.10+ from python.org and try again." -ForegroundColor Red
    exit 1
}

# 2. Install dependencies and editable package
Write-Host "[2/4] Installing TermCoder and dependencies..." -ForegroundColor Yellow
python -m pip install --upgrade pip
python -m pip install -e .
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Failed to install TermCoder package." -ForegroundColor Red
    exit 1
}
Write-Host "TermCoder package installed successfully." -ForegroundColor Green

# 3. Create global command launchers
Write-Host "[3/4] Creating 'ai' and 'termcoder' global commands..." -ForegroundColor Yellow
$binDir = Join-Path $HOME ".termcoder\bin"
if (-not (Test-Path $binDir)) {
    New-Item -ItemType Directory -Path $binDir -Force | Out-Null
}

$pyExe = (Get-Command python).Source
$aiCmd = @"
@echo off
"$pyExe" -m termcoder.cli %*
"@

Set-Content -Path (Join-Path $binDir "ai.cmd") -Value $aiCmd -Encoding ASCII
Set-Content -Path (Join-Path $binDir "termcoder.cmd") -Value $aiCmd -Encoding ASCII

# 4. Add to User PATH if not already present
Write-Host "[4/4] Ensuring '$binDir' is in User PATH..." -ForegroundColor Yellow
$userPath = [Environment]::GetEnvironmentVariable("Path", [EnvironmentVariableTarget]::User)
if ($userPath -notlike "*$binDir*") {
    $newPath = "$binDir;$userPath"
    [Environment]::SetEnvironmentVariable("Path", $newPath, [EnvironmentVariableTarget]::User)
    $env:Path = "$binDir;$env:Path"
    Write-Host "Added '$binDir' to User PATH." -ForegroundColor Green
} else {
    Write-Host "'$binDir' is already in PATH." -ForegroundColor Green
}

Write-Host ""
Write-Host "==================================================" -ForegroundColor Green
Write-Host "       TermCoder Successfully Installed!          " -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green
Write-Host ""
Write-Host "You can now run:" -ForegroundColor Cyan
Write-Host "  ai                     - Launch interactive assistant" -ForegroundColor White
Write-Host "  termcoder              - Launch interactive assistant" -ForegroundColor White
Write-Host "  ai 'explain my code'   - Run a quick command" -ForegroundColor White
Write-Host ""
Write-Host "Note: In newly opened terminal windows, 'ai' is immediately available!" -ForegroundColor Yellow
Write-Host "Get your free NVIDIA NIM API key at https://build.nvidia.com" -ForegroundColor Cyan
Write-Host "Configure anytime in chat using: /key <your_key>" -ForegroundColor Cyan
Write-Host ""
