#!/bin/bash
# Startup script for Masjid Connect API on Azure App Service
# 
# This script configures and starts the FastAPI application using Gunicorn
# with Uvicorn workers for production deployment on Azure.
#
# Environment:
# - Uses Gunicorn as the ASGI server
# - Configures 4 worker processes (adjust based on CPU cores)
# - Listens on 0.0.0.0:8000 as required by Azure App Service
# - Enables graceful timeout for long-running requests
# - Sets up proper logging and worker class

echo "=== Masjid Connect API - Startup Script ==="
echo "Start time: $(date)"

# Get the directory where this script is located (works during Oryx build in /tmp)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo "Script directory: $SCRIPT_DIR"

# Change to the directory where the app code is
cd "$SCRIPT_DIR" || { echo "Failed to change to script directory"; exit 1; }

# Create log directory if it doesn't exist (use absolute path for Azure)
mkdir -p /home/site/wwwroot/logs
mkdir -p logs  # Also create relative path as backup

# Debug: Show environment and directory info
echo "Current directory: $(pwd)"
echo "Python path: $(which python)"
echo "Python version: $(python --version)"

# Oryx sets environment variables for the virtual environment
# Check for Oryx environment variables first
if [ -n "$VIRTUAL_ENV" ]; then
    echo "Using Oryx-configured virtual environment: $VIRTUAL_ENV"
    echo "Virtual environment already activated by Oryx"
else
    echo "No VIRTUAL_ENV set, searching for virtual environment..."
    # Search for virtual environment in common locations
    for venv_dir in antenv3.13 antenv __oryx_prod_venv .venv venv; do
        if [ -d "$venv_dir" ] && [ -f "$venv_dir/bin/activate" ]; then
            echo "Found virtual environment: $venv_dir"
            source $venv_dir/bin/activate

            echo "Using virtual environment: $venv_dir - $VIRTUAL_ENV"
            break
        fi
    done
    
    if [ -z "$VIRTUAL_ENV" ]; then
        echo "Warning: No virtual environment found, using system Python"

        echo "Creating a new virtual environment..."
        python -m venv antenv
        source antenv/bin/activate

        echo "Installing dependencies..."
        pip install --upgrade pip
        pip install -r requirements.txt
    fi
fi

# Set environment variables for production if not already set
export ENVIRONMENT=${ENVIRONMENT:-production}
export DEBUG=${DEBUG:-False}
export LOG_LEVEL=${LOG_LEVEL:-INFO}

# Log configuration
echo "Configuration:"
echo "  ENVIRONMENT: $ENVIRONMENT"
echo "  DEBUG: $DEBUG"
echo "  LOG_LEVEL: $LOG_LEVEL"
echo "  HOST: 0.0.0.0"
echo "  PORT: 8000"

# Start Gunicorn with Uvicorn workers
# Workers = (2 × CPU cores) + 1, typically 4-8 for App Service B1/B2
# Timeout is set to 60 seconds, increase if needed for long-running requests
echo ""

# Check if uvicorn worker is available, otherwise use uvicorn directly
# if python -c "from uvicorn.workers import UvicornWorker" 2>/dev/null; then
#     echo "Starting Gunicorn with Uvicorn workers..."
#     exec gunicorn \
#       --workers 4 \
#       --worker-class uvicorn.workers.UvicornWorker \
#       --bind 0.0.0.0:8000 \
#       --timeout 120 \
#       --access-logfile - \
#       --error-logfile - \
#       --log-level info \
#       --graceful-timeout 30 \
#       src.main:app
# else
#     echo "Starting Uvicorn directly..."
#     exec uvicorn src.main:app \
#         --host 0.0.0.0 \
#         --port 8000 \
#         --workers 4 \
#         --timeout-keep-alive 120 \
#         --access-log \
#         --log-level info
# fi

# Verify Python can import the app
echo "Verifying app can be imported..."
python -c "from src.main import app; print('✓ App imported successfully')" || {
    echo "ERROR: Failed to import app"
    echo "Attempting to show import error:"
    python -c "from src.main import app" 2>&1
    exit 1
}

# Start Uvicorn as Python module (more reliable than shell command)
# Using single worker for easier debugging
echo "Starting Uvicorn server..."
exec python -m uvicorn src.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level debug \
    --access-log \
    --use-colors
