"""Pytest configuration for the research module.

Adds the PlanProof root directory to sys.path so that ``research.*`` imports
resolve when running::

    cd PlanProof && python -m pytest research/tests/ -v
"""

import os
import sys

# Add PlanProof root to sys.path for research.* imports
_planproof_root = os.path.dirname(os.path.dirname(__file__))
if _planproof_root not in sys.path:
    sys.path.insert(0, _planproof_root)
