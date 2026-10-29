#!/bin/bash
# Azure App Service startup script for Python FastAPI application
# Run from Package deployment mode

echo "=== Masjid Connect Backend - Azure Startup Script (Run from Package) ==="
echo "Python version: $(python --version)"
echo "Working directory: $(pwd)"
echo "Environment: ${ENVIRONMENT:-not set}"
echo "PYTHONPATH: ${PYTHONPATH:-not set}"

# List directory contents
echo "Directory contents:"
ls -la

# Verify src module is accessible
echo "Verifying src module..."
python -c "import sys; print('Python path:', sys.path)" || true
python -c "import src; print(f'src module found at: {src.__file__}')" || echo "WARNING: src module not found!"

# Start the application with Gunicorn
echo "Starting Gunicorn server..."
exec python -m gunicorn \
    --bind 0.0.0.0:${PORT:-8000} \
    --worker-class uvicorn.workers.UvicornWorker \
    --workers ${WORKERS:-4} \
    --timeout ${TIMEOUT:-600} \
    --access-logfile '-' \
    --error-logfile '-' \
    --log-level ${LOG_LEVEL:-info} \
    --preload \
    src.main:app
