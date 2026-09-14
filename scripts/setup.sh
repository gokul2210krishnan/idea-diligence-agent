#!/usr/bin/env bash
# =============================================================================
# Idea Diligence Agent — Linux & macOS Onboarding Setup Script
# =============================================================================

set -e

echo "============================================================"
echo "   Idea Diligence Agent — Developer Setup"
echo "============================================================"

# 1. Check Python
echo -e "\n[1/5] Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed or not in PATH."
    exit 1
fi
python3 --version

# 2. Virtual Environment
echo -e "\n[2/5] Setting up virtual environment (.venv)..."
if [ ! -d ".venv" ]; then
    echo "Creating new virtual environment in .venv..."
    python3 -m venv .venv
    echo "Virtual environment created."
else
    echo "Virtual environment .venv already exists."
fi

source .venv/bin/activate

# 3. Install Dependencies
echo -e "\n[3/5] Installing dependencies from requirements.txt..."
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
echo "Dependencies installed."

# 4. Configure .env
echo -e "\n[4/5] Checking environment configuration (.env)..."
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "Created .env from .env.example."
        echo "Please edit .env to add your Gemini API key or AWS Bedrock credentials."
    fi
else
    echo ".env already exists."
fi

# 5. Run Test Suite
echo -e "\n[5/5] Running test suite to verify setup..."
python -m pytest -q

echo "============================================================"
echo "   Setup complete! All 54 tests passed."
echo "============================================================"
echo -e "\nTo activate your environment in your shell:"
echo "   source .venv/bin/activate"
echo -e "\nTo launch the Web Workspace:"
echo "   python -m src.main --web"
echo -e "\nTo run the instant CLI demo:"
echo "   python -m src.main --demo"
echo ""
