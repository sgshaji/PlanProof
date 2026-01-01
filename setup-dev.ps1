# PlanProof - Quick Setup Script for New Developer
# Run this after cloning the repository

Write-Host "================================" -ForegroundColor Cyan
Write-Host "PlanProof - Developer Setup" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Check if Python is installed
Write-Host "[1/5] Checking Python installation..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Python not found! Please install Python 3.11+ first." -ForegroundColor Red
    exit 1
}

# Create virtual environment
Write-Host ""
Write-Host "[2/5] Creating virtual environment..." -ForegroundColor Yellow
if (Test-Path ".venv") {
    Write-Host "✓ Virtual environment already exists" -ForegroundColor Green
} else {
    python -m venv .venv
    Write-Host "✓ Created .venv" -ForegroundColor Green
}

# Activate virtual environment
Write-Host ""
Write-Host "[3/5] Activating virtual environment..." -ForegroundColor Yellow
& .\.venv\Scripts\Activate.ps1
Write-Host "✓ Activated" -ForegroundColor Green

# Install dependencies
Write-Host ""
Write-Host "[4/5] Installing Python packages..." -ForegroundColor Yellow
Write-Host "    This may take a few minutes..." -ForegroundColor Gray
pip install -r requirements-dev.txt --quiet
Write-Host "✓ Packages installed" -ForegroundColor Green

# Setup configuration files
Write-Host ""
Write-Host "[5/5] Setting up configuration files..." -ForegroundColor Yellow

# Copy .env.example to .env if not exists
if (!(Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item .env.example .env
        Write-Host "✓ Created .env from template" -ForegroundColor Green
        Write-Host "  ⚠ IMPORTANT: Edit .env and add your credentials!" -ForegroundColor Yellow
    } else {
        Write-Host "✗ .env.example not found" -ForegroundColor Red
    }
} else {
    Write-Host "✓ .env already exists" -ForegroundColor Green
}

# Copy settings.example.json to settings.json if not exists
if (!(Test-Path ".vscode\settings.json")) {
    if (Test-Path ".vscode\settings.example.json") {
        Copy-Item .vscode\settings.example.json .vscode\settings.json
        Write-Host "✓ Created .vscode\settings.json from template" -ForegroundColor Green
        Write-Host "  ⚠ IMPORTANT: Edit .vscode\settings.json and add database password!" -ForegroundColor Yellow
    } else {
        Write-Host "✗ .vscode\settings.example.json not found" -ForegroundColor Red
    }
} else {
    Write-Host "✓ .vscode\settings.json already exists" -ForegroundColor Green
}

# Summary
Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Setup Complete! 🎉" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Edit .env with your Azure credentials" -ForegroundColor White
Write-Host "2. Edit .vscode\settings.json with database password" -ForegroundColor White
Write-Host "3. Install VS Code extensions (see docs\VSCODE_SETUP.md)" -ForegroundColor White
Write-Host "4. Run the application: python run_ui.py" -ForegroundColor White
Write-Host ""
Write-Host "Documentation: docs\VSCODE_SETUP.md" -ForegroundColor Cyan
Write-Host ""
