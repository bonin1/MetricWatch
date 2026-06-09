# MetricWatch smoke test - quick pass/fail checks
$ErrorActionPreference = "Continue"
$pass = 0
$fail = 0

function Test-Check($name, $scriptBlock) {
    try {
        $result = & $scriptBlock
        if ($result) {
            Write-Host "[PASS] $name" -ForegroundColor Green
            $script:pass++
        } else {
            Write-Host "[FAIL] $name" -ForegroundColor Red
            $script:fail++
        }
    } catch {
        Write-Host "[FAIL] $name - $($_.Exception.Message)" -ForegroundColor Red
        $script:fail++
    }
}

Write-Host ""
Write-Host "MetricWatch Smoke Test"
Write-Host ""

Test-Check "Docker stack running" {
    $ps = docker compose ps --format json 2>$null | ConvertFrom-Json
    ($ps | Where-Object { $_.State -eq "running" }).Count -ge 10
}

Test-Check "API health" {
    (Invoke-RestMethod http://localhost:8000/health -TimeoutSec 5).status -eq "healthy"
}

Test-Check "Metrics in PostgreSQL" {
    $uri = 'http://localhost:8000/api/metrics/history?metric_type=cpu&hours=3'
    (Invoke-RestMethod $uri -TimeoutSec 5).count -gt 0
}

Test-Check "Sentiment in MongoDB" {
    (Invoke-RestMethod 'http://localhost:8000/api/sentiment/recent?limit=5' -TimeoutSec 5).count -gt 0
}

Test-Check "Dashboard reachable" {
    (Invoke-WebRequest http://localhost:3000 -TimeoutSec 5 -UseBasicParsing).StatusCode -eq 200
}

Test-Check "Prometheus reachable" {
    (Invoke-WebRequest http://localhost:9090/-/healthy -TimeoutSec 5 -UseBasicParsing).StatusCode -eq 200
}

Test-Check "Grafana reachable" {
    (Invoke-WebRequest http://localhost:3001/api/health -TimeoutSec 5 -UseBasicParsing).StatusCode -eq 200
}

Test-Check "Prometheus scraping producers" {
    $q = [uri]::EscapeDataString('up{job="metrics-producer"}')
    $r = Invoke-RestMethod "http://localhost:9090/api/v1/query?query=$q" -TimeoutSec 5
    $r.data.result.Count -gt 0 -and $r.data.result[0].value[1] -eq '1'
}

Write-Host ""
Write-Host "Results: $pass passed, $fail failed"
Write-Host ""
if ($fail -gt 0) {
    Write-Host "See docs/TESTING.md for detailed steps."
    exit 1
}
