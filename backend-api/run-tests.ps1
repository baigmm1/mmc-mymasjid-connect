#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Run pytest tests from the backend-api directory without manual configuration.

.DESCRIPTION
    This script automatically runs pytest with the correct Python interpreter
    and path configuration. No need to manually set PYTHONPATH.

.PARAMETER TestPaths
    Optional paths to specific test files or directories. Defaults to all tests.
    Can specify multiple paths.

.PARAMETER Verbose
    Run tests in verbose mode with detailed output.

.PARAMETER Quick
    Run tests in quiet mode with minimal output.

.PARAMETER Coverage
    Run tests with coverage reporting.

.EXAMPLE
    .\run-tests.ps1
    Run all tests

.EXAMPLE
    .\run-tests.ps1 -TestPath tests/unit/database/
    Run only database unit tests

.EXAMPLE
    .\run-tests.ps1 -VerboseOutput
    Run all tests with verbose output

.EXAMPLE
    .\run-tests.ps1 -Quick tests/integration/
    Run integration tests in quiet mode

.EXAMPLE
    .\run-tests.ps1 tests/unit/database/ tests/integration/test_database.py
    Run multiple test paths
#>

param(
    [Parameter(Position = 0, ValueFromRemainingArguments)]
    [string[]]$TestPaths = @("tests/"),
    
    [switch]$VerboseOutput,
    [switch]$Quick,
    [switch]$Coverage
)

# Get the script directory (backend-api)
$BackendApiDir = $PSScriptRoot
$VenvPython = Join-Path $BackendApiDir "..\.venv\Scripts\python.exe"

# Verify Python exists
if (-not (Test-Path $VenvPython)) {
    Write-Error "Python virtual environment not found at: $VenvPython"
    Write-Host "Please ensure the virtual environment is activated or create it first."
    exit 1
}

# Build pytest arguments
$PytestArgs = @()
$PytestArgs += $TestPaths

if ($VerboseOutput) {
    $PytestArgs += "-v"
    $PytestArgs += "--tb=short"
}
elseif ($Quick) {
    $PytestArgs += "-q"
    $PytestArgs += "--tb=line"
}
else {
    $PytestArgs += "-v"
    $PytestArgs += "--tb=line"
}

if ($Coverage) {
    $PytestArgs += "--cov=src"
    $PytestArgs += "--cov-report=term-missing"
}

# Run pytest from backend-api directory
Write-Host "Running tests from: $BackendApiDir" -ForegroundColor Cyan
Write-Host "Test paths: $($TestPaths -join ', ')" -ForegroundColor Cyan
Write-Host ""

& $VenvPython -m pytest @PytestArgs

# Return pytest exit code
exit $LASTEXITCODE
