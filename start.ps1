# MetricWatch - one-command deploy (Windows)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host "MetricWatch - Quick Start" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "[X] Docker not found. Install Docker Desktop first." -ForegroundColor Red
    exit 1
}
Write-Host "[OK] $(docker --version)" -ForegroundColor Green

$compose = "docker compose"
$composeCheck = & docker compose version 2>&1
if ($LASTEXITCODE -ne 0) {
    if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
        $compose = "docker-compose"
    } else {
        Write-Host "[X] Docker Compose not found." -ForegroundColor Red
        exit 1
    }
}
Write-Host "[OK] Docker Compose found" -ForegroundColor Green
Write-Host ""

if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "[OK] Created .env from .env.example" -ForegroundColor Green
    } else {
        Write-Host "[X] Missing .env.example" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "[OK] Using existing .env" -ForegroundColor Green
}
Write-Host ""

$sentimentMode = "keyword"
if (Test-Path ".env") {
    $match = Select-String -Path ".env" -Pattern "^SENTIMENT_MODE=(.+)$" | Select-Object -First 1
    if ($match) { $sentimentMode = $match.Matches.Groups[1].Value.Trim() }
}
if ($sentimentMode -eq "transformers") {
    Write-Host "SENTIMENT_MODE=transformers - first build downloads ~2GB (PyTorch + CUDA libs). This can take 15-30 min." -ForegroundColor Yellow
    Write-Host "For a fast start, set SENTIMENT_MODE=keyword in .env and re-run." -ForegroundColor Yellow
} else {
    Write-Host "SENTIMENT_MODE=keyword - lightweight build (no ML libraries)." -ForegroundColor Green
}
Write-Host "Starting all services..." -ForegroundColor Yellow
Invoke-Expression "$compose up -d --build"
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[X] docker compose failed. Check output above or run: $compose logs" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Waiting for core services..." -ForegroundColor Yellow
Start-Sleep -Seconds 15
Invoke-Expression "$compose ps"

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "MetricWatch is running!" -ForegroundColor Green
Write-Host ""
Write-Host "  Dashboard:   http://localhost:3000"
Write-Host "  API:         http://localhost:8000"
Write-Host "  Grafana:     http://localhost:3001  (admin / admin)"
Write-Host "  Prometheus:  http://localhost:9090"
Write-Host ""
Write-Host "  Seed data:   .\scripts\seed.ps1"
Write-Host "  CLI:         .\cli\metricwatch.ps1 status"
Write-Host "  Logs:        $compose logs -f"
Write-Host "  Stop:        $compose down"
Write-Host "================================" -ForegroundColor Cyan
