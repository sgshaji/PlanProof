#!/usr/bin/env python3
"""
Run FastAPI server for PlanProof API.

Usage:
    python run_api.py

    Development mode (auto-reload enabled):
        ENVIRONMENT=development python run_api.py

    Production mode (auto-reload disabled):
        ENVIRONMENT=production python run_api.py

API will be available at:
    - http://localhost:8000
    - API Docs: http://localhost:8000/api/docs
    - ReDoc: http://localhost:8000/api/redoc
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import uvicorn

if __name__ == "__main__":
    # Determine reload based on environment
    # Only enable auto-reload in development mode
    environment = os.getenv("ENVIRONMENT", "production").lower()
    enable_reload = environment == "development"

    if enable_reload:
        print("[DEV] Running in DEVELOPMENT mode with auto-reload enabled")
    else:
        print("[PROD] Running in PRODUCTION mode with auto-reload disabled")

    uvicorn.run(
        "planproof.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=enable_reload,
        log_level="info"
    )
