#!/bin/bash
# PlanProof - Quick Setup Script for New Developer (Linux/Mac)
# Run this after cloning the repository

echo "================================"
echo "PlanProof - Developer Setup"
echo "================================"
echo ""

# Check if Python is installed
echo "[1/5] Checking Python installation..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo "✓ Found: $PYTHON_VERSION"
else
    echo "✗ Python not found! Please install Python 3.11+ first."
    exit 1
fi

# Create virtual environment
echo ""
echo "[2/5] Creating virtual environment..."
if [ -d ".venv" ]; then
    echo "✓ Virtual environment already exists"
else
    python3 -m venv .venv
    echo "✓ Created .venv"
fi

# Activate virtual environment
echo ""
echo "[3/5] Activating virtual environment..."
source .venv/bin/activate
echo "✓ Activated"

# Install dependencies
echo ""
echo "[4/5] Installing Python packages..."
echo "    This may take a few minutes..."
pip install -r requirements-dev.txt --quiet
echo "✓ Packages installed"

# Setup configuration files
echo ""
echo "[5/5] Setting up configuration files..."

# Copy .env.example to .env if not exists
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✓ Created .env from template"
        echo "  ⚠ IMPORTANT: Edit .env and add your credentials!"
    else
        echo "✗ .env.example not found"
    fi
else
    echo "✓ .env already exists"
fi

# Copy settings.example.json to settings.json if not exists
if [ ! -f ".vscode/settings.json" ]; then
    if [ -f ".vscode/settings.example.json" ]; then
        cp .vscode/settings.example.json .vscode/settings.json
        echo "✓ Created .vscode/settings.json from template"
        echo "  ⚠ IMPORTANT: Edit .vscode/settings.json and add database password!"
    else
        echo "✗ .vscode/settings.example.json not found"
    fi
else
    echo "✓ .vscode/settings.json already exists"
fi

# Summary
echo ""
echo "================================"
echo "Setup Complete! 🎉"
echo "================================"
echo ""
echo "Next Steps:"
echo "1. Edit .env with your Azure credentials"
echo "2. Edit .vscode/settings.json with database password"
echo "3. Install VS Code extensions (see docs/VSCODE_SETUP.md)"
echo "4. Run the application: python run_ui.py"
echo ""
echo "Documentation: docs/VSCODE_SETUP.md"
echo ""
