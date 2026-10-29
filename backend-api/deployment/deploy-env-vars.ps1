param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('dev', 'staging', 'production')]
    [string]$Environment,

    [Parameter(Mandatory=$true)]
    [string]$AppName,

    [Parameter(Mandatory=$true)]
    [string]$ResourceGroup,

    [Parameter(Mandatory=$false)]
    [string]$ConfigFile,

    [Parameter(Mandatory=$false)]
    [switch]$ForceUpdate,

    [Parameter(Mandatory=$false)]
    [switch]$DryRun
)

# Script configuration
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Azure App Service Environment Variables Deployment" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Determine config file path
if (-not $ConfigFile) {
    $ConfigFile = Join-Path $ScriptDir "env-configs\env.$Environment.json"
}

# Validate config file exists
if (-not (Test-Path $ConfigFile)) {
    Write-Error "Configuration file not found: $ConfigFile"
    exit 1
}

Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  Environment:    $Environment"
Write-Host "  App Name:       $AppName"
Write-Host "  Resource Group: $ResourceGroup"
Write-Host "  Config File:    $ConfigFile"
Write-Host "  Force Update:   $ForceUpdate"
Write-Host "  Dry Run:        $DryRun"
Write-Host ""

# Check Azure CLI is installed
try {
    $azVersion = az version --output json | ConvertFrom-Json
    Write-Host "Azure CLI version: $($azVersion.'azure-cli')" -ForegroundColor Green
} catch {
    Write-Error "Azure CLI is not installed or not in PATH. Please install: https://aka.ms/installazurecliwindows"
    exit 1
}

# Check if logged in to Azure
Write-Host "Checking Azure authentication..." -ForegroundColor Yellow
try {
    $account = az account show 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Not logged in to Azure. Please run: az login"
        exit 1
    }
    $accountInfo = $account | ConvertFrom-Json
    Write-Host "Logged in as: $($accountInfo.user.name)" -ForegroundColor Green
    Write-Host "Subscription: $($accountInfo.name) ($($accountInfo.id))" -ForegroundColor Green
} catch {
    Write-Error "Failed to verify Azure authentication: $_"
    exit 1
}
Write-Host ""

# Verify App Service exists
Write-Host "Verifying App Service exists..." -ForegroundColor Yellow
try {
    $appService = az webapp show --name $AppName --resource-group $ResourceGroup 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Error "App Service '$AppName' not found in resource group '$ResourceGroup'"
        exit 1
    }
    Write-Host "App Service found: $AppName" -ForegroundColor Green
} catch {
    Write-Error "Failed to verify App Service: $_"
    exit 1
}
Write-Host ""

# Load configuration file
Write-Host "Loading configuration from: $ConfigFile" -ForegroundColor Yellow
try {
    $config = Get-Content $ConfigFile -Raw | ConvertFrom-Json
    $envVars = $config.environmentVariables
    Write-Host "Loaded $($envVars.PSObject.Properties.Count) environment variables from config" -ForegroundColor Green
} catch {
    Write-Error "Failed to load configuration file: $_"
    exit 1
}
Write-Host ""

# Get current App Service settings
Write-Host "Retrieving current App Service settings..." -ForegroundColor Yellow
try {
    $currentSettingsJson = az webapp config appsettings list --name $AppName --resource-group $ResourceGroup --output json
    $currentSettings = $currentSettingsJson | ConvertFrom-Json
    
    # Convert to hashtable for easier lookup
    $currentSettingsHash = @{}
    foreach ($setting in $currentSettings) {
        $currentSettingsHash[$setting.name] = $setting.value
    }
    
    Write-Host "Retrieved $($currentSettings.Count) existing settings" -ForegroundColor Green
} catch {
    Write-Error "Failed to retrieve current settings: $_"
    exit 1
}
Write-Host ""

# Determine which variables need to be added/updated
$toAdd = @{}
$toUpdate = @{}
$toSkip = @{}

foreach ($prop in $envVars.PSObject.Properties) {
    $varName = $prop.Name
    $varValue = $prop.Value
    
    if ($currentSettingsHash.ContainsKey($varName)) {
        if ($ForceUpdate) {
            $toUpdate[$varName] = $varValue
        } else {
            $toSkip[$varName] = $currentSettingsHash[$varName]
        }
    } else {
        $toAdd[$varName] = $varValue
    }
}

# Display summary
Write-Host "Deployment Summary:" -ForegroundColor Cyan
Write-Host "  Variables to add:    $($toAdd.Count)" -ForegroundColor Green
Write-Host "  Variables to update: $($toUpdate.Count)" -ForegroundColor Yellow
Write-Host "  Variables to skip:   $($toSkip.Count)" -ForegroundColor Gray
Write-Host ""

if ($toAdd.Count -eq 0 -and $toUpdate.Count -eq 0) {
    Write-Host "No changes needed. All environment variables are already configured." -ForegroundColor Green
    exit 0
}

# Show details of changes
if ($toAdd.Count -gt 0) {
    Write-Host "Variables to ADD:" -ForegroundColor Green
    foreach ($key in $toAdd.Keys | Sort-Object) {
        $value = $toAdd[$key]
        # Mask sensitive values
        $displayValue = if ($key -match "PASSWORD|SECRET|KEY|TOKEN|CONNECTION") { "***REDACTED***" } else { $value }
        Write-Host "  + $key = $displayValue"
    }
    Write-Host ""
}

if ($toUpdate.Count -gt 0) {
    Write-Host "Variables to UPDATE:" -ForegroundColor Yellow
    foreach ($key in $toUpdate.Keys | Sort-Object) {
        $value = $toUpdate[$key]
        $displayValue = if ($key -match "PASSWORD|SECRET|KEY|TOKEN|CONNECTION") { "***REDACTED***" } else { $value }
        Write-Host "  Update $key = $displayValue"
    }
    Write-Host ""
}

if ($toSkip.Count -gt 0 -and $toSkip.Count -le 20) {
    Write-Host "Variables to SKIP (already exist):" -ForegroundColor Gray
    foreach ($key in $toSkip.Keys | Sort-Object) {
        Write-Host "  - $key"
    }
    Write-Host ""
}

# Exit if dry run
if ($DryRun) {
    Write-Host "DRY RUN MODE - No changes were made" -ForegroundColor Yellow
    exit 0
}

# Merge changes
$allChanges = @{}
foreach ($key in $toAdd.Keys) { $allChanges[$key] = $toAdd[$key] }
foreach ($key in $toUpdate.Keys) { $allChanges[$key] = $toUpdate[$key] }

if ($allChanges.Count -eq 0) {
    Write-Host "No changes to apply" -ForegroundColor Green
    exit 0
}

# Apply changes
Write-Host "Applying changes to App Service..." -ForegroundColor Yellow

# Build settings array for Azure CLI
$settingsArray = @()
foreach ($key in $allChanges.Keys) {
    $value = $allChanges[$key]
    $settingsArray += "${key}=${value}"
}

try {
    # Apply all settings at once
    $result = az webapp config appsettings set --name $AppName --resource-group $ResourceGroup --settings $settingsArray --output json
    
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to apply settings"
        exit 1
    }
    
    Write-Host "Successfully applied $($allChanges.Count) environment variable(s)" -ForegroundColor Green
} catch {
    Write-Error "Failed to apply settings: $_"
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Deployment completed successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Note: The App Service will automatically restart to apply the new settings." -ForegroundColor Yellow
Write-Host ""

exit 0