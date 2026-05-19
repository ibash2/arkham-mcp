#Requires -Version 5.1
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoUrl    = "https://github.com/ibash2/arkham-mcp"
$InstallDir = Join-Path $env:LOCALAPPDATA "arkham-mcp"

function Info($msg) { Write-Host "▶ $msg" -ForegroundColor Cyan }
function Ok($msg)   { Write-Host "✓ $msg" -ForegroundColor Green }
function Err($msg)  { Write-Host "✗ $msg" -ForegroundColor Red }

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Err "git is required but not installed."
    Write-Host "  Install it from https://git-scm.com and re-run this script."
    exit 1
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Info "uv not found — installing..."
    irm https://astral.sh/uv/install.ps1 | iex
    $env:PATH = "$env:USERPROFILE\.local\bin;$env:PATH"
    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Err "uv install succeeded but it is not in PATH."
        Write-Host "  Open a new PowerShell window and re-run this script."
        exit 1
    }
    Ok "uv installed"
}

if (Test-Path (Join-Path $InstallDir ".git")) {
    Info "Updating existing install at $InstallDir..."
    git -C $InstallDir pull --ff-only
} else {
    Info "Cloning arkham-mcp into $InstallDir..."
    git clone $RepoUrl $InstallDir
}
Ok "Repository ready"

Info "Installing dependencies..."
uv sync --project $InstallDir --quiet
Ok "Dependencies installed"

Info "Launching installer..."
uv run --project $InstallDir python "$InstallDir\installer\install.py"
