# Obsidian AI Environment Setup Script (Windows PowerShell)
# ==========================================================
# This script sets up a Python virtual environment for the Obsidian AI project.
# Run with: .\setup_env.ps1

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Obsidian AI Environment Setup" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Find Python
$pythonCmd = $null
foreach ($cmd in @("python3.12", "python3.11", "python3", "python")) {
    try {
        $version = & $cmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        if ($version) {
            $major, $minor = $version -split '\.'
            if ([int]$major -ge 3 -and [int]$minor -ge 10) {
                $pythonCmd = $cmd
                break
            }
        }
    } catch {}
}

if (-not $pythonCmd) {
    Write-Host "Error: Python 3.10+ not found. Please install Python 3.11 or newer." -ForegroundColor Red
    Write-Host "Download from: https://www.python.org/downloads/"
    exit 1
}

Write-Host "Python command: $pythonCmd"
$pythonVersion = & $pythonCmd -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
Write-Host "Python version: $pythonVersion"
Write-Host ""

# Remove existing .venv if present
if (Test-Path ".venv") {
    Write-Host "Existing .venv found. Removing..."
    Remove-Item -Recurse -Force ".venv"
}

# Create virtual environment
Write-Host "Creating virtual environment..."
& $pythonCmd -m venv .venv

# Activate virtual environment
Write-Host "Activating virtual environment..."
& .\.venv\Scripts\Activate.ps1

# Upgrade pip
Write-Host "Upgrading pip..."
pip install --upgrade pip

# Install requirements
Write-Host ""
Write-Host "Installing requirements..."
pip install -r requirements.txt

# Install ai_core from sibling directory
$aiEnginePath = "..\ai_engine"
if (Test-Path $aiEnginePath) {
    Write-Host ""
    Write-Host "Found ai_engine at $aiEnginePath"
    Write-Host "Installing ai_core as editable package..."
    pip install -e $aiEnginePath
} else {
    Write-Host ""
    Write-Host "WARNING: ai_engine not found at $aiEnginePath" -ForegroundColor Yellow
    Write-Host "You'll need to install ai_core manually:"
    Write-Host "  pip install -e C:\path\to\ai_engine"
}

# Optional: Install notion_markdown_converter
$notionConverterPath = "..\notion_md_converter"
if (Test-Path $notionConverterPath) {
    Write-Host ""
    Write-Host "Found notion_md_converter at $notionConverterPath"
    Write-Host "Installing notion_markdown_converter as editable package..."
    pip install -e $notionConverterPath
} else {
    Write-Host ""
    Write-Host "Note: notion_md_converter not found (optional, for Notion integration)" -ForegroundColor Gray
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "To activate the virtual environment:"
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host ""
Write-Host "Before running, create a .env file with your API keys:"
Write-Host "  CLAUDE_API_KEY=..."
Write-Host "  OPENAI_API_KEY=..."
Write-Host "  DISCORD_BOT_TOKEN=..."
Write-Host "  etc."
Write-Host ""
Write-Host "To run Obsidian AI:"
Write-Host "  python obsidian_ai.py"

