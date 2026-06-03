$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

# ── Create .env on first run ─────────────────────────────────────
$envFile = Join-Path $root ".env"
if (-not (Test-Path $envFile)) {
    Write-Host ""
    Write-Host "  Doc Translator - First Time Setup" -ForegroundColor Cyan
    Write-Host "  -----------------------------------" -ForegroundColor Cyan
    Write-Host ""
    $pw = Read-Host "  Set team password"
    $chars = (65..90) + (97..122) + (48..57)
    $secret = -join ($chars | Get-Random -Count 32 | ForEach-Object { [char]$_ })
    # Use UTF8 without BOM (PowerShell 5.1 Set-Content adds BOM with -Encoding utf8)
    $envContent = "SHARED_PASSWORD=$pw`nSECRET_KEY=$secret"
    [System.IO.File]::WriteAllText($envFile, $envContent, [System.Text.UTF8Encoding]::new($false))
    Write-Host ""
    Write-Host "  Created .env file." -ForegroundColor Green
}

# ── Install python-dotenv if missing ────────────────────────────
$pip = Join-Path $root "backend\.venv\Scripts\pip.exe"
$dotenvCheck = & $pip show python-dotenv 2>&1
if ($dotenvCheck -notmatch "Name: python-dotenv") {
    Write-Host "  Installing python-dotenv..." -ForegroundColor Yellow
    & $pip install "python-dotenv==1.0.1" --quiet
}

# ── Start backend (new window) ───────────────────────────────────
$backendCmd = "Set-Location '$root\backend'; .\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd

# ── Start frontend (new window) ──────────────────────────────────
$frontendCmd = "Set-Location '$root\frontend'; npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

# ── Open browser ─────────────────────────────────────────────────
Write-Host ""
Write-Host "  Starting servers..." -ForegroundColor Cyan
Start-Sleep -Seconds 3
Start-Process "http://localhost:5173"

Write-Host "  Opened browser -> http://localhost:5173" -ForegroundColor Green
Write-Host "  (Close the server windows to stop)" -ForegroundColor Gray
Write-Host ""
