# MetricWatch CLI (Windows)
param(
    [Parameter(Position = 0)]
    [string]$Command = "help",
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$compose = "docker compose"
try { docker compose version | Out-Null } catch { $compose = "docker-compose" }

function Ensure-Env {
    if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }
}

switch ($Command) {
    "start" { Ensure-Env; Invoke-Expression "$compose up -d --build" }
    "stop" { Invoke-Expression "$compose down" }
    "restart" { Invoke-Expression "$compose restart $($Args -join ' ')" }
    "status" { Invoke-Expression "$compose ps" }
    "logs" { Invoke-Expression "$compose logs -f $($Args -join ' ')" }
    "scale" {
        if ($Args.Count -lt 2) { Write-Error "Usage: scale <service> <count>"; exit 1 }
        Invoke-Expression "$compose up -d --scale $($Args[0])=$($Args[1]) --no-recreate"
    }
    "topics" { Invoke-Expression "$compose exec kafka kafka-topics --list --bootstrap-server kafka:9092" }
    "health" { Invoke-RestMethod "http://localhost:8000/health" | ConvertTo-Json }
    default {
        Write-Host @"
MetricWatch CLI

Commands: start | stop | restart | status | logs | scale | topics | health
"@
    }
}
