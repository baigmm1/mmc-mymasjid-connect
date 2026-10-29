#!/bin/bash
# Manual Azure Deployment Script for Masjid Connect Backend API
# This script deploys the application to Azure App Service with proper ORYX configuration

# Exit on any error
set -e

# ============================================================================
# Configuration Variables - UPDATE THESE FOR YOUR ENVIRONMENT
# ============================================================================
RESOURCE_GROUP="rg-dev-pymc"
APP_NAME="mmc-api-app-dev"
LOCATION="eastus"
APP_SERVICE_PLAN="plan-mmc-dev"
SKU="B2"
PYTHON_VERSION="3.11"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Masjid Connect Backend - Azure Deployment ===${NC}"
echo "Resource Group: $RESOURCE_GROUP"
echo "App Name: $APP_NAME"
echo "Location: $LOCATION"
echo ""

# ============================================================================
# Step 1: Verify Azure CLI is installed and logged in
# ============================================================================
echo -e "${YELLOW}Step 1: Verifying Azure CLI...${NC}"
if ! command -v az &> /dev/null; then
    echo -e "${RED}Error: Azure CLI is not installed. Install it from https://aka.ms/installazurecli${NC}"
    exit 1
fi

echo "Azure CLI version:"
az version --output table

echo "Checking login status..."
az account show --output table || {
    echo -e "${RED}Not logged in. Running 'az login'...${NC}"
    az login
}

echo -e "${GREEN}✓ Azure CLI verified${NC}\n"

# ============================================================================
# Step 2: Create App Service Plan (if not exists)
# ============================================================================
echo -e "${YELLOW}Step 2: Checking App Service Plan...${NC}"
if az appservice plan show --name $APP_SERVICE_PLAN --resource-group $RESOURCE_GROUP &> /dev/null; then
    echo "App Service Plan '$APP_SERVICE_PLAN' already exists"
else
    echo "Creating App Service Plan '$APP_SERVICE_PLAN'..."
    az appservice plan create \
        --name $APP_SERVICE_PLAN \
        --resource-group $RESOURCE_GROUP \
        --location $LOCATION \
        --is-linux \
        --sku $SKU
    echo -e "${GREEN}✓ App Service Plan created${NC}"
fi
echo ""

# ============================================================================
# Step 3: Create Web App (if not exists)
# ============================================================================
echo -e "${YELLOW}Step 3: Checking Web App...${NC}"
if az webapp show --name $APP_NAME --resource-group $RESOURCE_GROUP &> /dev/null; then
    echo "Web App '$APP_NAME' already exists"
else
    echo "Creating Web App '$APP_NAME'..."
    az webapp create \
        --name $APP_NAME \
        --resource-group $RESOURCE_GROUP \
        --plan $APP_SERVICE_PLAN \
        --runtime "PYTHON:$PYTHON_VERSION"
    echo -e "${GREEN}✓ Web App created${NC}"
fi
echo ""

# ============================================================================
# Step 4: Configure Run from Package Settings
# ============================================================================
echo -e "${YELLOW}Step 4: Configuring Run from Package settings...${NC}"
az webapp config appsettings set \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --settings \
        SCM_DO_BUILD_DURING_DEPLOYMENT=false \
        WEBSITE_RUN_FROM_PACKAGE=1 \
        PYTHON_VERSION=$PYTHON_VERSION
echo -e "${GREEN}✓ Run from Package settings configured${NC}\n"

# ============================================================================
# Step 5: Configure Startup Command
# ============================================================================
echo -e "${YELLOW}Step 5: Configuring startup command...${NC}"
az webapp config set \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --startup-file "startup.txt"
echo -e "${GREEN}✓ Startup command configured to use startup.txt${NC}\n"

# ============================================================================
# Step 6: Configure Application Settings
# ============================================================================
echo -e "${YELLOW}Step 6: Configuring application environment variables...${NC}"
echo "⚠️  IMPORTANT: Update these values before deployment!"
echo ""
read -p "Have you updated the environment variables in this script? (y/n): " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${RED}Please update the environment variables in the 'Configure App Settings' section below and run again.${NC}"
    exit 1
fi

# Configure application environment variables
# ⚠️ UPDATE THESE VALUES FOR YOUR ENVIRONMENT
az webapp config appsettings set \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --settings \
        ENVIRONMENT=development \
        DEBUG=false \
        API_VERSION=1.0.0 \
        API_TITLE="Masjid Connect API" \
        LOG_LEVEL=INFO \
        PORT=8000 \
        WORKERS=4 \
        TIMEOUT=600 \
        DB_SERVER="your-server.database.windows.net" \
        DB_NAME="masjiddb" \
        DB_POOL_SIZE=20 \
        DB_MAX_OVERFLOW=10 \
        DB_POOL_RECYCLE=3600 \
        CORS_ORIGINS='["https://yourdomain.com"]' \
        CORS_ALLOW_CREDENTIALS=true \
        CORS_ALLOW_METHODS='["GET","POST","PUT","DELETE","OPTIONS","PATCH"]' \
        CORS_ALLOW_HEADERS='["*"]'

echo -e "${GREEN}✓ Application settings configured${NC}\n"

# ============================================================================
# Step 7: Enable Managed Identity (for database access)
# ============================================================================
echo -e "${YELLOW}Step 7: Enabling system-assigned managed identity...${NC}"
az webapp identity assign \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP
echo -e "${GREEN}✓ Managed identity enabled${NC}\n"

# ============================================================================
# Step 8: Create and Deploy Application Package
# ============================================================================
echo -e "${YELLOW}Step 8: Creating deployment package...${NC}"

# Change to backend-api directory
cd "$(dirname "$0")"

# Create temp directory for package
TEMP_DIR=$(mktemp -d)
PACKAGE_PATH="$TEMP_DIR/deploy.zip"

echo "Packaging application files..."
# Create zip excluding unnecessary files
zip -r "$PACKAGE_PATH" . \
    -x "*.git*" \
    -x "*venv/*" \
    -x "*.venv/*" \
    -x "*env/*" \
    -x "*__pycache__/*" \
    -x "*.pytest_cache/*" \
    -x "*.pyc" \
    -x "*tests/*" \
    -x "*.log"

echo "Package created: $PACKAGE_PATH"
echo "Package size: $(du -h "$PACKAGE_PATH" | cut -f1)"

echo "Deploying package to Azure..."
az webapp deployment source config-zip \
    --resource-group $RESOURCE_GROUP \
    --name $APP_NAME \
    --src "$PACKAGE_PATH"

# Clean up temp directory
rm -rf "$TEMP_DIR"

echo -e "${GREEN}✓ Application deployed${NC}\n"

# ============================================================================
# Step 9: Verify Deployment
# ============================================================================
echo -e "${YELLOW}Step 9: Verifying deployment...${NC}"
echo "Waiting 30 seconds for app to start..."
sleep 30

APP_URL="https://$APP_NAME.azurewebsites.net"

echo "Testing root endpoint..."
curl -s "$APP_URL/" | jq . || echo "Root endpoint check failed or jq not installed"

echo ""
echo "Testing health endpoint..."
curl -s "$APP_URL/health" | jq . || echo "Health endpoint check failed or jq not installed"

echo ""
echo "Testing database health endpoint..."
curl -s "$APP_URL/health/db" | jq . || echo "Database health endpoint check failed or jq not installed"

echo ""
echo -e "${GREEN}=== Deployment Complete! ===${NC}"
echo ""
echo "Application URL: $APP_URL"
echo "API Documentation: $APP_URL/docs"
echo "Health Check: $APP_URL/health"
echo "Database Health: $APP_URL/health/db"
echo ""
echo "View logs with:"
echo "  az webapp log tail --name $APP_NAME --resource-group $RESOURCE_GROUP"
echo ""
echo "SSH into container:"
echo "  az webapp ssh --name $APP_NAME --resource-group $RESOURCE_GROUP"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Configure database access for managed identity (see AZURE_APPSERVICE_CONFIGURATION.md)"
echo "2. Update CORS_ORIGINS with your frontend domain"
echo "3. Configure Application Insights for monitoring"
echo "4. Set up custom domain and SSL certificate"
echo ""
