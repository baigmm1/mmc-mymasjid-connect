# Manual Azure Deployment Script for Masjid Connect Backend API (PowerShell)
# This script deploys the application to Azure App Service with proper ORYX configuration

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet('development', 'staging', 'production')]
    [string]$Environment = "development",

    [Parameter(Mandatory=$false)]
    [string]$AppName,

    [Parameter(Mandatory=$false)]
    [string]$ResourceGroup,

    [Parameter(Mandatory=$false)]
    [string]$Location = "eastus",

    [Parameter(Mandatory=$false)]
    [string]$AppServicePlan,

    [Parameter(Mandatory=$false)]
    [string]$Sku = "B2",

    [Parameter(Mandatory=$false)]
    [string]$PythonVersion = "3.11",

    [Parameter(Mandatory=$false)]
    [switch]$DryRun
)

# Exit on any error
$ErrorActionPreference = "Stop"

# ============================================================================
# Configuration Variables
# ============================================================================
# Use parameter values if provided, otherwise use defaults
$RESOURCE_GROUP = if ($ResourceGroup) { $ResourceGroup } else { "rg-dev-pymc" }
$APP_NAME = if ($AppName) { $AppName } else { "mmc-api-app-dev" }
$LOCATION = $Location
$APP_SERVICE_PLAN = if ($AppServicePlan) { $AppServicePlan } else { "plan-mmc-dev" }
$SKU = $Sku
$PYTHON_VERSION = $PythonVersion

Write-Host "=== Masjid Connect Backend - Azure Deployment ===" -ForegroundColor Green
Write-Host "Environment:    $Environment"
Write-Host "Resource Group: $RESOURCE_GROUP"
Write-Host "App Name:       $APP_NAME"
Write-Host "Location:       $LOCATION"
Write-Host "App Plan:       $APP_SERVICE_PLAN"
Write-Host "SKU:            $SKU"
Write-Host "Python Version: $PYTHON_VERSION"
if ($DryRun) {
    Write-Host "DRY RUN MODE:   Enabled (no changes will be made)" -ForegroundColor Yellow
}
Write-Host ""

# ============================================================================
# Step 1: Verify Azure CLI is installed and logged in
# ============================================================================
Write-Host "Step 1: Verifying Azure CLI..." -ForegroundColor Yellow
if (!(Get-Command az -ErrorAction SilentlyContinue)) {
    Write-Host "Error: Azure CLI is not installed. Install it from https://aka.ms/installazurecli" -ForegroundColor Red
    exit 1
}

Write-Host "Azure CLI version:"
az version --output table

Write-Host "Checking login status..."
try {
    az account show --output table
}
catch {
    Write-Host "Not logged in. Running 'az login'..." -ForegroundColor Red
    az login
}

Write-Host "✓ Azure CLI verified`n" -ForegroundColor Green

# ============================================================================
# Step 2: Create App Service Plan (if not exists)
# ============================================================================
Write-Host "Step 2: Checking App Service Plan..." -ForegroundColor Yellow
$planExists = az appservice plan show --name $APP_SERVICE_PLAN --resource-group $RESOURCE_GROUP 2>$null
if ($planExists) {
    Write-Host "App Service Plan '$APP_SERVICE_PLAN' already exists"
}
else {
    if ($DryRun) {
        Write-Host "[DRY RUN] Would create App Service Plan '$APP_SERVICE_PLAN'" -ForegroundColor Yellow
    } else {
        Write-Host "Creating App Service Plan '$APP_SERVICE_PLAN'..."
        az appservice plan create `
            --name $APP_SERVICE_PLAN `
            --resource-group $RESOURCE_GROUP `
            --location $LOCATION `
            --is-linux `
            --sku $SKU
        Write-Host "✓ App Service Plan created" -ForegroundColor Green
    }
}
Write-Host ""

# ============================================================================
# Step 3: Create Web App (if not exists)
# ============================================================================
Write-Host "Step 3: Checking Web App..." -ForegroundColor Yellow
$webappExists = az webapp show --name $APP_NAME --resource-group $RESOURCE_GROUP 2>$null
if ($webappExists) {
    Write-Host "Web App '$APP_NAME' already exists"
}
else {
    if ($DryRun) {
        Write-Host "[DRY RUN] Would create Web App '$APP_NAME'" -ForegroundColor Yellow
    } else {
        Write-Host "Creating Web App '$APP_NAME'..."
        az webapp create `
            --name $APP_NAME `
            --resource-group $RESOURCE_GROUP `
            --plan $APP_SERVICE_PLAN `
            --runtime "PYTHON:$PYTHON_VERSION"
        Write-Host "✓ Web App created" -ForegroundColor Green
    }
}
Write-Host ""

# ============================================================================
# Step 4: Configure Run from Package Settings
# ============================================================================
Write-Host "Step 4: Configuring Run from Package settings..." -ForegroundColor Yellow
if ($DryRun) {
    Write-Host "[DRY RUN] Would configure Run from Package settings" -ForegroundColor Yellow
} else {
    az webapp config appsettings set `
        --name $APP_NAME `
        --resource-group $RESOURCE_GROUP `
        --settings `
        SCM_DO_BUILD_DURING_DEPLOYMENT=false `
        WEBSITE_RUN_FROM_PACKAGE=1 `
        PYTHON_VERSION=$PYTHON_VERSION
    Write-Host "✓ Run from Package settings configured" -ForegroundColor Green
}
Write-Host ""

# ============================================================================
# Step 5: Configure Startup Command
# ============================================================================
Write-Host "Step 5: Configuring startup command..." -ForegroundColor Yellow
if ($DryRun) {
    Write-Host "[DRY RUN] Would configure startup command" -ForegroundColor Yellow
} else {
    az webapp config set `
        --name $APP_NAME `
        --resource-group $RESOURCE_GROUP `
        --startup-file "startup.txt"
    Write-Host "✓ Startup command configured to use startup.txt" -ForegroundColor Green
}
Write-Host ""

# ============================================================================
# Step 6: Configure Application Settings
# ============================================================================
Write-Host "Step 6: Configuring application environment variables..." -ForegroundColor Yellow
if (-not $DryRun) {
    Write-Host "⚠️  IMPORTANT: Update these values before deployment!"
    $confirmation = Read-Host "Have you updated the environment variables in this script? (y/n)"
    if ($confirmation -ne 'y' -and $confirmation -ne 'Y') {
        Write-Host "Please update the environment variables in the 'Configure App Settings' section and run again." -ForegroundColor Red
        exit 1
    }
}

# Configure application environment variables
# ⚠️ UPDATE THESE VALUES FOR YOUR ENVIRONMENT
az webapp config appsettings set `
    --name $APP_NAME `
    --resource-group $RESOURCE_GROUP `
    --settings `
    ENVIRONMENT=development `
    DEBUG=false `
    API_VERSION=1.0.0 `
    API_TITLE="Masjid Connect API" `
    LOG_LEVEL=INFO `
    PORT=8000 `
    WORKERS=4 `
    TIMEOUT=600 `
    DB_SERVER="your-server.database.windows.net" `
    DB_NAME="masjiddb" `
    DB_POOL_SIZE=20 `
    DB_MAX_OVERFLOW=10 `
    DB_POOL_RECYCLE=3600 `
    CORS_ORIGINS='[\"https://yourdomain.com\"]' `
    CORS_ALLOW_CREDENTIALS=true `
    CORS_ALLOW_METHODS='[\"GET\",\"POST\",\"PUT\",\"DELETE\",\"OPTIONS\",\"PATCH\"]' `
    CORS_ALLOW_HEADERS='[\"*\"]'

Write-Host "✓ Application settings configured`n" -ForegroundColor Green

# ============================================================================
# Step 7: Enable Managed Identity (for database access)
# ============================================================================
Write-Host "Step 7: Enabling system-assigned managed identity..." -ForegroundColor Yellow
if ($DryRun) {
    Write-Host "[DRY RUN] Would enable system-assigned managed identity" -ForegroundColor Yellow
} else {
    az webapp identity assign `
        --name $APP_NAME `
        --resource-group $RESOURCE_GROUP
    Write-Host "✓ Managed identity enabled" -ForegroundColor Green
}
Write-Host ""

# ============================================================================
# Step 8: Create and Deploy Application Package
# ============================================================================
if ($DryRun) {
    Write-Host "Step 8: Create and Deploy Application Package..." -ForegroundColor Yellow
    Write-Host "[DRY RUN] Would create deployment package and deploy to Azure" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "=== DRY RUN COMPLETE ===" -ForegroundColor Green
    Write-Host "No changes were made to Azure resources." -ForegroundColor Yellow
    Write-Host "Remove -DryRun flag to execute the deployment." -ForegroundColor Yellow
    exit 0
}

Write-Host "Step 8: Creating deployment package..." -ForegroundColor Yellow

# Create temp directory for package
$tempDir = New-Item -ItemType Directory -Path "$env:TEMP\azure-deploy-$(Get-Date -Format 'yyyyMMdd-HHmmss')" -Force
$packagePath = Join-Path $tempDir "deploy.zip"

Write-Host "Packaging application files..."
# Create zip excluding unnecessary files
Compress-Archive -Path * -DestinationPath $packagePath -Force `
    -Exclude @("venv", ".venv", "env", "__pycache__", ".pytest_cache", "*.pyc", ".git", ".gitignore", "tests", "*.log")

Write-Host "Package created: $packagePath"
Write-Host "Package size: $((Get-Item $packagePath).Length / 1MB) MB"

Write-Host "Deploying package to Azure..."
az webapp deployment source config-zip `
    --resource-group $RESOURCE_GROUP `
    --name $APP_NAME `
    --src $packagePath

# Clean up temp directory
Remove-Item -Path $tempDir -Recurse -Force

Write-Host "✓ Application deployed`n" -ForegroundColor Green

# ============================================================================
# Step 9: Verify Deployment
# ============================================================================
Write-Host "Step 9: Verifying deployment..." -ForegroundColor Yellow
Write-Host "Waiting 30 seconds for app to start..."
Start-Sleep -Seconds 30

$APP_URL = "https://$APP_NAME.azurewebsites.net"

Write-Host "Testing root endpoint..."
try {
    $response = Invoke-RestMethod -Uri "$APP_URL/" -Method Get
    $response | ConvertTo-Json
}
catch {
    Write-Host "Root endpoint check failed: $_" -ForegroundColor Red
}

Write-Host "`nTesting health endpoint..."
try {
    $response = Invoke-RestMethod -Uri "$APP_URL/health" -Method Get
    $response | ConvertTo-Json
}
catch {
    Write-Host "Health endpoint check failed: $_" -ForegroundColor Red
}

Write-Host "`nTesting database health endpoint..."
try {
    $response = Invoke-RestMethod -Uri "$APP_URL/health/db" -Method Get
    $response | ConvertTo-Json
}
catch {
    Write-Host "Database health endpoint check failed: $_" -ForegroundColor Red
}

Write-Host "`n=== Deployment Complete! ===" -ForegroundColor Green
Write-Host ""
Write-Host "Application URL: $APP_URL"
Write-Host "API Documentation: $APP_URL/docs"
Write-Host "Health Check: $APP_URL/health"
Write-Host "Database Health: $APP_URL/health/db"
Write-Host ""
Write-Host "View logs with:"
Write-Host "  az webapp log tail --name $APP_NAME --resource-group $RESOURCE_GROUP"
Write-Host ""
Write-Host "SSH into container:"
Write-Host "  az webapp ssh --name $APP_NAME --resource-group $RESOURCE_GROUP"
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Configure database access for managed identity (see AZURE_APPSERVICE_CONFIGURATION.md)"
Write-Host "2. Update CORS_ORIGINS with your frontend domain"
Write-Host "3. Configure Application Insights for monitoring"
Write-Host "4. Set up custom domain and SSL certificate"
Write-Host ""
