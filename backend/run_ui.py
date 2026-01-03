#!/usr/bin/env python3
"""
Standalone script to run the PlanProof UI.
This ensures PYTHONPATH is set correctly.
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Now import and run streamlit
import streamlit.web.cli as stcli

if __name__ == "__main__":
    sys.argv = ["streamlit", "run", "planproof/ui/main.py"]
    stcli.main()

