#!/usr/bin/env python3
"""
Run FastAPI server for PlanProof API.

Usage:
    python run_api.py

API will be available at:
    - http://localhost:8000
    - API Docs: http://localhost:8000/api/docs
    - ReDoc: http://localhost:8000/api/redoc
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "planproof.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes (development only)
        log_level="info"
    )
