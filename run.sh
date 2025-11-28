#!/bin/bash
# Obsidian AI Runner Script
# Activates the virtual environment and runs the application

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Error: Virtual environment not found."
    echo "Please run ./setup_env.sh first to set up the environment."
    exit 1
fi

# Activate and run
source .venv/bin/activate
python obsidian_ai.py "$@"

