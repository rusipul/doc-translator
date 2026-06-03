$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

# ── .env 확인 / 최초 설정 ─────────────────────────────────────────
$envFile = Join-Path $root ".env"
if (-not (Test-Path $envFile)) {
    Write-Host ""
    Write-Host "  Doc Translator - 최초 설정" -ForegroundColor Cyan
    Write-Host "  ──────────────────────────" -ForegroundColor Cyan
    Write-Host ""
    $pw = Read-Host "  팀 비밀번호를 입력하세요"
    $secret = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | ForEach-Object { [char]$_ })
    @"
SHARED_PASSWORD=$pw
SECRET_KEY=$secret
"@ | Set-Content $envFile -Encoding utf8
    Write-Host ""
    Write-Host "  .env 파일이 생성됐습니다." -ForegroundColor Green
}

# ── python-dotenv 설치 확인 ───────────────────────────────────────
$pip = Join-Path $root "backend\.venv\Scripts\pip.exe"
$python = Join-Path $root "backend\.venv\Scripts\python.exe"

$installed = & $pip show python-dotenv 2>&1
if ($installed -notmatch "Name: python-dotenv") {
    Write-Host "  python-dotenv 설치 중..." -ForegroundColor Yellow
    & $pip install "python-dotenv==1.0.1" --quiet
}

# ── 백엔드 실행 (새 창) ───────────────────────────────────────────
$backendCmd = "Set-Location '$root\backend'; & '.\.venv\Scripts\python.exe' -m uvicorn main:app --reload --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd

# ── 프론트엔드 실행 (새 창) ──────────────────────────────────────
$frontendCmd = "Set-Location '$root\frontend'; npm run dev"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd

# ── 브라우저 열기 ────────────────────────────────────────────────
Write-Host ""
Write-Host "  서버를 시작하는 중..." -ForegroundColor Cyan
Start-Sleep -Seconds 3
Start-Process "http://localhost:5173"

Write-Host "  브라우저를 열었습니다 → http://localhost:5173" -ForegroundColor Green
Write-Host "  (창을 닫으면 서버가 종료됩니다)" -ForegroundColor Gray
Write-Host ""
