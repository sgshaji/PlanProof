# Part 2 Complete: UI Components for Enhanced Issues

## What Was Built

### 1. Enhanced Issue Card Component
**File:** `planproof/ui/components/enhanced_issue_card.py` (528 lines)

Comprehensive Streamlit components for displaying enhanced validation issues:

#### Main Components:
- **`render_enhanced_issue_card(issue)`** - Complete issue card with all sections
  - Severity badges (Blocker, Critical, Warning, Info)
  - Status badges (Open, In Progress, Awaiting Verification, Resolved, Dismissed)
  - User message section (title, description, why it matters, impact)
  - "What We Checked" transparency section with evidence
  - Actionable buttons with appropriate handlers
  - Resolution progress tracking

- **`render_bulk_action_panel(issues)`** - Bulk upload for multiple missing documents
  - Groups issues by document type
  - Multi-file upload with type assignment
  - "Upload All & Revalidate" button

- **`render_resolution_tracker(issues)`** - Progress dashboard
  - Overall resolution progress bar
  - Metrics: Total, Resolved, In Progress, Open
  - Breakdown by severity (Blocker, Critical, Warning, Info)

#### Action Handlers:
- **`render_upload_widget()`** - File upload for documents (single/bulk)
- **`render_select_option_widget()`** - Radio buttons for choices (e.g., BNG applicability)
- **`render_provide_explanation_widget()`** - Text area for explanations/justifications
- **`render_action_handler()`** - Routes to appropriate widget based on ActionType

### 2. Issue Converter
**File:** `planproof/ui/components/issue_converter.py` (262 lines)

Bridges legacy validation findings with enhanced issue model:

#### Functions:
- **`convert_validation_finding_to_enhanced_issue()`** - Main conversion entry point
- **`_map_rule_to_factory()`** - Maps rule_id to appropriate factory function:
  - Missing documents → `create_missing_document_issue()`
  - BNG applicability → `create_bng_applicability_issue()`
  - BNG exemption → `create_bng_exemption_reason_issue()`
  - M3 registration → `create_m3_registration_issue()`
  - PA documents → `create_pa_required_docs_issue()`
  - Data conflicts → `create_data_conflict_issue()`
- **`_identify_document_type()`** - Extracts document type from rule/message
- **`_create_generic_enhanced_issue()`** - Fallback for unmapped rules
- **`convert_all_findings()`** - Batch conversion with error handling

### 3. Results Page Integration
**File:** `planproof/ui/pages/results.py` (updated)

Added enhanced issue display with feature toggle:

#### New Features:
- **🎯 Enhanced Issue Display toggle** - Switch between legacy and new views
- **`_render_enhanced_issues_view()`** - Enhanced issue rendering:
  - Resolution tracker at top
  - Bulk action panel for multi-document issues
  - Advanced filters (Severity, Status, Category)
  - Issue count display
  - Renders all enhanced issue cards
- **`_render_legacy_findings_view()`** - Original display (extracted into function)
  - Preserves existing functionality
  - Officer overrides
  - Evidence viewing

## How It Works

### User Flow (Enhanced Mode):

1. **Toggle Enhanced Display**
   ```
   User enables "🎯 Enhanced Issue Display" toggle
   ```

2. **View Resolution Progress**
   ```
   Resolution Tracker shows:
   - Progress bar: 3/10 issues resolved (30%)
   - Metrics: 10 Total, 3 Resolved, 2 In Progress, 5 Open
   - By Severity: 1 Blocker, 3 Critical, 4 Warning, 2 Info
   ```

3. **Bulk Actions (if multiple missing docs)**
   ```
   Bulk Action Panel appears:
   - Lists all required documents
   - Multi-file uploader
   - Assign types to each file
   - "Upload All & Revalidate" button
   ```

4. **Filter Issues**
   ```
   Three filter dropdowns:
   - Severity: All | Blocker | Critical | Warning | Info
   - Status: All | Open | In Progress | Awaiting Verification | Resolved | Dismissed
   - Category: All | Missing Document | Data Quality | etc.
   ```

5. **View Issue Card**
   ```
   Each issue expands to show:
   
   ┌─────────────────────────────────────────────┐
   │ 🚫 BLOCKER   📁 Missing Document   👤 Applicant│
   ├─────────────────────────────────────────────┤
   │ Missing: Site Location Plan                 │
   │                                             │
   │ We couldn't find a Site Location Plan...   │
   │                                             │
   │ 💡 Why it matters: Required by GDPO 1995   │
   │ ⚠️ Impact: Application cannot be validated  │
   ├─────────────────────────────────────────────┤
   │ 🔍 What We Checked                          │
   │   Search Area: All uploaded documents       │
   │   How: Document classification + OCR        │
   │   Documents: [application_form.pdf, ...]    │
   ├─────────────────────────────────────────────┤
   │ 🎯 What You Can Do                          │
   │                                             │
   │ 1. Upload Site Location Plan               │
   │    [📤 Upload Document] ✓ Done             │
   │                                             │
   │ 2. Confirm Document Included                │
   │    [✓ Confirm Data]                        │
   ├─────────────────────────────────────────────┤
   │ 📊 Resolution Progress                      │
   │                                             │
   │ Status: 🟡 IN PROGRESS                     │
   │ Last Attempt: 2025-12-31 10:30             │
   │ 🔄 Auto-Recheck: ✓ On document upload     │
   └─────────────────────────────────────────────┘
   ```

6. **Take Action**
   ```
   Click action button → Widget appears:
   
   For UPLOAD_DOCUMENT:
   - File uploader appears
   - Select PDF
   - Click "Upload" button
   - File stored in session state for processing
   
   For SELECT_OPTION:
   - Radio buttons with options
   - Each option shows description
   - Click "Confirm Selection"
   
   For PROVIDE_EXPLANATION:
   - Text area (min 10 chars)
   - Character counter
   - "Submit Explanation" button
   ```

### Backend Data Flow:

```
Validation Findings (legacy dict)
    ↓
issue_converter.py → convert_all_findings()
    ↓
Maps rule_id → Factory function
    ↓
EnhancedIssue objects (dataclasses)
    ↓
enhanced_issue_card.py → render_enhanced_issue_card()
    ↓
Streamlit UI with actions
    ↓
User actions stored in st.session_state
    ↓
(Part 3 will process actions and trigger revalidation)
```

## Key Design Patterns

### 1. **Feature Toggle**
```python
use_enhanced = st.toggle("🎯 Enhanced Issue Display")
if use_enhanced:
    _render_enhanced_issues_view(findings, run_id)
else:
    _render_legacy_findings_view(findings, run_id)
```

### 2. **Factory Pattern Mapping**
```python
# Maps rule IDs to appropriate factory functions
if "missing" in rule_id.lower():
    doc_type = _identify_document_type(rule_id)
    return create_missing_document_issue(doc_type, rule_id, run_id)
elif "bng" in rule_id.lower():
    return create_bng_applicability_issue(rule_id, run_id)
```

### 3. **Action Routing**
```python
# Routes action types to appropriate widgets
if action.action_type == ActionType.UPLOAD_DOCUMENT:
    render_upload_widget(issue_id, action)
elif action.action_type == ActionType.SELECT_OPTION:
    render_select_option_widget(issue_id, action)
```

### 4. **Session State Management**
```python
# Store action requests for processing
st.session_state[f"action_request_{issue_id}"] = action

# Store uploaded files
st.session_state[f"uploaded_doc_{issue_id}"] = file

# Bulk uploads
st.session_state["bulk_upload_data"] = {
    "files": uploaded_files,
    "assignments": assignments,
    "issue_ids": [i.issue_id for i in issues]
}
```

## Testing Instructions

### 1. **Enable Enhanced Display**
```bash
# Restart UI (if needed)
python run_ui.py

# Navigate to Results page
# Enter run ID: 22
# Toggle "🎯 Enhanced Issue Display" ON
```

### 2. **View Components**
```
✓ Resolution Tracker should show at top
✓ Filter dropdowns should appear (3 columns)
✓ Issue cards should expand/collapse
✓ Each card shows all sections:
  - Severity badge
  - User message
  - What we checked
  - Actions
  - Resolution progress
```

### 3. **Test Actions**
```
Click action button →
✓ Widget appears inline
✓ File uploader accepts PDF
✓ Radio buttons work
✓ Text area has character counter
✓ Buttons respond to clicks
```

### 4. **Test Bulk Actions**
```
If multiple missing docs:
✓ Bulk panel appears
✓ Can upload multiple files
✓ Can assign types to each
✓ "Upload All" button appears
```

## What's Next (Part 3)

Part 3 will implement **Resolution Tracking & Auto-Recheck**:

1. **Process uploaded documents**
   - Move files from session state to runs/{run_id}/inputs/
   - Re-run extraction pipeline
   - Generate new document IDs

2. **Auto-recheck logic**
   - Detect upload event
   - Find issues with `auto_recheck_on_upload = True`
   - Re-run validation rules
   - Update issue status automatically

3. **Dependency resolution**
   - Track issue dependencies
   - Cascade resolution (fixing one resolves others)
   - Update UI in real-time

4. **Officer override integration**
   - Allow officers to dismiss issues
   - Add dismissal reasons
   - Track override history

## Files Created/Modified

### Created:
1. ✅ `planproof/ui/components/enhanced_issue_card.py` (528 lines)
2. ✅ `planproof/ui/components/issue_converter.py` (262 lines)

### Modified:
3. ✅ `planproof/ui/pages/results.py`
   - Added enhanced issue imports
   - Added feature toggle
   - Extracted `_render_legacy_findings_view()`
   - Added `_render_enhanced_issues_view()`
   - Removed duplicate code

## Summary

Part 2 successfully transforms the validation results page from a **static list of errors** into an **interactive issue resolution system**:

**Before (Legacy):**
- List of validation failures
- Technical rule IDs
- Cryptic error messages
- No clear next steps

**After (Enhanced):**
- Resolution progress dashboard
- Clear user-friendly titles
- "Why it matters" explanations
- Concrete actionable buttons
- Transparency about what was checked
- Real-time status tracking

The enhanced display is **opt-in** (toggle), ensuring backward compatibility while providing a superior user experience for those who enable it.

Ready to proceed with **Part 3: Resolution Tracking & Auto-Recheck** when you say "continue".
