@echo off
REM Start PlanProof UI
echo Starting PlanProof UI...
echo.

REM Change to script directory (project root)
cd /d "%~dp0"

REM Set PYTHONPATH to current directory
set PYTHONPATH=%CD%

echo PYTHONPATH is set to: %PYTHONPATH%
echo.
echo Starting Streamlit...
echo.

REM Start Streamlit
streamlit run planproof/ui/main.py

pause

