# GitHub Workflows Configuration Guide

## Overview

This guide explains the enhanced GitHub Actions workflow for deploying the Python backend API to Azure Web Apps with support for multiple environments.

## Workflow: `develop_mmc-api-app.yml`

### Features

1. **Multi-Branch Support**: Automatically deploys to different Azure Web Apps based on the branch

   - `develop` branch → Development environment
   - `main` branch → Production environment

2. **Environment Variable Deployment**: Automatically deploys environment variables before application deployment

3. **Conditional Building**: Only builds and deploys when changes are detected in the `backend-api/` directory

### Branch-to-Environment Mapping

| Branch  | Azure Web App              | Resource Group | Environment |
| ------- | -------------------------- | -------------- | ----------- |
| develop | mc-backend-service-api     | rg-dev-pymc    | dev         |
| main    | mc-backend-service-api-prd | rg-prd-pymc    | production  |

## Required Secrets

You need to configure the following secrets in your GitHub repository for **both environments**:

### For Development (develop branch)

- `AZUREAPPSERVICE_CLIENTID_9AD894D8FD7F44CA8EEE4B9F45931254` - Azure Service Principal Client ID
- `AZUREAPPSERVICE_TENANTID_E33EC653433642E79FD8B70954692EB5` - Azure Tenant ID
- `AZUREAPPSERVICE_SUBSCRIPTIONID_772D5A24E20A44C7B3D442D661BD4384` - Azure Subscription ID

### For Production (main branch)

- `AZUREAPPSERVICE_CLIENTID_PROD` - Azure Service Principal Client ID for Production
- `AZUREAPPSERVICE_TENANTID_E33EC653433642E79FD8B70954692EB5` - Azure Tenant ID
- `AZUREAPPSERVICE_SUBSCRIPTIONID_772D5A24E20A44C7B3D442D661BD4384` - Azure Subscription ID

## Setting Up GitHub Secrets

1. Go to your GitHub repository
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret with the exact name shown above

## Setting Up Azure Service Principal for Production

If you haven't created a Service Principal for production yet, follow these steps:

```bash
# Login to Azure
az login

# Set the subscription (replace with your production subscription ID)
az account set --subscription "your-prod-subscription-id"

# Create a service principal with contributor role for the resource group
az ad sp create-for-rbac \
  --name "mmc-api-prod-github-actions" \
  --role contributor \
  --scopes /subscriptions/{subscription-id}/resourceGroups/rg-prod-pymc \
  --sdk-auth

# The output will contain the clientId, tenantId, and subscriptionId
# Add these to GitHub Secrets as specified above
```

## Environment Configuration Files

Ensure you have environment configuration files in `backend-api/deployment/env-configs/`:

- `env.dev.json` - Development environment variables
- `env.production.json` - Production environment variables

## Workflow Jobs

### 1. Setup Job

- Determines the target environment based on the branch
- Sets environment-specific variables (app name, resource group, secrets)
- Outputs these variables for subsequent jobs

### 2. Build Job

- Checks for changes in the `backend-api/` directory
- Sets up Python environment
- Installs dependencies
- Creates deployment artifact
- Only runs if backend changes are detected

### 3. Deploy Job

- Downloads the build artifact
- Authenticates with Azure using environment-specific credentials
- **Deploys environment variables** using the PowerShell script
- Stops the web app for clean deployment
- Creates a deployment package
- Configures Oryx build settings
- Deploys to Azure Web App
- Starts the web app
- Provides deployment summary

## Environment Variable Deployment

The workflow automatically runs the `deploy-env-vars.ps1` script before deploying the application. This ensures that:

1. All environment variables are up-to-date
2. Configuration changes are applied before the new code runs
3. The deployment is consistent across environments

If the script is not found, the workflow will log a warning and continue without failing.

## Manual Workflow Trigger

You can manually trigger the workflow from the GitHub Actions tab:

1. Go to **Actions** tab in your repository
2. Select **Azure Python Backend - Deploy API**
3. Click **Run workflow**
4. Choose the branch (develop or main)
5. Click **Run workflow**

## Monitoring Deployments

After deployment completes, you can access your application at:

- **Development**: https://mc-backend-service-api.azurewebsites.net
- **Production**: https://mmc-api-app-prod.azurewebsites.net

## Troubleshooting

### Deployment Fails Due to Missing Secrets

**Error**: `secret not found`

**Solution**: Ensure all required secrets are configured in GitHub Settings → Secrets and variables → Actions

### Environment Variables Not Deployed

**Error**: `deploy-env-vars.ps1 not found`

**Solution**: Ensure the PowerShell script exists in `backend-api/deployment/deploy-env-vars.ps1`

### Azure Authentication Fails

**Error**: `AADSTS700016: Application with identifier not found`

**Solution**:

1. Verify the Service Principal exists in Azure AD
2. Check that the Client ID, Tenant ID, and Subscription ID match
3. Ensure the Service Principal has Contributor role on the resource group

### No Deployment on Push

**Cause**: No changes detected in `backend-api/` directory

**Solution**: This is expected behavior. The workflow only deploys when backend code changes are detected.

## Best Practices

1. **Always test in develop first**: Push changes to develop branch before merging to main
2. **Review environment variables**: Before deploying to production, review the env.production.json file
3. **Monitor deployments**: Check the GitHub Actions tab for deployment status
4. **Use deployment slots**: Consider using Azure deployment slots for zero-downtime deployments
5. **Keep secrets secure**: Never commit secrets to the repository

## Related Documentation

- [Azure Web Apps Deploy Action](https://github.com/Azure/webapps-deploy)
- [GitHub Actions for Azure](https://github.com/Azure/actions)
- [Environment Variable Deployment Guide](../../backend-api/deployment/ENV_DEPLOYMENT_GUIDE.md)
