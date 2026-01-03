#!/bin/bash
# Start PlanProof UI

echo "Starting PlanProof UI..."
echo ""

# Set PYTHONPATH
export PYTHONPATH="$PWD"

# Start Streamlit
streamlit run planproof/ui/main.py

