# PlanProof - Error Troubleshooting Guide

## ✅ IMPROVEMENTS MADE

### 1. Better Error Tracking
- **Summary File**: Each run now creates `runs/<run_id>/outputs/summary.json` with complete details
- **Error Step Identification**: Errors now show which step failed (ingestion, extraction, validation, llm_gate)
- **Detailed Error Info**: Error type, timestamp, and step are captured

### 2. Improved UI Status Page
- **Error Display**: Shows all errors with expandable details
- **Metrics Dashboard**: Shows total documents, processed, errors, and LLM calls
- **Download Options**: Download summary and error logs
- **Real-time Visibility**: Auto-refresh shows current status

### 3. Diagnostic Tool
- **Run diagnose_run.py**: Quick script to analyze any run
- **Usage**: `python diagnose_run.py <run_id>`
- **Shows**: Missing files, error details, progress summary

## 🔍 HOW TO DEBUG ISSUES

### Quick Check
```bash
python diagnose_run.py <run_id>
```

### Check Summary
```bash
cat runs/<run_id>/outputs/summary.json
```

### Check Individual Errors
```bash
cat runs/<run_id>/outputs/error_*.txt
```

## 📊 WHAT "VALIDATION MISSING" MEANS

When you see "1 validation missing":
- ✅ The PDF was uploaded successfully
- ✅ Azure Document Intelligence extracted the text
- ❌ The validation step failed or is stuck

**Common Causes:**
1. **Database Error**: ValidationCheck trying to insert invalid data
2. **LLM Timeout**: If LLM gate is triggered but takes too long
3. **Consistency Check Error**: Code bug in consistency validation (like the document_id issue we fixed)

## 💰 SAVING AZURE CREDITS

### Disable Features During Testing
Edit `.env` file:
```env
# Disable LLM to save credits
ENABLE_LLM_GATE=false

# Disable database writes if having DB issues
ENABLE_DB_WRITES=false
```

### Test with Small Files First
- Upload 1 small PDF (< 5 pages) first
- Check it completes successfully
- Then try larger batches

### Check Before Uploading
```bash
# Verify Azure services are needed
python -c "from planproof.config import get_settings; s = get_settings(); print(f'LLM: {s.enable_llm_gate}, DB: {s.enable_db_writes}')"
```

## 🎯 CURRENT ISSUE IN RUN 19

**Status**: Document 83 validation is stuck/failed
**Reason**: Likely the consistency validation bug we just fixed
**Solution**: Try a new run now with the fixes applied

## 📝 BEST PRACTICE WORKFLOW

1. **Start Small**: Test with 1 document first
2. **Check Status Page**: Use auto-refresh to monitor
3. **Download Summary**: Get `summary.json` for analysis
4. **Review Errors**: Check error files for details
5. **Disable LLM**: Set `ENABLE_LLM_GATE=false` for testing

## 🚀 NEXT RUN

The UI is now running with:
- ✅ Fixed ValidationCheck database issues
- ✅ Fixed consistency validation document_id bug
- ✅ Better error display and tracking
- ✅ Summary file generation

Go to http://localhost:8504 and try uploading again!
