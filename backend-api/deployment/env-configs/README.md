# Environment Configuration Files

This directory contains environment-specific configuration files for deploying environment variables to Azure App Service.

## Files

- **env.dev.json** - Development environment configuration
- **env.staging.json** - Staging environment configuration  
- **env.production.json** - Production environment configuration
- **env.template.json** - Template for creating new environment configs

## Structure

Each configuration file follows this JSON structure:

```json
{
  "environmentName": "environment-name",
  "description": "Environment description",
  "lastUpdated": "YYYY-MM-DD",
  "environmentVariables": {
    "VAR_NAME": "value",
    "ANOTHER_VAR": "value"
  },
  "notes": [
    "Important notes about this environment"
  ]
}
```

## Usage

### 1. Update Configuration Files

Before deploying, update the configuration files with your actual values:

**Required Updates:**
- `DB_SERVER`: Your Azure SQL Server FQDN (e.g., `myserver.database.windows.net`)
- `DB_NAME`: Your database name
- `CORS_ORIGINS`: Your frontend URL(s)
- `APP_NAME`, `API_TITLE`, `API_DESCRIPTION`: Customize as needed

**Optional Settings:**
- `DB_IDENTITY_CLIENT_ID`: Only needed if using user-assigned managed identity
- `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`: Adjust based on expected load
- `LOG_LEVEL`: Adjust logging verbosity as needed

### 2. Deploy Using PowerShell Script

```powershell
# Deploy to development
.\deploy-env-vars.ps1 -Environment dev -AppName your-app-name -ResourceGroup your-rg

# Deploy to staging
.\deploy-env-vars.ps1 -Environment staging -AppName your-app-name -ResourceGroup your-rg

# Deploy to production
.\deploy-env-vars.ps1 -Environment production -AppName your-app-name -ResourceGroup your-rg

# Dry run (see what would change without applying)
.\deploy-env-vars.ps1 -Environment production -AppName your-app-name -ResourceGroup your-rg -DryRun

# Force update all variables (even existing ones)
.\deploy-env-vars.ps1 -Environment production -AppName your-app-name -ResourceGroup your-rg -ForceUpdate
```

### 3. Use in GitHub Actions

```yaml
- name: Deploy Environment Variables
  run: |
    ./backend-api/deployment/deploy-env-vars.ps1 `
      -Environment production `
      -AppName ${{ secrets.AZURE_APP_NAME }} `
      -ResourceGroup ${{ secrets.AZURE_RESOURCE_GROUP }}
  shell: pwsh
```

## Environment Variables Reference

### Application Settings
| Variable | Type | Description |
|----------|------|-------------|
| `ENVIRONMENT` | string | Deployment environment (development/testing/production) |
| `DEBUG` | boolean | Enable debug mode (True/False) |
| `LOG_LEVEL` | string | Logging level (DEBUG/INFO/WARNING/ERROR/CRITICAL) |
| `API_VERSION` | string | API version (v1, v2, etc.) |
| `APP_NAME` | string | Application name |
| `API_TITLE` | string | API title for documentation |
| `API_DESCRIPTION` | string | API description for documentation |

### Server Settings
| Variable | Type | Description |
|----------|------|-------------|
| `HOST` | string | Server bind address (0.0.0.0 for Azure) |
| `PORT` | integer | Server port (8000 default) |

### CORS Settings
| Variable | Type | Description |
|----------|------|-------------|
| `CORS_ORIGINS` | JSON array | Allowed origin domains |
| `CORS_ALLOW_CREDENTIALS` | boolean | Allow cookies in CORS requests |
| `CORS_ALLOW_METHODS` | JSON array | Allowed HTTP methods |
| `CORS_ALLOW_HEADERS` | JSON array | Allowed HTTP headers |

### Database Settings (Azure SQL with Managed Identity)
| Variable | Type | Description |
|----------|------|-------------|
| `DB_SERVER` | string | SQL Server FQDN (e.g., server.database.windows.net) |
| `DB_NAME` | string | Database name |
| `DB_IDENTITY_CLIENT_ID` | string | User-assigned managed identity client ID (optional) |
| `DB_POOL_SIZE` | integer | Connection pool minimum size |
| `DB_MAX_OVERFLOW` | integer | Maximum additional connections |
| `DB_POOL_RECYCLE` | integer | Recycle connections after N seconds |
| `DB_CONNECT_TIMEOUT` | integer | Connection timeout in seconds |
| `DB_ECHO_SQL` | boolean | Log all SQL statements (debugging) |

## Security Notes

### Secrets Management

⚠️ **Do NOT store sensitive values in these JSON files:**
- Database passwords
- API keys
- Connection strings with embedded credentials
- Access tokens

For managed identity authentication, you don't need passwords or connection strings. The App Service authenticates using its managed identity.

### Git Repository

✅ **Safe to commit:**
- These configuration files (they contain no secrets)
- Environment structure and non-sensitive defaults

❌ **Never commit:**
- Files with actual production URLs if they need to remain private
- Any files with credentials or secrets

### Using GitHub Secrets

For GitHub Actions, store sensitive deployment details as secrets:

```yaml
env:
  AZURE_APP_NAME: ${{ secrets.AZURE_APP_NAME }}
  AZURE_RESOURCE_GROUP: ${{ secrets.AZURE_RESOURCE_GROUP }}
```

## Deployment Script Features

### Smart Updates
- **Only creates missing variables** by default
- Preserves existing values unless `-ForceUpdate` is used
- Shows summary of changes before applying

### Safety Features
- **Dry run mode** (`-DryRun`) to preview changes
- **Masks sensitive values** in output (passwords, secrets, keys)
- **Validates** Azure authentication and resource existence
- **Clear error messages** if something fails

### Azure Integration
- Uses Azure CLI for reliable deployment
- Automatically restarts App Service after changes
- Supports all Azure App Service configurations

## Best Practices

1. **Version Control**
   - Commit configuration files to git
   - Track changes with meaningful commit messages
   - Use pull requests for production changes

2. **Environment Separation**
   - Use separate App Services for dev/staging/production
   - Use separate databases for each environment
   - Test in staging before deploying to production

3. **Deployment Process**
   - Always run with `-DryRun` first
   - Review changes before applying
   - Deploy to dev → staging → production in sequence
   - Verify application health after deployment

4. **Maintenance**
   - Update `lastUpdated` field when making changes
   - Document changes in `notes` array
   - Review and update configurations regularly
   - Remove obsolete variables

## Troubleshooting

### Configuration File Not Found
```
Configuration file not found: .\env-configs\env.dev.json
```
**Solution**: Ensure you're running the script from the `deployment` directory or provide full path to config file.

### Not Logged In to Azure
```
Not logged in to Azure. Please run: az login
```
**Solution**: Run `az login` and authenticate with your Azure account.

### App Service Not Found
```
App Service 'myapp' not found in resource group 'myrg'
```
**Solution**: Verify the App Service name and resource group are correct.

### Variable Already Exists
If you need to update existing variables, use the `-ForceUpdate` flag:
```powershell
.\deploy-env-vars.ps1 -Environment dev -AppName myapp -ResourceGroup myrg -ForceUpdate
```

## Related Documentation

- [ENV_REFERENCE.md](../../ENV_REFERENCE.md) - Complete environment variables reference
- [AZURE_APPSERVICE_CONFIGURATION.md](../../specifications/002-azure-sql-support/AZURE_APPSERVICE_CONFIGURATION.md) - Azure App Service setup guide
- [DEPLOYMENT_CHECKLIST.md](../DEPLOYMENT_CHECKLIST.md) - Full deployment checklist

---

**Last Updated**: December 10, 2025  
**Maintained By**: Development Team
