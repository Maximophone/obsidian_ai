# Obsidian AI Runner Script (Windows PowerShell)
# Activates the virtual environment and runs the application

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Check if virtual environment exists
if (-not (Test-Path ".venv")) {
    Write-Host "Error: Virtual environment not found." -ForegroundColor Red
    Write-Host "Please run .\setup_env.ps1 first to set up the environment."
    exit 1
}

# Activate and run
& .\.venv\Scripts\Activate.ps1
python obsidian_ai.py $args

