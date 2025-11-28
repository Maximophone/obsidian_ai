#!/bin/bash
# Obsidian AI Environment Setup Script
# =====================================
# This script sets up a Python virtual environment for the Obsidian AI project.
# Works on macOS and Linux.

set -e

echo "=========================================="
echo "Obsidian AI Environment Setup"
echo "=========================================="
echo

# Detect platform and find Python
if [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORM="macOS"
    # Try to find Python 3.10+ on macOS
    if command -v python3.12 &> /dev/null; then
        PYTHON_CMD="python3.12"
    elif command -v python3.11 &> /dev/null; then
        PYTHON_CMD="python3.11"
    elif command -v /opt/homebrew/bin/python3.12 &> /dev/null; then
        PYTHON_CMD="/opt/homebrew/bin/python3.12"
    elif command -v /opt/homebrew/bin/python3.11 &> /dev/null; then
        PYTHON_CMD="/opt/homebrew/bin/python3.11"
    elif command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    else
        echo "Error: Python 3.10+ not found. Please install it:"
        echo "  brew install python@3.11"
        exit 1
    fi
else
    PLATFORM="Linux"
    if command -v python3.12 &> /dev/null; then
        PYTHON_CMD="python3.12"
    elif command -v python3.11 &> /dev/null; then
        PYTHON_CMD="python3.11"
    else
        PYTHON_CMD="python3"
    fi
fi

echo "Platform: $PLATFORM"
echo "Python command: $PYTHON_CMD"

# Check Python version
PYTHON_VERSION=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "Python version: $PYTHON_VERSION"

MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [[ $MAJOR -lt 3 ]] || [[ $MAJOR -eq 3 && $MINOR -lt 10 ]]; then
    echo "Error: Python 3.10+ is required. Found: $PYTHON_VERSION"
    exit 1
fi

echo

# Create virtual environment
if [ -d ".venv" ]; then
    echo "Existing .venv found. Removing..."
    rm -rf .venv
fi

echo "Creating virtual environment..."
$PYTHON_CMD -m venv .venv

# Activate virtual environment
source .venv/bin/activate

echo "Upgrading pip..."
pip install --upgrade pip

echo
echo "Installing requirements..."
pip install -r requirements.txt

# Install ai_core from sibling directory
AI_ENGINE_PATH="../ai_engine"
if [ -d "$AI_ENGINE_PATH" ]; then
    echo
    echo "Found ai_engine at $AI_ENGINE_PATH"
    echo "Installing ai_core as editable package..."
    pip install -e "$AI_ENGINE_PATH"
else
    echo
    echo "WARNING: ai_engine not found at $AI_ENGINE_PATH"
    echo "You'll need to install ai_core manually:"
    echo "  pip install -e /path/to/ai_engine"
fi

# Optional: Install notion_markdown_converter
NOTION_CONVERTER_PATH="../notion_md_converter"
if [ -d "$NOTION_CONVERTER_PATH" ]; then
    echo
    echo "Found notion_md_converter at $NOTION_CONVERTER_PATH"
    echo "Installing notion_markdown_converter as editable package..."
    pip install -e "$NOTION_CONVERTER_PATH"
else
    echo
    echo "Note: notion_md_converter not found (optional, for Notion integration)"
fi

echo
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo
echo "To activate the virtual environment:"
echo "  source .venv/bin/activate"
echo
echo "Before running, create a .env file with your API keys:"
echo "  CLAUDE_API_KEY=..."
echo "  OPENAI_API_KEY=..."
echo "  DISCORD_BOT_TOKEN=..."
echo "  etc."
echo
echo "To run Obsidian AI:"
echo "  python obsidian_ai.py"
