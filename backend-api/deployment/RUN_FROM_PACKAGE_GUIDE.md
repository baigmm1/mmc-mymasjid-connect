# Run from Package Deployment Guide

## Overview

**Run from Package** is the recommended deployment method for Azure App Service Python applications. It deploys a pre-built zip package that runs in read-only mode, providing:

- ✅ Faster deployments (no build on Azure)
- ✅ Consistent packages across environments
- ✅ Faster startup times
- ✅ Immutable deployments
- ✅ Better security (read-only file system)

---

## Configuration Summary

### Azure App Service Settings

**Configuration → General Settings:**

- **Startup Command:** `startup.txt`

**Configuration → Application Settings:**

```bash
SCM_DO_BUILD_DURING_DEPLOYMENT=false
WEBSITE_RUN_FROM_PACKAGE=1
ENVIRONMENT=production
# ... other app settings
```

### Local Files

**`.deployment`:**

```ini
[config]
SCM_DO_BUILD_DURING_DEPLOYMENT=false
WEBSITE_RUN_FROM_PACKAGE=1
```

**`startup.txt`:**

```bash
python -m gunicorn --bind 0.0.0.0:8000 --worker-class uvicorn.workers.UvicornWorker --workers 4 --timeout 600 --access-logfile '-' --error-logfile '-' src.main:app
```

---

## Deployment Methods

### Method 1: PowerShell Script (Windows)

```powershell
cd backend-api
.\deploy-azure.ps1
```

**What it does:**

1. Creates infrastructure (if needed)
2. Configures Run from Package settings
3. Creates zip package excluding venv, tests, etc.
4. Deploys via `az webapp deployment source config-zip`
5. Verifies deployment

### Method 2: Bash Script (Linux/Mac)

```bash
cd backend-api
chmod +x deploy-azure.sh
./deploy-azure.sh
```

### Method 3: Manual Deployment

```bash
# 1. Create package
cd backend-api
zip -r deploy.zip . \
  -x "*.git*" \
  -x "*venv/*" \
  -x "*__pycache__/*" \
  -x "*.pytest_cache/*" \
  -x "*tests/*" \
  -x "*.log"

# 2. Configure Azure
az webapp config appsettings set \
  --name your-app \
  --resource-group your-rg \
  --settings SCM_DO_BUILD_DURING_DEPLOYMENT=false WEBSITE_RUN_FROM_PACKAGE=1

az webapp config set \
  --name your-app \
  --resource-group your-rg \
  --startup-file "startup.txt"

# 3. Deploy
az webapp deployment source config-zip \
  --resource-group your-rg \
  --name your-app \
  --src deploy.zip

# 4. Verify
curl https://your-app.azurewebsites.net/health
```

### Method 4: GitHub Actions ⭐ RECOMMENDED

Push to `develop` branch - workflow automatically:

1. Builds application
2. Creates zip package
3. Configures Run from Package
4. Deploys to Azure
5. Verifies deployment

---

## Key Differences: Run from Package vs ORYX

| Aspect           | Run from Package | ORYX Build  |
| ---------------- | ---------------- | ----------- |
| Build Location   | Local/CI         | Azure       |
| Deployment Speed | Fast             | Slower      |
| File System      | Read-only        | Read-write  |
| Startup Time     | Faster           | Slower      |
| Consistency      | High             | Variable    |
| Best For         | Production       | Development |

---

## Troubleshooting

### New endpoints return 404

1. Verify router registered in `src/main.py`
2. Recreate package with latest code
3. Redeploy

### ModuleNotFoundError: No module named 'src'

1. Check `setup.py` exists
2. Verify `src/__init__.py` exists
3. Use `python -m gunicorn` in startup command
4. Check package structure: `unzip -l deploy.zip`

### Can't write files

**Expected behavior!** File system is read-only.

- Use `/home/data` for persistent storage
- Use `/tmp` for temporary files

### Deployment fails

1. Check package size (<2GB)
2. Verify zip format (not tar.gz)
3. Check Kudu deployment logs
4. Review exclusion patterns

---

## Verification Checklist

After deployment:

- [ ] Root endpoint returns app info: `https://your-app.azurewebsites.net/`
- [ ] Health check passes: `https://your-app.azurewebsites.net/health`
- [ ] Database health passes: `https://your-app.azurewebsites.net/health/db`
- [ ] API docs accessible: `https://your-app.azurewebsites.net/docs`
- [ ] All new endpoints appear in docs
- [ ] Logs show "Environment: production"
- [ ] No module import errors in logs

---

## Best Practices

### ✅ DO:

- Build packages in CI/CD
- Exclude venv, tests, logs from package
- Use `python -m gunicorn` in startup
- Set `WEBSITE_RUN_FROM_PACKAGE=1`
- Version your packages
- Test package locally first

### ❌ DON'T:

- Don't try to write to app directory
- Don't include virtual environments
- Don't rely on `.env` files in production
- Don't use ORYX build in production
- Don't skip package structure validation

---

## Quick Reference Commands

```bash
# View logs
az webapp log tail --name your-app --resource-group your-rg

# SSH into container
az webapp ssh --name your-app --resource-group your-rg

# Restart app
az webapp restart --name your-app --resource-group your-rg

# Check package contents
unzip -l deploy.zip | head -20

# Test endpoints
curl https://your-app.azurewebsites.net/health
curl https://your-app.azurewebsites.net/health/db
```

---

## Related Documents

- **`DEPLOYMENT_CHECKLIST.md`** - Complete deployment checklist
- **`AZURE_APPSERVICE_CONFIGURATION.md`** - Managed identity setup
- **`.env.production.example`** - Environment variables reference
- **`deploy-azure.ps1`** / **`deploy-azure.sh`** - Deployment scripts

---

## Summary

Run from Package provides:

- 🚀 **Faster** deployments and startup
- 🎯 **Consistent** packages across environments
- 🔒 **Secure** read-only file system
- ✅ **Reliable** immutable deployments

**Recommended for all production deployments!**
