@echo off
REM Obsidian AI Environment Setup Script (Windows CMD)
REM ===================================================
REM This script sets up a Python virtual environment for the Obsidian AI project.

echo ==========================================
echo Obsidian AI Environment Setup
echo ==========================================
echo.

REM Find Python
set PYTHON_CMD=
for %%p in (python3.12 python3.11 python3 python) do (
    where %%p >nul 2>&1
    if not errorlevel 1 (
        set PYTHON_CMD=%%p
        goto :found_python
    )
)

echo Error: Python 3.10+ not found. Please install Python 3.11 or newer.
echo Download from: https://www.python.org/downloads/
exit /b 1

:found_python
echo Python command: %PYTHON_CMD%

REM Check version
for /f "tokens=*" %%v in ('%PYTHON_CMD% -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"') do set PYTHON_VERSION=%%v
echo Python version: %PYTHON_VERSION%
echo.

REM Remove existing .venv if present
if exist .venv (
    echo Existing .venv found. Removing...
    rmdir /s /q .venv
)

REM Create virtual environment
echo Creating virtual environment...
%PYTHON_CMD% -m venv .venv

REM Activate virtual environment
echo Activating virtual environment...
call .venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
pip install --upgrade pip

REM Install requirements
echo.
echo Installing requirements...
pip install -r requirements.txt

REM Install ai_core from sibling directory
if exist ..\ai_engine (
    echo.
    echo Found ai_engine at ..\ai_engine
    echo Installing ai_core as editable package...
    pip install -e ..\ai_engine
) else (
    echo.
    echo WARNING: ai_engine not found at ..\ai_engine
    echo You'll need to install ai_core manually:
    echo   pip install -e C:\path\to\ai_engine
)

REM Optional: Install notion_markdown_converter
if exist ..\notion_md_converter (
    echo.
    echo Found notion_md_converter at ..\notion_md_converter
    echo Installing notion_markdown_converter as editable package...
    pip install -e ..\notion_md_converter
) else (
    echo.
    echo Note: notion_md_converter not found (optional, for Notion integration)
)

echo.
echo ==========================================
echo Setup Complete!
echo ==========================================
echo.
echo To activate the virtual environment:
echo   .venv\Scripts\activate.bat
echo.
echo Before running, create a .env file with your API keys:
echo   CLAUDE_API_KEY=...
echo   OPENAI_API_KEY=...
echo   DISCORD_BOT_TOKEN=...
echo   etc.
echo.
echo To run Obsidian AI:
echo   python obsidian_ai.py

