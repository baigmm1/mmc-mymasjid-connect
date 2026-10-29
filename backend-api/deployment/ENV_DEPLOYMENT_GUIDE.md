# Environment Variables Deployment Guide

This guide explains how to deploy environment variables to Azure App Service using the automated deployment script.

## Overview

The deployment system consists of:

1. **PowerShell Script**: `deploy-env-vars.ps1` - Deploys environment variables to Azure App Service
2. **Environment Configs**: JSON files in `env-configs/` directory for each environment
3. **GitHub Actions Workflow**: `.github-workflow-deploy-env-vars.yml` - Automated deployment pipeline

## Quick Start

### Prerequisites

- Azure CLI installed and configured
- Azure App Service created
- Appropriate permissions on the Azure subscription
- Environment configuration files updated with your values

### 1. Update Configuration Files

Edit the appropriate config file for your environment:

```bash
# For development
backend-api/deployment/env-configs/env.dev.json

# For staging  
backend-api/deployment/env-configs/env.staging.json

# For production
backend-api/deployment/env-configs/env.production.json
```

**Required updates:**
- `DB_SERVER`: Your Azure SQL Server FQDN
- `DB_NAME`: Your database name
- `CORS_ORIGINS`: Your frontend URL(s)

### 2. Deploy Manually

```powershell
# Navigate to deployment directory
cd backend-api/deployment

# Login to Azure
az login

# Preview changes (dry run)
.\deploy-env-vars.ps1 `
  -Environment production `
  -AppName your-app-name `
  -ResourceGroup your-resource-group `
  -DryRun

# Deploy for real
.\deploy-env-vars.ps1 `
  -Environment production `
  -AppName your-app-name `
  -ResourceGroup your-resource-group
```

.\deploy-env-vars.ps1 -Environment dev -AppName mc-backend-service-api -ResourceGroup rg-dev-pymc
### 3. Deploy via GitHub Actions

#### Setup GitHub Secrets

Add these secrets to your GitHub repository:

| Secret Name | Description | Example |
|------------|-------------|---------|
| `AZURE_CREDENTIALS` | Azure service principal credentials | `{"clientId":"...","clientSecret":"...","subscriptionId":"...","tenantId":"..."}` |
| `AZURE_APP_NAME` | Azure App Service name | `masjid-connect-api` |
| `AZURE_RESOURCE_GROUP` | Azure Resource Group name | `rg-masjid-connect` |

#### Create Service Principal

```bash
# Create service principal for GitHub Actions
az ad sp create-for-rbac \
  --name "github-actions-masjid-connect" \
  --role contributor \
  --scopes /subscriptions/{subscription-id}/resourceGroups/{resource-group} \
  --sdk-auth

# Copy the JSON output to AZURE_CREDENTIALS secret
```

#### Add Workflow to Repository

```bash
# Copy the workflow file to your .github/workflows directory
mkdir -p .github/workflows
cp backend-api/deployment/.github-workflow-deploy-env-vars.yml .github/workflows/deploy-env-vars.yml
```

#### Run Workflow

1. Go to GitHub repository → Actions tab
2. Select "Deploy Environment Variables" workflow
3. Click "Run workflow"
4. Select environment (dev/staging/production)
5. Optionally enable "Force update existing variables"
6. Click "Run workflow"

## Script Features

### Smart Deployment

The script only creates environment variables that don't already exist:

- ✅ **New variables**: Automatically added
- ⏭️ **Existing variables**: Skipped (unless `-ForceUpdate` is used)
- 🔄 **Force update**: Use `-ForceUpdate` to update all variables

### Safety Features

- **Dry Run Mode**: Preview changes without applying them
- **Validation**: Checks Azure authentication and resource existence
- **Masked Output**: Sensitive values (passwords, secrets) are hidden in logs
- **Summary Report**: Shows what will be added/updated/skipped

### Example Output

```
========================================
Azure App Service Environment Variables Deployment
========================================

Configuration:
  Environment:    production
  App Name:       masjid-connect-api
  Resource Group: rg-masjid-connect
  Config File:    env-configs\env.production.json
  Force Update:   False
  Dry Run:        False

✓ Azure CLI version: 2.50.0
✓ Logged in as: user@domain.com
✓ Subscription: My Subscription (12345678-1234-1234-1234-123456789abc)
✓ App Service found: masjid-connect-api
✓ Loaded 17 environment variables from config
✓ Retrieved 12 existing settings

Deployment Summary:
  Variables to add:    5
  Variables to update: 0
  Variables to skip:   12

Variables to ADD:
  + DB_POOL_SIZE = 20
  + DB_MAX_OVERFLOW = 10
  + DB_POOL_RECYCLE = 300
  + DB_CONNECT_TIMEOUT = 30
  + DB_ECHO_SQL = False

Applying changes to App Service...
✓ Successfully applied 5 environment variable(s)

========================================
Deployment completed successfully!
========================================

Note: The App Service will automatically restart to apply the new settings.
```

## Script Parameters

### Required Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `-Environment` | Target environment | `dev`, `staging`, `production` |
| `-AppName` | Azure App Service name | `masjid-connect-api` |
| `-ResourceGroup` | Azure Resource Group | `rg-masjid-connect` |

### Optional Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `-ConfigFile` | Custom config file path | `env-configs\env.{environment}.json` |
| `-ForceUpdate` | Update existing variables | `False` |
| `-DryRun` | Preview without applying | `False` |

## Common Scenarios

### Scenario 1: Initial Deployment

Deploy all variables to a fresh App Service:

```powershell
.\deploy-env-vars.ps1 `
  -Environment production `
  -AppName myapp `
  -ResourceGroup myrg
```

### Scenario 2: Add New Variables

Add new variables without affecting existing ones:

1. Update config file with new variables
2. Run deployment script (default behavior)
3. Only new variables will be added

### Scenario 3: Update Existing Variables

Force update all variables with new values:

```powershell
.\deploy-env-vars.ps1 `
  -Environment production `
  -AppName myapp `
  -ResourceGroup myrg `
  -ForceUpdate
```

### Scenario 4: Preview Changes

See what would change without applying:

```powershell
.\deploy-env-vars.ps1 `
  -Environment production `
  -AppName myapp `
  -ResourceGroup myrg `
  -DryRun
```

### Scenario 5: Deploy to Multiple Environments

Deploy to dev, staging, and production in sequence:

```powershell
# Deploy to dev
.\deploy-env-vars.ps1 -Environment dev -AppName myapp-dev -ResourceGroup myrg

# Verify dev is working, then deploy to staging
.\deploy-env-vars.ps1 -Environment staging -AppName myapp-staging -ResourceGroup myrg

# Verify staging is working, then deploy to production
.\deploy-env-vars.ps1 -Environment production -AppName myapp-prod -ResourceGroup myrg
```

## Configuration File Format

Each environment configuration file is a JSON file with this structure:

```json
{
  "environmentName": "production",
  "description": "Production environment configuration",
  "lastUpdated": "2025-12-10",
  "environmentVariables": {
    "VARIABLE_NAME": "value",
    "ANOTHER_VARIABLE": "another_value"
  },
  "notes": [
    "Important notes about this configuration"
  ]
}
```

### Adding New Variables

1. Edit the appropriate config file
2. Add the new variable to `environmentVariables` object
3. Update `lastUpdated` field
4. Add note explaining the change
5. Run deployment script

### Removing Variables

To remove a variable from App Service:

```powershell
# Use Azure CLI directly
az webapp config appsettings delete `
  --name myapp `
  --resource-group myrg `
  --setting-names VARIABLE_TO_REMOVE
```

Then update the config file to remove the variable from tracking.

## Integration with CI/CD

### As Part of Deployment Pipeline

Add this step to your main deployment workflow:

```yaml
jobs:
  deploy:
    steps:
      # ... build and deploy steps ...
      
      - name: Deploy Environment Variables
        uses: ./.github/workflows/deploy-env-vars.yml
        with:
          environment: ${{ github.event.inputs.environment }}
          force_update: false
        secrets:
          AZURE_CREDENTIALS: ${{ secrets.AZURE_CREDENTIALS }}
          AZURE_APP_NAME: ${{ secrets.AZURE_APP_NAME }}
          AZURE_RESOURCE_GROUP: ${{ secrets.AZURE_RESOURCE_GROUP }}
      
      # ... verification steps ...
```

### Standalone Workflow

Use the standalone workflow for manual deployments or configuration updates:

- Manual trigger via GitHub Actions UI
- Scheduled updates (e.g., weekly configuration review)
- Triggered by configuration file changes

## Troubleshooting

### Issue: Configuration file not found

**Error:**
```
Configuration file not found: env-configs\env.production.json
```

**Solution:**
- Ensure you're running from the `deployment` directory
- Verify the config file exists
- Use `-ConfigFile` parameter to specify custom path

### Issue: Not authenticated with Azure

**Error:**
```
Not logged in to Azure. Please run: az login
```

**Solution:**
```powershell
az login
az account show  # Verify correct subscription
```

### Issue: App Service not found

**Error:**
```
App Service 'myapp' not found in resource group 'myrg'
```

**Solution:**
- Verify App Service name is correct
- Verify Resource Group name is correct
- Check you're using the right subscription: `az account show`

### Issue: Permission denied

**Error:**
```
Failed to apply settings: insufficient permissions
```

**Solution:**
- Ensure your account has Contributor role on the App Service
- For service principal, verify it has appropriate RBAC role
- Check subscription permissions

### Issue: Variables not taking effect

**Problem:** Deployed variables but application doesn't see them

**Solution:**
1. Verify variables are set in Azure Portal
2. Check App Service restarted (happens automatically)
3. Manual restart if needed: `az webapp restart --name myapp --resource-group myrg`
4. Check application logs for configuration errors

## Best Practices

### Version Control

- ✅ Commit configuration files to git
- ✅ Use meaningful commit messages
- ✅ Require pull request reviews for production changes
- ✅ Tag releases with environment configuration versions

### Security

- ❌ Never commit secrets or credentials
- ✅ Use Managed Identity for database authentication (no passwords needed)
- ✅ Use GitHub Secrets for deployment credentials
- ✅ Review changes before deploying to production

### Deployment Process

1. **Test locally** - Verify configuration works in dev environment
2. **Dry run** - Use `-DryRun` to preview production changes
3. **Deploy to dev** - Test with actual Azure resources
4. **Deploy to staging** - Validate with production-like environment
5. **Deploy to production** - Deploy during maintenance window if possible
6. **Verify** - Check application health and logs

### Maintenance

- Update `lastUpdated` field when modifying configs
- Document changes in `notes` array
- Regular reviews of environment variables (quarterly)
- Remove obsolete variables promptly
- Keep staging and production configs in sync (except environment-specific values)

## Related Documentation

- [env-configs/README.md](env-configs/README.md) - Configuration files documentation
- [ENV_REFERENCE.md](../ENV_REFERENCE.md) - Complete environment variables reference
- [AZURE_APPSERVICE_CONFIGURATION.md](../specifications/002-azure-sql-support/AZURE_APPSERVICE_CONFIGURATION.md) - Azure setup guide

---

**Last Updated**: December 10, 2025  
**Version**: 1.0
