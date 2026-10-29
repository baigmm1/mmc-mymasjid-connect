# Run from Package Deployment Setup - Summary

## Problem Statement

When deploying to Azure App Service, the application was failing because:

1. Environment variables from Azure App Service weren't being picked up
2. The `src` module wasn't discoverable at runtime
3. New endpoints were returning 404 errors
4. Deployment was slow with ORYX build process

## Solution Overview

This solution uses **Run from Package** deployment which:

1. Pre-packages the application locally or in CI/CD
2. Deploys a complete zip file to Azure
3. Runs directly from the immutable package (read-only)
4. Ensures consistent deployments across environments
5. Faster startup times and better performance

---

## Files Created/Modified

### 1. `setup.py` ⭐ CRITICAL

**Purpose:** Ensures the `src` package structure is proper for Python imports.

**Key Features:**

- Uses `find_packages()` to discover the `src` module
- Includes proper package metadata
- Required even for Run from Package to ensure proper Python package structure

### 2. `.deployment`

**Purpose:** Configures deployment behavior for Azure.

**Settings:**

```ini
SCM_DO_BUILD_DURING_DEPLOYMENT=false
WEBSITE_RUN_FROM_PACKAGE=1
```

**Key Points:**

- `SCM_DO_BUILD_DURING_DEPLOYMENT=false` - Disables ORYX build
- `WEBSITE_RUN_FROM_PACKAGE=1` - Enables Run from Package mode

### 3. `startup.txt` ⭐ RECOMMENDED

**Purpose:** Basic startup command for Gunicorn.

**Command:**

```bash
gunicorn --bind 0.0.0.0:8000 --worker-class uvicorn.workers.UvicornWorker --workers 4 --timeout 600 --access-logfile '-' --error-logfile '-' src.main:app
```

### 4. `startup-azure.sh` (Recommended Option) ⭐

**Purpose:** Advanced startup script that installs the package and verifies setup before starting.

**What it does:**

1. Installs the package: `pip install -e .`
2. Verifies the `src` module is discoverable
3. Lists installed packages for debugging
4. Starts Gunicorn with proper configuration

**Why it's better:** Ensures the package is installed fresh on every startup, preventing stale code issues.

### 5. `src/config.py` (Modified)

**Purpose:** Updated to prioritize Azure environment variables over `.env` files.

**Change:**

```python
# Only load .env in non-production environments
env_file = ".env" if os.getenv("ENVIRONMENT", "development") != "production" else None
```

**Why:** In production (Azure), environment variables should come from App Service configuration, not `.env` files.

### 6. `.env.production.example`

**Purpose:** Documents all required environment variables for Azure deployment.

**Use:** Reference this when configuring Azure App Service → Configuration → Application settings.

### 7. `deploy-azure.sh` and `deploy-azure.ps1`

**Purpose:** Automated deployment scripts for bash and PowerShell.

**What they do:**

1. Create App Service Plan and Web App (if needed)
2. Configure ORYX build settings
3. Set startup command to `startup-azure.sh`
4. Configure application environment variables
5. Enable managed identity
6. Deploy the application
7. Verify endpoints are working

### 8. `specifications/deployment/ORYX_DEPLOYMENT.md`

**Purpose:** Comprehensive deployment guide with troubleshooting.

**Sections:**

- Critical files explanation
- Azure App Service settings
- Deployment steps (3 options)
- Troubleshooting common issues
- Verification checklist
- Useful commands

### 9. `.github/workflows/develop_mmc-api-app.yml` (Modified)

**Purpose:** Updated CI/CD workflow to use new startup script.

**Changes:**

- Updated startup file to `startup-azure.sh`
- Added `WEBSITE_RUN_FROM_PACKAGE=0` setting
- Ensured ORYX build is enabled

---

## How to Deploy

### Option 1: Automated Deployment (Recommended)

#### For Linux/Mac (bash):

```bash
cd backend-api
chmod +x deploy-azure.sh
./deploy-azure.sh
```

#### For Windows (PowerShell):

```powershell
cd backend-api
.\deploy-azure.ps1
```

**Important:** Edit the script first to update these variables:

- `RESOURCE_GROUP`
- `APP_NAME`
- `LOCATION`
- Database settings (DB_SERVER, DB_NAME)
- CORS_ORIGINS

### Option 2: GitHub Actions (CI/CD)

The workflow `.github/workflows/develop_mmc-api-app.yml` is already configured:

1. Push to the `develop` branch
2. GitHub Actions will automatically:
   - Build the application
   - Configure ORYX settings
   - Deploy to Azure App Service
   - Start the application

### Option 3: Manual Azure CLI

See `specifications/deployment/ORYX_DEPLOYMENT.md` for step-by-step Azure CLI commands.

### Option 4: VS Code Azure Extension

1. Install "Azure App Service" extension
2. Right-click on `backend-api` folder
3. Select "Deploy to Web App..."
4. Follow the prompts

---

## Required Azure Configuration

After deployment, configure these in **Azure Portal → App Service → Configuration → Application settings**:

### Critical Settings:

```bash
ENVIRONMENT=production
DB_SERVER=your-server.database.windows.net
DB_NAME=masjiddb
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
API_VERSION=1.0.0
LOG_LEVEL=INFO
PORT=8000
WORKERS=4
TIMEOUT=600
```

### ORYX Settings (Azure Portal → Configuration → General settings):

```bash
SCM_DO_BUILD_DURING_DEPLOYMENT=true
WEBSITE_RUN_FROM_PACKAGE=0
ENABLE_ORYX_BUILD=true
```

### Startup Command (Azure Portal → Configuration → General settings):

```bash
startup-azure.sh
```

**See `.env.production.example` for complete list of variables.**

---

## Verification Steps

After deployment:

### 1. Check Root Endpoint

```bash
curl https://your-app.azurewebsites.net/
```

Expected response:

```json
{
  "service": "Masjid Connect API",
  "version": "1.0.0",
  "environment": "production",
  "status": "running"
}
```

### 2. Check Health Endpoint

```bash
curl https://your-app.azurewebsites.net/health
```

Expected: `200 OK`

### 3. Check API Documentation

Open: `https://your-app.azurewebsites.net/docs`

Should show all endpoints including newly added ones.

### 4. Check Logs

```bash
az webapp log tail --name your-app-name --resource-group your-rg
```

Should see:

```
Starting Masjid Connect API v1.0.0
Environment: production
Debug mode: False
```

### 5. Verify New Endpoints

Test your new endpoints:

```bash
curl https://your-app.azurewebsites.net/api/v1/your-new-endpoint
```

---

## Troubleshooting

### Issue: New endpoints return 404

**Solution:**

1. Verify router is registered in `src/main.py`:
   ```python
   app.include_router(your_router.router, prefix="/api/v1")
   ```
2. Check `/docs` to see if endpoint appears
3. SSH into container and run:
   ```bash
   pip uninstall -y masjidconnect-backend
   pip install -e .
   ```
4. Restart App Service

### Issue: Environment variables not picked up

**Solution:**

1. Check Azure Portal → Configuration → Application settings
2. Ensure `ENVIRONMENT=production` is set
3. Restart App Service after adding variables
4. Verify in logs:
   ```bash
   az webapp log tail --name your-app --resource-group your-rg
   ```

### Issue: ModuleNotFoundError: No module named 'src'

**Solution:**

1. Ensure `setup.py` exists in backend-api root
2. Update startup command to `startup-azure.sh` (not `startup.txt`)
3. Verify ORYX build logs show package installation
4. SSH into container and verify:
   ```bash
   python -c "import src; print(src.__file__)"
   ```

### Issue: Application won't start (timeout)

**Solution:**

1. Check startup logs in Kudu: `https://your-app.scm.azurewebsites.net`
2. Increase timeout: `--timeout 600` in startup command
3. Check for blocking operations in `startup_event()`
4. Scale up to B2 or higher SKU

**See `specifications/deployment/ORYX_DEPLOYMENT.md` for more troubleshooting scenarios.**

---

## Key Takeaways

### ✅ DO:

- Use `setup.py` to make your package installable
- Use `startup-azure.sh` that runs `pip install -e .`
- Set `SCM_DO_BUILD_DURING_DEPLOYMENT=true`
- Set `WEBSITE_RUN_FROM_PACKAGE=0`
- Configure environment variables in Azure Portal, not `.env`
- Use Managed Identity for database access
- Verify deployment with `/health` and `/docs` endpoints

### ❌ DON'T:

- Don't rely on `.env` files in production
- Don't skip `pip install -e .` in startup script
- Don't use `startup.txt` without package installation
- Don't set `WEBSITE_RUN_FROM_PACKAGE=1` (prevents writes)
- Don't skip ORYX build configuration
- Don't forget to register new routers in `main.py`

---

## Next Steps

1. **Deploy:** Run `deploy-azure.ps1` or `deploy-azure.sh`
2. **Configure Database:** Follow `AZURE_APPSERVICE_CONFIGURATION.md` for managed identity setup
3. **Test Endpoints:** Verify all endpoints work including new ones
4. **Set Up Monitoring:** Configure Application Insights
5. **Configure Domain:** Set up custom domain and SSL certificate
6. **Enable CI/CD:** Push to GitHub to trigger automatic deployments

---

## Support Documents

- **`ORYX_DEPLOYMENT.md`** - Comprehensive deployment guide
- **`AZURE_APPSERVICE_CONFIGURATION.md`** - Managed identity and database setup
- **`.env.production.example`** - Required environment variables
- **`deploy-azure.ps1`** / **`deploy-azure.sh`** - Automated deployment scripts

---

## Questions?

If you encounter issues:

1. Check `ORYX_DEPLOYMENT.md` troubleshooting section
2. View logs: `az webapp log tail --name your-app --resource-group your-rg`
3. SSH into container: `az webapp ssh --name your-app --resource-group your-rg`
4. Check ORYX build logs in Kudu console

**Remember:** The key to successful deployment is ensuring the `src` package is properly installed via `pip install -e .` in the startup script.
