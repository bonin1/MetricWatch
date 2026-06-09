# Seed MetricWatch demo data (stack must be running)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$compose = "docker compose"
try { docker compose version | Out-Null } catch { $compose = "docker-compose" }

if (Get-Command docker -ErrorAction SilentlyContinue) {
    Write-Host "Seeding via Docker (recommended)..." -ForegroundColor Cyan
    Invoke-Expression "$compose --profile seed run --rm seed $args"
    exit $LASTEXITCODE
}

Write-Host "Docker not found — falling back to local Python..." -ForegroundColor Yellow
python -m pip install -q -r scripts/requirements.txt
python scripts/seed_data.py --local @args
