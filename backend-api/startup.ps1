# Startup script for Masjid Connect API on Azure App Service (Windows)
# 
# This PowerShell script configures and starts the FastAPI application using Gunicorn
# with Uvicorn workers for production deployment on Azure App Service.

Write-Host "=== Masjid Connect API - Startup Script (PowerShell) ===" -ForegroundColor Green
Write-Host "Start time: $(Get-Date)" -ForegroundColor Cyan

# Get to the deployment directory
Set-Location -Path $env:DEPLOYMENT_TARGET

# Create log directory if it doesn't exist
if (-not (Test-Path -Path "logs")) {
    New-Item -ItemType Directory -Path "logs" -Force | Out-Null
    Write-Host "Created logs directory" -ForegroundColor Green
}

# Check if gunicorn is installed
try {
    python -m gunicorn --version | Out-Null
}
catch {
    Write-Host "Installing gunicorn..." -ForegroundColor Yellow
    pip install gunicorn --quiet
}

# Set environment variables for production if not already set
if (-not $env:ENVIRONMENT) { $env:ENVIRONMENT = "production" }
if (-not $env:DEBUG) { $env:DEBUG = "False" }
if (-not $env:LOG_LEVEL) { $env:LOG_LEVEL = "INFO" }

# Log configuration
Write-Host "Configuration:" -ForegroundColor Cyan
Write-Host "  ENVIRONMENT: $($env:ENVIRONMENT)"
Write-Host "  DEBUG: $($env:DEBUG)"
Write-Host "  LOG_LEVEL: $($env:LOG_LEVEL)"
Write-Host "  HOST: 0.0.0.0"
Write-Host "  PORT: 8000"
Write-Host ""

# Start Gunicorn with Uvicorn workers
Write-Host "Starting Gunicorn with Uvicorn workers..." -ForegroundColor Green

# Calculate optimal worker count (2 × CPU cores + 1, max 8)
$cpuCores = [Environment]::ProcessorCount
$workers = [Math]::Min(($cpuCores * 2 + 1), 8)

Write-Host "Workers: $workers (CPU cores: $cpuCores)" -ForegroundColor Green
Write-Host ""

& python -m gunicorn `
    --workers $workers `
    --worker-class uvicorn.workers.UvicornWorker `
    --bind 0.0.0.0:8000 `
    --timeout 120 `
    --access-logfile logs/access.log `
    --error-logfile logs/error.log `
    --log-level info `
    --graceful-timeout 30 `
    src.main:app
