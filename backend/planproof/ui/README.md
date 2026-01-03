# PlanProof UI

Streamlit-based user interface for validation officers.

## Quick Start

### Run the UI

```bash
streamlit run planproof/ui/main.py
```

The UI will open in your browser at `http://localhost:8501`

## Pages

### 1. Upload
- Enter application reference
- Upload one or more PDF files
- Click "Process Documents" to start

### 2. Status
- View processing progress
- See current file being processed
- Auto-refreshes every 2 seconds
- Shows errors if processing fails

### 3. Results
- View validation summary (PASS/FAIL/NEEDS_REVIEW counts)
- Browse validation findings with evidence
- Filter by status and severity
- Export results as JSON or ZIP bundle

## File Structure

```
planproof/ui/
├── main.py              # Streamlit app entry point
├── run_orchestrator.py  # Backend orchestration logic
└── pages/
    ├── upload.py        # Upload page
    ├── status.py        # Status page
    └── results.py       # Results page
```

## Run Storage

Runs are stored in:
- `./runs/<run_id>/inputs/` - Uploaded PDF files
- `./runs/<run_id>/outputs/` - Processing artifacts (extraction, validation, LLM notes, errors)

## Session State

The UI uses Streamlit session state to track:
- `run_id`: Current run ID
- `stage`: Current stage (upload/status/results)
- `outputs`: Processing outputs

