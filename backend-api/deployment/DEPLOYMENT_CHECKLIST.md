# Azure Deployment Quick Checklist

## Pre-Deployment Checklist

- [ ] **setup.py exists** in backend-api root directory
- [ ] **startup.txt exists** with gunicorn command
- [ ] **.deployment file exists** with Run from Package settings
- [ ] **requirements.txt** includes all dependencies including `gunicorn`
- [ ] **src/config.py** prioritizes Azure env vars (env_file = None in production)
- [ ] **All routers registered** in src/main.py `create_app()` function
- [ ] **.dockerignore exists** to exclude venv, tests, etc. from package

## Azure Portal Configuration

### App Service → Configuration → General Settings

- [ ] **Stack**: Python
- [ ] **Python version**: 3.11 or higher
- [ ] **Startup Command**: `startup.txt`

### App Service → Configuration → Application Settings

#### Required Settings:

- [ ] `ENVIRONMENT=production`
- [ ] `DEBUG=false`
- [ ] `API_VERSION=1.0.0`
- [ ] `LOG_LEVEL=INFO`
- [ ] `PORT=8000`
- [ ] `WORKERS=4`
- [ ] `TIMEOUT=600`

#### Database Settings:

- [ ] `DB_SERVER=your-server.database.windows.net`
- [ ] `DB_NAME=masjiddb`
- [ ] `DB_POOL_SIZE=20`
- [ ] `DB_MAX_OVERFLOW=10`
- [ ] `DB_POOL_RECYCLE=3600`

#### Run from Package Settings:

- [ ] `SCM_DO_BUILD_DURING_DEPLOYMENT=false`
- [ ] `WEBSITE_RUN_FROM_PACKAGE=1`

#### CORS Settings:

- [ ] `CORS_ORIGINS=["https://yourdomain.com"]` (update with your domain)
- [ ] `CORS_ALLOW_CREDENTIALS=true`
- [ ] `CORS_ALLOW_METHODS=["GET","POST","PUT","DELETE","OPTIONS","PATCH"]`
- [ ] `CORS_ALLOW_HEADERS=["*"]`

### App Service → Identity

- [ ] **System-assigned managed identity**: On
- [ ] **Principal ID**: Copy for database configuration

## Deployment Options (Choose One)

### Option 1: PowerShell Script (Windows)

```powershell
cd backend-api
.\deploy-azure.ps1
```

- [ ] Updated script variables (RESOURCE_GROUP, APP_NAME, DB_SERVER)
- [ ] Script executed successfully
- [ ] No errors in output

### Option 2: Bash Script (Linux/Mac)

```bash
cd backend-api
chmod +x deploy-azure.sh
./deploy-azure.sh
```

- [ ] Updated script variables (RESOURCE_GROUP, APP_NAME, DB_SERVER)
- [ ] Script executed successfully
- [ ] No errors in output

### Option 3: GitHub Actions

- [ ] Pushed code to `develop` branch
- [ ] GitHub Actions workflow completed successfully
- [ ] Check Actions tab for build/deploy status

### Option 4: Azure CLI Manual

- [ ] Created deployment package (zip file)
- [ ] Configured Run from Package settings
- [ ] Deployed using `az webapp deployment source config-zip`
- [ ] All CLI commands executed successfully

## Database Configuration (If Using Azure SQL)

- [ ] **Managed Identity enabled** on App Service
- [ ] **SQL Server firewall** allows Azure services
- [ ] **Database user created** for managed identity:
  ```sql
  CREATE USER [app-name] FROM EXTERNAL PROVIDER;
  ALTER ROLE db_datareader ADD MEMBER [app-name];
  ALTER ROLE db_datawriter ADD MEMBER [app-name];
  ```
- [ ] **Connection tested** from App Service

## Post-Deployment Verification

### Basic Health Checks:

- [ ] **Root endpoint** returns app info:

  ```bash
  curl https://your-app.azurewebsites.net/
  ```

  Expected: JSON with service, version, environment, status

- [ ] **Health endpoint** returns 200 OK:

  ```bash
  curl https://your-app.azurewebsites.net/health
  ```

- [ ] **Database health** returns 200 OK (if database configured):

  ```bash
  curl https://your-app.azurewebsites.net/health/db
  ```

- [ ] **API documentation** accessible:
  ```
  https://your-app.azurewebsites.net/docs
  ```

### Endpoint Verification:

- [ ] **All existing endpoints** return expected responses
- [ ] **New endpoints** appear in /docs
- [ ] **New endpoints** return expected responses (not 404)
- [ ] **Sample API call** works as expected

### Log Verification:

- [ ] **View logs** using Azure CLI:
  ```bash
  az webapp log tail --name your-app --resource-group your-rg
  ```
- [ ] **Startup logs show**:

  - ✓ "=== Masjid Connect Backend - Azure Startup Script (Run from Package) ==="
  - ✓ "Working directory: /home/site/wwwroot"
  - ✓ "Environment: production"
  - ✓ "Starting Gunicorn server..."
  - ✓ "Starting Masjid Connect API v1.0.0"

- [ ] **No errors** in logs
- [ ] **No ModuleNotFoundError** in logs

## Troubleshooting (If Issues Found)

### If new endpoints return 404:

- [ ] Verified router registered in src/main.py
- [ ] Checked /docs shows the endpoint
- [ ] Recreated deployment package with latest code
- [ ] Redeployed package to Azure
- [ ] Restarted App Service

### If environment variables not picked up:

- [ ] Verified settings in Azure Portal → Configuration
- [ ] Restarted App Service
- [ ] Checked logs show correct ENVIRONMENT value
- [ ] Verified src/config.py not loading .env in production

### If "ModuleNotFoundError: No module named 'src'":

- [ ] Verified setup.py exists in package
- [ ] Verified startup command is "startup.txt"
- [ ] Checked startup command uses `python -m gunicorn`
- [ ] Verified package structure: `unzip -l deploy.zip`
- [ ] SSH and verified: `python -c "import src; print(src.__file__)"`

### If application won't start:

- [ ] Checked Kudu logs: https://your-app.scm.azurewebsites.net
- [ ] Increased timeout in startup command
- [ ] Scaled up to B2 or higher SKU
- [ ] Checked for blocking operations in startup_event()

## Monitoring & Maintenance

- [ ] **Application Insights** configured (optional)
- [ ] **Alert rules** set up for errors (optional)
- [ ] **Custom domain** configured (optional)
- [ ] **SSL certificate** configured (optional)
- [ ] **Backup strategy** in place
- [ ] **Deployment slots** configured for staging (optional)

## Security Review

- [ ] **Managed Identity** used for database (no passwords in config)
- [ ] **CORS origins** set to specific domains (not "\*")
- [ ] **DEBUG=false** in production
- [ ] **Firewall rules** configured on SQL Server
- [ ] **Network security** configured (VNet integration if needed)
- [ ] **Secrets** in Azure Key Vault (if applicable)
- [ ] **HTTPS only** enforced in App Service settings

## Documentation

- [ ] **Deployment documented** for team
- [ ] **Environment variables** documented
- [ ] **Database setup** documented
- [ ] **Rollback procedure** documented
- [ ] **Monitoring dashboard** shared with team

---

## Quick Commands Reference

### View Logs

```bash
az webapp log tail --name your-app --resource-group your-rg
```

### SSH into Container

```bash
az webapp ssh --name your-app --resource-group your-rg
```

### Restart App

```bash
az webapp restart --name your-app --resource-group your-rg
```

### Test Endpoints

```bash
curl https://your-app.azurewebsites.net/
curl https://your-app.azurewebsites.net/health
curl https://your-app.azurewebsites.net/health/db
curl https://your-app.azurewebsites.net/docs
```

### Download Logs

```bash
az webapp log download --name your-app --resource-group your-rg
```

---

## Support Resources

- **RUN_FROM_PACKAGE_GUIDE.md** - Run from Package deployment guide
- **DEPLOYMENT_SETUP_SUMMARY.md** - Complete setup guide
- **AZURE_APPSERVICE_CONFIGURATION.md** - Database and managed identity setup
- **.env.production.example** - Environment variable reference
- **deploy-azure.ps1** / **deploy-azure.sh** - Automated deployment scripts

---

**✅ Deployment Complete!** Check all boxes before considering deployment successful.

## Deployment Mode: Run from Package

- Faster deployments (pre-built package)
- Consistent across environments
- Read-only file system (secure)
- Recommended for production
