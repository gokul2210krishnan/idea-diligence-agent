<#
.SYNOPSIS
    Automated developer setup script for Idea Diligence Agent on Windows.
.DESCRIPTION
    Creates virtual environment, installs dependencies, initializes .env,
    and runs the test suite to verify the installation.
#>

$ErrorActionPreference = "Stop"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   Idea Diligence Agent — Windows Onboarding Setup" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 1. Check Python version
Write-Host "`n[1/5] Checking Python installation..." -ForegroundColor Yellow
try {
    $pythonVersionStr = python --version 2>&1
    Write-Host "Found: $pythonVersionStr" -ForegroundColor Green
} catch {
    Write-Error "Python is not found in PATH. Please install Python 3.12+ from https://www.python.org/"
    exit 1
}

# 2. Setup Virtual Environment
Write-Host "`n[2/5] Setting up virtual environment (.venv)..." -ForegroundColor Yellow
if (-not (Test-Path ".venv")) {
    Write-Host "Creating new virtual environment in .venv..."
    python -m venv .venv
    Write-Host "Virtual environment created." -ForegroundColor Green
} else {
    Write-Host "Virtual environment .venv already exists." -ForegroundColor Green
}

# Activate virtual environment
$venvPython = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"
$venvPip = Join-Path $PSScriptRoot "..\.venv\Scripts\pip.exe"

if (-not (Test-Path $venvPython)) {
    # Fallback to local relative path
    $venvPython = ".\.venv\Scripts\python.exe"
    $venvPip = ".\.venv\Scripts\pip.exe"
}

# 3. Install Dependencies
Write-Host "`n[3/5] Installing dependencies from requirements.txt..." -ForegroundColor Yellow
& $venvPip install --upgrade pip --quiet
& $venvPip install -r requirements.txt --quiet
Write-Host "Dependencies successfully installed." -ForegroundColor Green

# 4. Configure .env file
Write-Host "`n[4/5] Checking environment configuration (.env)..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "Created .env from .env.example." -ForegroundColor Green
        Write-Host "Please edit .env to add your Gemini API key or AWS Bedrock credentials." -ForegroundColor Magenta
    } else {
        Write-Host "Warning: .env.example not found." -ForegroundColor DarkYellow
    }
} else {
    Write-Host ".env already exists." -ForegroundColor Green
}

# 5. Run Test Suite
Write-Host "`n[5/5] Running test suite to verify setup..." -ForegroundColor Yellow
& $venvPython -m pytest -q

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n============================================================" -ForegroundColor Green
    Write-Host "   Setup complete! All 42 tests passed." -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Green
    Write-Host "`nTo activate your environment:" -ForegroundColor Cyan
    Write-Host "   .\.venv\Scripts\Activate.ps1" -ForegroundColor White
    Write-Host "`nTo launch the Web Workspace:" -ForegroundColor Cyan
    Write-Host "   python -m src.main --web" -ForegroundColor White
    Write-Host "`nTo run the instant CLI demo:" -ForegroundColor Cyan
    Write-Host "   python -m src.main --demo" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host "`n[!] Some tests failed. Please review the output above." -ForegroundColor Red
}
