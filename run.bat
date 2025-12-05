@echo off
REM Obsidian AI Runner Script (Windows CMD)
REM Activates the virtual environment and runs the application

cd /d "%~dp0"

REM Check if virtual environment exists
if not exist .venv (
    echo Error: Virtual environment not found.
    echo Please run setup_env.bat first to set up the environment.
    exit /b 1
)

REM Activate and run
call .venv\Scripts\activate.bat
python obsidian_ai.py %*


