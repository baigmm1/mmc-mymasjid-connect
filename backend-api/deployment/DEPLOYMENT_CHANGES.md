# Deployment Changes: ORYX to Run from Package

## Summary of Changes

All deployment configuration has been updated from **ORYX Build** mode to **Run from Package** mode for faster, more reliable deployments.

---

## Files Modified

### 1. `.deployment`

**Changed:**

```ini
# OLD (ORYX)
SCM_DO_BUILD_DURING_DEPLOYMENT=true
WEBSITE_RUN_FROM_PACKAGE=0

# NEW (Run from Package)
SCM_DO_BUILD_DURING_DEPLOYMENT=false
WEBSITE_RUN_FROM_PACKAGE=1
```

### 2. `startup.txt`

**Changed:**

```bash
# OLD
gunicorn --bind 0.0.0.0:8000 ...

# NEW
python -m gunicorn --bind 0.0.0.0:8000 ...
```

**Reason:** `python -m` ensures correct module resolution in packaged deployment

### 3. `startup-azure.sh`

**Changed:**

- Removed package installation step (`pip install -e .`)
- Added diagnostics for troubleshooting
- Uses `python -m gunicorn` instead of direct `gunicorn`

**Reason:** Package is already deployed, no need to install

### 4. `.github/workflows/develop_mmc-api-app.yml`

**Changed:**

- Removed ORYX build configuration
- Added zip package creation step
- Changed to `WEBSITE_RUN_FROM_PACKAGE=1`
- Changed startup file to `startup.txt`
- Uses `az webapp deployment source config-zip` for deployment

### 5. `deploy-azure.ps1`

**Changed:**

- Step 4: Renamed from "Configure ORYX Build" to "Configure Run from Package"
- Settings changed to `WEBSITE_RUN_FROM_PACKAGE=1`
- Step 5: Changed startup file from `startup-azure.sh` to `startup.txt`
- Step 8: Added zip package creation
- Deployment method changed to `az webapp deployment source config-zip`

### 6. `deploy-azure.sh`

**Same changes as deploy-azure.ps1 for bash**

### 7. `DEPLOYMENT_SETUP_SUMMARY.md`

**Updated:**

- Changed from "ORYX Deployment" to "Run from Package Deployment"
- Updated problem statement and solution overview
- Updated all configuration examples
- Added Run from Package vs ORYX comparison table
- Updated troubleshooting for Run from Package

### 8. `DEPLOYMENT_CHECKLIST.md`

**Updated:**

- Changed startup command reference to `startup.txt`
- Changed settings from ORYX to Run from Package
- Updated verification steps
- Updated troubleshooting steps
- Added Run from Package note at bottom

---

## New Files Created

### 1. `RUN_FROM_PACKAGE_GUIDE.md`

**Purpose:** Quick reference guide for Run from Package deployment

**Contains:**

- Overview and benefits
- Configuration summary
- All deployment methods
- Comparison table
- Troubleshooting
- Verification checklist
- Quick reference commands

---

## Key Configuration Changes

### Azure App Service Settings

**General Settings:**

- Startup Command: `startup.txt` (was: `startup-azure.sh`)

**Application Settings:**

```bash
# CHANGED
SCM_DO_BUILD_DURING_DEPLOYMENT=false  # was: true
WEBSITE_RUN_FROM_PACKAGE=1            # was: 0

# REMOVED
ENABLE_ORYX_BUILD                     # no longer needed
```

---

## Deployment Process Changes

### OLD (ORYX Build):

1. Push code to Azure
2. Azure builds application using ORYX
3. ORYX installs dependencies
4. Startup script installs package (`pip install -e .`)
5. Application starts

### NEW (Run from Package):

1. Create zip package locally or in CI/CD
2. Exclude venv, tests, cache files
3. Deploy zip to Azure using `az webapp deployment source config-zip`
4. Azure mounts package as read-only
5. Application starts immediately (no build/install)

---

## Benefits of Run from Package

✅ **Faster Deployments**

- No build time on Azure
- Pre-built packages deploy in seconds

✅ **Faster Startup**

- No `pip install` on startup
- Dependencies already in package

✅ **Consistent**

- Same package tested in CI/CD
- Identical across all environments

✅ **Secure**

- Read-only file system
- Immutable deployments

✅ **Reliable**

- No build failures on Azure
- Predictable deployments

---

## Migration Steps

If you have existing ORYX deployments, follow these steps:

### 1. Update Azure Settings

```bash
az webapp config appsettings set \
  --name your-app \
  --resource-group your-rg \
  --settings \
    SCM_DO_BUILD_DURING_DEPLOYMENT=false \
    WEBSITE_RUN_FROM_PACKAGE=1

az webapp config set \
  --name your-app \
  --resource-group your-rg \
  --startup-file "startup.txt"
```

### 2. Create and Deploy Package

```bash
# Create package
cd backend-api
zip -r deploy.zip . -x "*.git*" "*venv/*" "*__pycache__/*" "*.pytest_cache/*" "*tests/*"

# Deploy
az webapp deployment source config-zip \
  --resource-group your-rg \
  --name your-app \
  --src deploy.zip
```

### 3. Verify

```bash
# Check logs
az webapp log tail --name your-app --resource-group your-rg

# Test endpoints
curl https://your-app.azurewebsites.net/health
```

---

## Important Notes

### Read-Only File System

Run from Package uses a **read-only file system** for the application directory.

**If you need to write files:**

- Use `/home/data` for persistent storage
- Use `/tmp` for temporary files
- Don't try to write to `/home/site/wwwroot`

### Package Size

- Maximum package size: 2GB
- Exclude venv, tests, logs, cache files
- Use `.dockerignore` to define exclusions

### Startup Command

Always use `python -m gunicorn` instead of direct `gunicorn`:

```bash
# CORRECT
python -m gunicorn src.main:app

# INCORRECT (may fail with module errors)
gunicorn src.main:app
```

---

## Troubleshooting

### Issue: ModuleNotFoundError

**Solution:** Ensure startup.txt uses `python -m gunicorn`

### Issue: Can't write files

**Expected!** Use `/home/data` or `/tmp` instead

### Issue: Old code still running

**Solution:** Package is cached. Create new package and redeploy

### Issue: Deployment fails

**Check:**

- Package size < 2GB
- Zip format (not tar.gz)
- Kudu deployment logs
- File permissions

---

## Quick Reference

### View Deployment Logs (Kudu)

```
https://your-app.scm.azurewebsites.net/
Navigate to: Deployments → View Log
```

### Check Package Contents

```bash
unzip -l deploy.zip | head -20
```

### Verify Settings

```bash
az webapp config show --name your-app --resource-group your-rg
```

### Restart After Config Change

```bash
az webapp restart --name your-app --resource-group your-rg
```

---

## Next Steps

1. ✅ Review `RUN_FROM_PACKAGE_GUIDE.md` for detailed guide
2. ✅ Use `deploy-azure.ps1` or `deploy-azure.sh` for automated deployment
3. ✅ Configure GitHub Actions for CI/CD (already updated in workflow)
4. ✅ Follow `DEPLOYMENT_CHECKLIST.md` for verification
5. ✅ Monitor application logs after deployment

---

## Support

For issues or questions:

1. Check `RUN_FROM_PACKAGE_GUIDE.md` troubleshooting section
2. Review application logs: `az webapp log tail`
3. Check Kudu deployment logs
4. Verify package contents
5. Review Azure App Service settings

---

**Deployment mode changed to Run from Package for better performance and reliability!** 🚀
