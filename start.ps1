# MetricWatch Quick Start Script
# This script helps you get started with the MetricWatch system

Write-Host "🚀 MetricWatch - Quick Start" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host ""

# Check Docker
Write-Host "Checking Docker..." -ForegroundColor Yellow
if (Get-Command docker -ErrorAction SilentlyContinue) {
    Write-Host "✓ Docker found" -ForegroundColor Green
    docker --version
} else {
    Write-Host "✗ Docker not found. Please install Docker first." -ForegroundColor Red
    exit 1
}

Write-Host ""

# Check Docker Compose
Write-Host "Checking Docker Compose..." -ForegroundColor Yellow
if (Get-Command docker-compose -ErrorAction SilentlyContinue) {
    Write-Host "✓ Docker Compose found" -ForegroundColor Green
    docker-compose --version
} else {
    Write-Host "✗ Docker Compose not found. Please install Docker Compose first." -ForegroundColor Red
    exit 1
}

Write-Host ""

# Check for existing Kafka
Write-Host "Checking for Kafka container..." -ForegroundColor Yellow
$kafkaContainers = docker ps --filter "name=kafka" --format "{{.Names}}"
if ($kafkaContainers) {
    Write-Host "✓ Found Kafka container(s): $kafkaContainers" -ForegroundColor Green
    Write-Host "  Make sure KAFKA_BOOTSTRAP_SERVERS in .env points to your Kafka instance" -ForegroundColor Yellow
} else {
    Write-Host "⚠ No Kafka container found running" -ForegroundColor Yellow
    Write-Host "  You need a running Kafka instance. See docs/KAFKA_CONNECTION.md" -ForegroundColor Yellow
}

Write-Host ""

# Prompt to continue
$continue = Read-Host "Do you want to start MetricWatch services? (y/n)"
if ($continue -ne "y") {
    Write-Host "Exiting..." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "Starting MetricWatch services..." -ForegroundColor Cyan
Write-Host "This may take a few minutes on first run (downloading images, ML models)..." -ForegroundColor Yellow
Write-Host ""

# Start services
docker-compose up -d

Write-Host ""
Write-Host "Waiting for services to be healthy..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Check service status
Write-Host ""
Write-Host "Service Status:" -ForegroundColor Cyan
docker-compose ps

Write-Host ""
Write-Host "================================" -ForegroundColor Cyan
Write-Host "🎉 MetricWatch is starting!" -ForegroundColor Green
Write-Host ""
Write-Host "Access the services at:" -ForegroundColor Cyan
Write-Host "  📊 Dashboard:   http://localhost:3000" -ForegroundColor White
Write-Host "  🔌 API Gateway: http://localhost:8000" -ForegroundColor White
Write-Host "  📈 Grafana:     http://localhost:3001 (admin/admin)" -ForegroundColor White
Write-Host "  🔍 Prometheus:  http://localhost:9090" -ForegroundColor White
Write-Host ""
Write-Host "View logs with:" -ForegroundColor Cyan
Write-Host "  docker-compose logs -f" -ForegroundColor White
Write-Host ""
Write-Host "Stop services with:" -ForegroundColor Cyan
Write-Host "  docker-compose down" -ForegroundColor White
Write-Host ""
Write-Host "For troubleshooting, see README.md" -ForegroundColor Yellow
Write-Host "================================" -ForegroundColor Cyan
