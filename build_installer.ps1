# ==============================================================================
# TermCoder Installer Builder
# Packages the latest code changes and compiles TermCoder-Setup.exe via Inno Setup.
# Whenever you modify code in TermCoder, re-run this script to build an updated installer!
# ==============================================================================

$ErrorActionPreference = "Stop"

$ProjectRoot = $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "       TermCoder Setup Builder (Inno Setup)       " -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Locate Inno Setup Compiler (iscc.exe)
Write-Host "[1/4] Locating Inno Setup Compiler (iscc.exe)..." -ForegroundColor Yellow
$isccCandidates = @(
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\iscc.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 7\iscc.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\iscc.exe",
    "${env:ProgramFiles}\Inno Setup 6\iscc.exe"
)

$isccPath = $null
foreach ($candidate in $isccCandidates) {
    if (Test-Path $candidate) {
        $isccPath = $candidate
        break
    }
}

if (-not $isccPath) {
    $cmd = Get-Command iscc.exe -ErrorAction SilentlyContinue
    if ($cmd) {
        $isccPath = $cmd.Source
    }
}

if (-not $isccPath) {
    Write-Host "Inno Setup compiler not found in standard paths. Attempting winget install..." -ForegroundColor Cyan
    try {
        winget install JRSoftware.InnoSetup --silent --accept-source-agreements --accept-package-agreements
        foreach ($candidate in $isccCandidates) {
            if (Test-Path $candidate) {
                $isccPath = $candidate
                break
            }
        }
    } catch {
        Write-Host "Warning: winget installation failed or required manual confirmation." -ForegroundColor Yellow
    }
}

if (-not $isccPath -or -not (Test-Path $isccPath)) {
    Write-Host "[ERROR] Could not find Inno Setup compiler (iscc.exe)." -ForegroundColor Red
    Write-Host "Please install Inno Setup 6 from https://jrsoftware.org/isdl.php" -ForegroundColor Yellow
    exit 1
}

Write-Host "Using Inno Setup: $isccPath" -ForegroundColor Green

# 2. Stage files in dist\TermCoder
Write-Host "[2/4] Staging application files to dist\TermCoder..." -ForegroundColor Yellow
$distDir = Join-Path $ProjectRoot "dist\TermCoder"
if (Test-Path $distDir) {
    Remove-Item -Recurse -Force $distDir
}
New-Item -ItemType Directory -Path $distDir -Force | Out-Null

# Copy termcoder package
$termcoderSrc = Join-Path $ProjectRoot "termcoder"
$termcoderDest = Join-Path $distDir "termcoder"
Copy-Item -Path $termcoderSrc -Destination $termcoderDest -Recurse -Force

# Clean __pycache__ from dist
Get-ChildItem -Path $distDir -Filter "__pycache__" -Recurse -Directory | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# Copy bin folder
$binSrc = Join-Path $ProjectRoot "bin"
$binDest = Join-Path $distDir "bin"
Copy-Item -Path $binSrc -Destination $binDest -Recurse -Force

# Copy pyproject.toml & README.md
Copy-Item -Path (Join-Path $ProjectRoot "pyproject.toml") -Destination (Join-Path $distDir "pyproject.toml") -Force
Copy-Item -Path (Join-Path $ProjectRoot "README.md") -Destination (Join-Path $distDir "README.md") -Force

Write-Host "Staged application files successfully." -ForegroundColor Green

# 3. Create Output directory
$outputDir = Join-Path $ProjectRoot "Output"
if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}

# 4. Compile Inno Setup Script
Write-Host "[3/4] Compiling installer with Inno Setup..." -ForegroundColor Yellow
$issPath = Join-Path $ProjectRoot "installer.iss"
& $isccPath $issPath

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Inno Setup compilation failed with exit code $LASTEXITCODE" -ForegroundColor Red
    exit 1
}

# 5. Summary
$setupExe = Join-Path $outputDir "TermCoder-Setup.exe"
if (Test-Path $setupExe) {
    # Also copy to project root for instant access
    $rootSetupExe = Join-Path $ProjectRoot "TermCoder-Setup.exe"
    Copy-Item -Path $setupExe -Destination $rootSetupExe -Force

    $fileInfo = Get-Item $setupExe
    $sizeMB = [math]::Round($fileInfo.Length / 1MB, 2)
    Write-Host ""
    Write-Host "==================================================" -ForegroundColor Green
    Write-Host "       TermCoder Installer Built Successfully!     " -ForegroundColor Green
    Write-Host "==================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Installer Executable:" -ForegroundColor Cyan
    Write-Host "  $rootSetupExe ($sizeMB MB)" -ForegroundColor White
    Write-Host "  $setupExe ($sizeMB MB)" -ForegroundColor White
    Write-Host ""
    Write-Host "How to use:" -ForegroundColor Cyan
    Write-Host "  1. Double-click 'TermCoder-Setup.exe' in the project folder to install/update." -ForegroundColor White
    Write-Host "  2. Launch via Desktop / Start Menu shortcut (opens directly in Windows Terminal)." -ForegroundColor White
    Write-Host "  3. Or run 'ai' or 'termcoder' in any existing terminal." -ForegroundColor White
    Write-Host "  4. Or double-click 'TermCoder.bat' right here to run directly!" -ForegroundColor White
    Write-Host "  5. Whenever you change code, re-run .\build_installer.ps1 (or double-click build_installer.bat) to update!" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host "[ERROR] Output executable was not found at $setupExe" -ForegroundColor Red
    exit 1
}
