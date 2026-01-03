# Automatic Parent Application Discovery - Implementation Summary

## 🎯 Feature Overview

Implemented automatic discovery and linking of parent applications for modification/resubmission scenarios. The system now intelligently identifies when a new application is a modification of an existing one and automatically links them together.

## ✅ What Was Implemented

### 1. Database Search Methods (`planproof/db.py`)

Added two new methods to the `Database` class:

#### `find_applications_by_address(site_address, exclude_application_id)`
- Performs fuzzy matching (ILIKE) on site addresses
- Handles format variations (e.g., "123 Main St" vs "123 Main Street")
- Returns up to 10 most recent matches
- Excludes current application from results

#### `find_applications_by_postcode(postcode, exclude_application_id)`
- Searches for applications with matching postcode
- Normalizes postcode format (removes spaces, uppercase)
- Returns up to 10 most recent matches
- Excludes current application from results

### 2. Parent Discovery Service (`planproof/services/parent_discovery.py`)

Created comprehensive parent discovery logic using multiple strategies:

#### **Strategy 1: Reference Extraction (95% confidence)**
- Extracts parent application references from description
- Patterns recognized:
  - `APP-2024-001`, `APP/2024/001`
  - `PP-14469287`
  - `20240615/HOU`
- Searches database for exact reference match

#### **Strategy 2: Address Matching (90%+ confidence)**
- Uses fuzzy string matching (fuzzywuzzy library)
- Scores address similarity
- Auto-links if similarity ≥ 90%
- Handles typos and format differences

#### **Strategy 3: Postcode Matching (70% confidence)**
- Fallback when address unavailable
- Auto-links if single match found
- Returns multiple matches for manual selection

#### Functions Provided:

```python
def discover_parent_application(
    extracted_fields: Dict,
    current_application_id: Optional[int],
    db: Optional[Database]
) -> Tuple[Optional[int], float, str]:
    """
    Returns: (parent_submission_id, confidence, reason)
    """

def get_potential_parents(
    extracted_fields: Dict,
    current_application_id: Optional[int],
    db: Optional[Database]
) -> List[Dict]:
    """
    Returns list of potential parents for manual selection.
    """
```

### 3. Integration into Upload Flow (`planproof/api/routes/documents.py`)

Modified `_process_document_for_run()` function:

#### **Step 2.5: Auto-Discovery (NEW)**

After extraction, before validation:

1. **Calls `discover_parent_application()`** with extracted fields
2. **Auto-links if confidence ≥ 85%**:
   - Updates `Submission.parent_submission_id`
   - Logs discovery details
   - Enables delta computation in validation
3. **Logs medium-confidence matches (85% > confidence > 50%)**:
   - Suggests manual review
   - Can be presented to user for confirmation

#### **Key Logic:**

```python
# Step 2.5: Auto-discover parent application (if not already set)
if parent_submission_id is None and extraction.get("fields"):
    discovered_parent_id, confidence, reason = discover_parent_application(
        extracted_fields=extraction["fields"],
        current_application_id=application_id,
        db=db
    )
    
    if discovered_parent_id and confidence >= 0.85:
        # Auto-link with high confidence
        parent_submission_id = discovered_parent_id
        # Update submission record...
```

### 4. API Endpoint for Manual Selection

Added new endpoint: `POST /api/v1/documents/applications/find-parents`

**Purpose:** Get list of potential parents when auto-discovery returns multiple matches

**Parameters:**
- `site_address` (Form): Site address to search
- `postcode` (Form): UK postcode to search
- `application_id` (Form): Current application ID (to exclude)

**Returns:**
```json
[
  {
    "application_id": 123,
    "application_ref": "APP-2024-001",
    "site_address": "123 Main Street, Birmingham, B8 1BG",
    "postcode": "B8 1BG",
    "status": "approved",
    "created_at": "2024-06-15T10:30:00",
    "latest_submission_id": 456
  }
]
```

### 5. Dependencies Added

Updated `requirements.txt`:
- `fuzzywuzzy==0.18.0` - Fuzzy string matching
- `python-Levenshtein==0.25.0` - Faster string distance calculations

## 🔄 How It Works

### Example Workflow:

**1. User uploads documents for extension:**
```
Files: extension_plans.pdf, elevations.pdf
No parent application specified
```

**2. System extracts fields:**
```python
{
  "site_address": "123 Main Street, Birmingham, B8 1BG",
  "postcode": "B8 1BG",
  "proposed_use": "Single storey rear extension to existing dwelling"
}
```

**3. Auto-discovery runs:**

**Step 1:** Check description for parent reference
- Pattern match: `"existing dwelling"` (no specific reference)
- Result: None found

**Step 2:** Search by address
- Query: `find_applications_by_address("123 Main Street, Birmingham, B8 1BG")`
- Found: APP-2024-001 (address: "123 Main Street, Birmingham B8 1BG")
- Similarity: 98%
- Result: **AUTO-LINKED** ✅

**Step 3:** Update database
```python
submission.parent_submission_id = 456  # Latest submission of APP-2024-001
```

**4. Validation runs with delta:**
- System compares V0 (APP-2024-001) vs V1 (new extension)
- Only revalidates impacted rules
- Generates comparison view

## 🎯 Confidence Thresholds

| Confidence | Action | Example |
|-----------|---------|---------|
| **≥ 95%** | Auto-link | Exact reference match in description |
| **90-95%** | Auto-link | High address similarity |
| **85-90%** | Auto-link | Very good address match |
| **70-85%** | Log, suggest manual review | Single postcode match |
| **< 70%** | Return candidates for user selection | Multiple postcode matches |

## 📊 Benefits

### Before:
- ❌ Users had to manually link modifications
- ❌ No way to discover historical applications
- ❌ Delta computation not automated
- ❌ All 50+ rules re-run unnecessarily

### After:
- ✅ **Automatic parent discovery** by address/postcode
- ✅ **Smart reference extraction** from descriptions  
- ✅ **Fuzzy address matching** handles format variations
- ✅ **Confidence scoring** for reliable auto-linking
- ✅ **Manual override** available for edge cases
- ✅ **Targeted revalidation** (only impacted rules)
- ✅ **Full audit trail** of discovery logic

## 🧪 Testing

To test the implementation:

1. **Create parent application:**
   ```
   APP-2024-001
   Site: 123 Main Street, Birmingham, B8 1BG
   Status: Approved
   ```

2. **Upload modification documents:**
   ```
   Description: "Single storey rear extension"
   Site: 123 Main Street, Birmingham, B8 1BG
   ```

3. **Verify auto-linking:**
   - Check logs for: `"Auto-discovered parent submission..."`
   - Verify `submission.parent_submission_id` is set
   - Confirm delta computation runs

## 🔧 Future Enhancements

Potential improvements:
- [ ] Add ML-based address normalization
- [ ] Support for UPRN (Unique Property Reference Number) matching
- [ ] Historical application timeline visualization
- [ ] Confidence score calibration based on feedback
- [ ] Search in ExtractedField table for postcode fallback
- [ ] Support for related applications (not just modifications)

## 📝 Files Modified

1. **`planproof/db.py`** (85 lines added)
   - `find_applications_by_address()`
   - `find_applications_by_postcode()`

2. **`planproof/services/parent_discovery.py`** (NEW, 315 lines)
   - `discover_parent_application()`
   - `get_potential_parents()`
   - Helper functions for matching

3. **`planproof/api/routes/documents.py`** (60 lines modified)
   - Integrated auto-discovery in upload flow
   - Added `/find-parents` endpoint

4. **`requirements.txt`** (2 lines added)
   - fuzzywuzzy, python-Levenshtein

## ✅ Implementation Complete

The automatic parent discovery feature is now **fully implemented** and ready for testing. The system will automatically identify and link modification applications to their parent applications with high confidence, dramatically improving the user experience and enabling intelligent delta-based validation.

---

**Next Steps:**
1. Install new dependencies: `pip install -r requirements.txt`
2. Restart backend server
3. Test with real modification scenarios
4. Monitor logs for discovery confidence scores
5. Adjust thresholds based on real-world performance
