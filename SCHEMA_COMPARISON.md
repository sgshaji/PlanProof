# Database Schema vs Code Model Comparison

## Summary
Comparison between actual PostgreSQL database schema and SQLAlchemy ORM models defined in `planproof/db.py`.

**✅ = Match | ⚠️ = Partial/Minor Issue | ❌ = Missing/Critical Gap**

---

## Core Tables

### 1. applications
| Status | Database Column | Code Model | Gap/Issue |
|--------|----------------|------------|-----------|
| ✅ | id (integer, NOT NULL) | Column(Integer, primary_key=True) | Match |
| ✅ | application_ref (varchar, NOT NULL) | Column(String(100), unique=True, nullable=False) | Match |
| ✅ | applicant_name (varchar, NULL) | Column(String(255)) | Match |
| ✅ | application_date (timestamp, NULL) | Column(DateTime(timezone=True)) | Match |
| ✅ | created_at (timestamp, NOT NULL) | Column(DateTime(timezone=True), default=utcnow) | Match |
| ✅ | updated_at (timestamp, NULL) | Column(DateTime(timezone=True), onupdate=utcnow) | Match |
| ✅ | site_address (text, NULL) | Column(Text, nullable=True) | **FIXED** - Column added |
| ✅ | proposal_description (text, NULL) | Column(Text, nullable=True) | **FIXED** - Column added |
| ❌ | **postcode** | **Not defined** | **CRITICAL**: Code tries to query `Application.postcode` in `find_applications_by_postcode()` but column doesn't exist in DB or model. **FIXED** - Function now searches ExtractedField table instead |

---

### 2. submissions
| Status | Database Column | Code Model | Gap/Issue |
|--------|----------------|------------|-----------|
| ✅ | id (integer, NOT NULL) | Column(Integer, primary_key=True) | Match |
| ✅ | planning_case_id (integer, NOT NULL) | Column(Integer, ForeignKey("applications.id")) | Match |
| ✅ | submission_version (varchar, NOT NULL) | Column(String(10), nullable=False) | Match |
| ✅ | parent_submission_id (integer, NULL) | Column(Integer, ForeignKey("submissions.id")) | Match |
| ✅ | status (varchar, NOT NULL) | Column(String(20), nullable=False, default="pending") | Match |
| ✅ | submission_metadata (json, NULL) | Column(JSON, nullable=True) | Match |
| ✅ | submission_type (varchar, NULL) | Column(String(50), nullable=True) | Match |
| ✅ | submission_type_confidence (double, NULL) | Column(Float, nullable=True) | Match |
| ✅ | submission_type_source (varchar, NULL) | Column(String(20), nullable=True) | Match |
| ✅ | application_type (varchar, NULL) | Column(String(50), nullable=True) | **FIXED** - Column added |
| ✅ | created_at (timestamp, NOT NULL) | Column(DateTime(timezone=True), default=utcnow) | Match |
| ✅ | updated_at (timestamp, NULL) | Column(DateTime(timezone=True), onupdate=utcnow) | Match |

---

### 3. documents
| Status | Database Column | Code Model | Gap/Issue |
|--------|----------------|------------|-----------|
| ✅ | id (integer, NOT NULL) | Column(Integer, primary_key=True) | Match |
| ✅ | application_id (integer, NULL) | Column(Integer, ForeignKey("applications.id")) | Match |
| ✅ | submission_id (integer, NULL) | Column(Integer, ForeignKey("submissions.id")) | Match |
| ✅ | blob_uri (varchar, NOT NULL) | Column(String(500), nullable=False, unique=True) | Match |
| ✅ | filename (varchar, NOT NULL) | Column(String(255), nullable=False) | Match |
| ✅ | content_hash (varchar, NULL) | Column(String(64), nullable=True, unique=True) | Match |
| ✅ | uploaded_at (timestamp, NOT NULL) | Column(DateTime(timezone=True), default=utcnow) | Match |
| ✅ | processed_at (timestamp, NULL) | Column(DateTime(timezone=True), nullable=True) | Match |
| ✅ | page_count (integer, NULL) | Column(Integer, nullable=True) | Match |
| ✅ | docintel_model (varchar, NULL) | Column(String(50), nullable=True) | Match |
| ✅ | document_type (varchar, NULL) | Column(String(50), nullable=True) | Match |

---

### 4. validation_checks
| Status | Database Column | Code Model | Gap/Issue |
|--------|----------------|------------|-----------|
| ✅ | id (integer, NOT NULL) | Column(Integer, primary_key=True) | Match |
| ✅ | submission_id (integer, NULL) | Column(Integer, ForeignKey("submissions.id")) | Match |
| ✅ | document_id (integer, NULL) | Column(Integer, ForeignKey("documents.id")) | Match |
| ✅ | rule_id (integer, NULL) | Column(Integer, ForeignKey("rules.id")) | Match |
| ✅ | rule_id_string (varchar, NULL) | Column(String(100), nullable=True) | Match |
| ✅ | status (USER-DEFINED enum, NOT NULL) | Column(SQLEnum(ValidationStatus), nullable=False) | Match |
| ✅ | explanation (text, NULL) | Column(Text, nullable=True) | Match |
| ✅ | evidence_ids (json, NULL) | Column(JSON, nullable=True) | Match |
| ✅ | evidence_details (json, NULL) | Column(JSON, nullable=True) | **FIXED** - Column added |
| ✅ | candidate_documents (json, NULL) | Column(JSON, nullable=True) | **FIXED** - Column added |
| ✅ | created_at (timestamp, NOT NULL) | Column(DateTime(timezone=True), default=utcnow) | Match |
| ✅ | updated_at (timestamp, NULL) | Column(DateTime(timezone=True), onupdate=utcnow) | Match |

---

### 5. run_documents (Junction Table)
| Status | Database Column | Code Model | Gap/Issue |
|--------|----------------|------------|-----------|
| ✅ | run_id (integer, NOT NULL, PK) | Column(Integer, ForeignKey("runs.id"), primary_key=True) | **FIXED** - Table created |
| ✅ | document_id (integer, NOT NULL, PK) | Column(Integer, ForeignKey("documents.id"), primary_key=True) | **FIXED** - Table created |
| ✅ | created_at (timestamp, NOT NULL) | Column(DateTime(timezone=True), default=utcnow) | **FIXED** - Table created |

---

### 6. runs
| Status | Database Column | Code Model | Gap/Issue |
|--------|----------------|------------|-----------|
| ✅ | id (integer, NOT NULL) | Column(Integer, primary_key=True) | Match |
| ✅ | run_type (varchar, NOT NULL) | Column(String(50), nullable=False) | Match |
| ✅ | document_id (integer, NULL) | Column(Integer, ForeignKey("documents.id")) | Match |
| ✅ | application_id (integer, NULL) | Column(Integer, ForeignKey("applications.id")) | Match |
| ✅ | started_at (timestamp, NOT NULL) | Column(DateTime(timezone=True), default=utcnow) | Match |
| ✅ | completed_at (timestamp, NULL) | Column(DateTime(timezone=True), nullable=True) | Match |
| ✅ | status (varchar, NOT NULL) | Column(String(50), nullable=False, default="running") | Match |
| ✅ | error_message (text, NULL) | Column(Text, nullable=True) | Match |
| ✅ | run_metadata (json, NULL) | Column(JSON, nullable=True) | Match |

---

### 7. extracted_fields
| Status | Database Column | Code Model | Gap/Issue |
|--------|----------------|------------|-----------|
| ✅ | id (integer, NOT NULL) | Column(Integer, primary_key=True) | Match |
| ✅ | submission_id (integer, NOT NULL) | Column(Integer, ForeignKey("submissions.id")) | Match |
| ✅ | field_name (varchar, NOT NULL) | Column(String(100), nullable=False) | Match |
| ✅ | field_value (text, NULL) | Column(Text, nullable=True) | Match |
| ✅ | field_unit (varchar, NULL) | Column(String(50), nullable=True) | Match |
| ✅ | confidence (double, NULL) | Column(Float, nullable=True) | Match |
| ✅ | extractor (varchar, NULL) | Column(String(50), nullable=True) | Match |
| ✅ | evidence_id (integer, NULL) | Column(Integer, ForeignKey("evidence.id")) | Match |
| ✅ | conflict_flag (varchar, NULL) | Column(String(20), nullable=True) | Match |
| ✅ | created_at (timestamp, NOT NULL) | Column(DateTime(timezone=True), default=utcnow) | Match |
| ✅ | updated_at (timestamp, NULL) | Column(DateTime(timezone=True), onupdate=utcnow) | Match |

---

### 8. evidence
| Status | Database Column | Code Model | Gap/Issue |
|--------|----------------|------------|-----------|
| ✅ | id (integer, NOT NULL) | Column(Integer, primary_key=True) | Match |
| ✅ | document_id (integer, NOT NULL) | Column(Integer, ForeignKey("documents.id")) | Match |
| ✅ | page_id (integer, NULL) | Column(Integer, ForeignKey("pages.id")) | Match |
| ✅ | page_number (integer, NOT NULL) | Column(Integer, nullable=False) | Match |
| ✅ | evidence_type (varchar, NOT NULL) | Column(String(50), nullable=False) | Match |
| ✅ | evidence_key (varchar, NOT NULL) | Column(String(100), nullable=False) | Match |
| ✅ | bbox (json, NULL) | Column(JSON, nullable=True) | Match |
| ✅ | snippet (text, NULL) | Column(Text, nullable=True) | Match |
| ✅ | content (text, NULL) | Column(Text, nullable=True) | Match |
| ✅ | confidence (double, NULL) | Column(Float, nullable=True) | Match |
| ✅ | created_at (timestamp, NOT NULL) | Column(DateTime(timezone=True), default=utcnow) | Match |

---

### 9. pages
| Status | Database Column | Code Model | Gap/Issue |
|--------|----------------|------------|-----------|
| ✅ | id (integer, NOT NULL) | Column(Integer, primary_key=True) | Match |
| ✅ | document_id (integer, NOT NULL) | Column(Integer, ForeignKey("documents.id")) | Match |
| ✅ | page_number (integer, NOT NULL) | Column(Integer, nullable=False) | Match |
| ✅ | page_metadata (json, NULL) | Column(JSON, nullable=True) | Match |
| ✅ | created_at (timestamp, NOT NULL) | Column(DateTime(timezone=True), default=utcnow) | Match |

---

### 10. rules
| Status | Database Column | Code Model | Gap/Issue |
|--------|----------------|------------|-----------|
| ✅ | id (integer, NOT NULL) | Column(Integer, primary_key=True) | Match |
| ✅ | rule_id (varchar, NOT NULL) | Column(String(100), unique=True, nullable=False) | Match |
| ✅ | rule_name (varchar, NOT NULL) | Column(String(255), nullable=False) | Match |
| ✅ | rule_category (varchar, NOT NULL) | Column(String(50), nullable=False) | Match |
| ✅ | required_fields (json, NOT NULL) | Column(JSON, nullable=False) | Match |
| ✅ | severity (varchar, NOT NULL) | Column(String(20), nullable=False) | Match |
| ✅ | rule_config (json, NULL) | Column(JSON, nullable=True) | Match |
| ✅ | is_active (varchar, NOT NULL) | Column(String(10), nullable=False, default="yes") | Match |
| ✅ | created_at (timestamp, NOT NULL) | Column(DateTime(timezone=True), default=utcnow) | Match |
| ✅ | updated_at (timestamp, NULL) | Column(DateTime(timezone=True), onupdate=utcnow) | Match |

---

## Additional Tables in Database (Not in ORM Models)

### change_items
| Database Column | Code Model | Issue |
|----------------|------------|-------|
| id, change_set_id, change_type, item_key, old_value, new_value, significance, impacted_rule_ids, created_at | **Column names don't match** | ⚠️ **Model has**: field_key, document_type, change_metadata. **DB has**: item_key, significance, impacted_rule_ids. Mismatch in column names |

### change_sets
| Database Column | Code Model | Issue |
|----------------|------------|-------|
| All columns match | ✅ Match | Correct |

### artefacts
| Database Column | Code Model | Issue |
|----------------|------------|-------|
| All columns match | ✅ Match | Correct |

### geometry_features
| Database Column | Code Model | Issue |
|----------------|------------|-------|
| All columns match | ✅ Match | Correct |

### spatial_metrics
| Database Column | Code Model | Issue |
|----------------|------------|-------|
| All columns match | ✅ Match | Correct |

### validation_results
| Database Column | Code Model | Issue |
|----------------|------------|-------|
| All columns match | ✅ Match | Correct (legacy table) |

---

## Models NOT in Database (Missing Tables)

The following models are defined in code but tables **DO NOT exist** in the database:

| Model Class | Table Name | Status | Issue |
|-------------|-----------|--------|-------|
| OfficerOverride | officer_overrides | ❌ **MISSING** | Table not created in database |
| FieldResolution | field_resolutions | ❌ **MISSING** | Table not created in database |
| IssueResolution | issue_resolutions | ❌ **MISSING** | Table not created in database |
| ReviewDecision | review_decisions | ❌ **MISSING** | Table not created in database |
| EvidenceFeedback | evidence_feedback | ❌ **MISSING** | Table not created in database |
| ResolutionAction | resolution_actions | ❌ **MISSING** | Referenced in IssueResolution but model not found in db.py |
| RecheckHistory | recheck_history | ❌ **MISSING** | Referenced in IssueResolution but model not found in db.py |

---

## System Tables (PostgreSQL/PostGIS)

These are system tables from PostGIS extension - ignore:
- alembic_version
- geography_columns
- geometry_columns
- spatial_ref_sys

---

## Critical Issues Found

### 1. **Application.postcode Missing** ❌ **FIXED**
- **Issue**: Code in `find_applications_by_postcode()` (line 978-1025) tried to query `Application.postcode` 
- **Reality**: Column doesn't exist in database OR model
- **Impact**: Postcode search broke with AttributeError
- **Fix Applied**: Changed function to search `ExtractedField` table where postcode values actually stored, added try/catch for graceful degradation

### 2. **ChangeItem Column Mismatch** ⚠️
- **Code Model**: `field_key`, `document_type`, `change_metadata`
- **Database**: `item_key`, `significance`, `impacted_rule_ids`
- **Impact**: ORM queries/inserts for ChangeItem will fail
- **Fix Needed**: Align column names between model and database

### 3. **Missing HIL (Human-in-Loop) Tables** ❌
- **Missing Tables**: officer_overrides, field_resolutions, issue_resolutions, review_decisions, evidence_feedback, resolution_actions, recheck_history
- **Impact**: Any code referencing these models will fail with "table does not exist" errors
- **Fix Needed**: Run migration to create these tables OR remove models from db.py if not used

### 4. **Missing Model Classes** ❌
- **ResolutionAction** and **RecheckHistory** are referenced in `IssueResolution` relationships but class definitions not found in db.py
- **Impact**: SQLAlchemy will fail to build relationships
- **Fix Needed**: Add missing model classes or remove relationships

---

## Validation Status

### ✅ **FIXED Issues**:
1. applications.site_address - Column added
2. applications.proposal_description - Column added
3. submissions.application_type - Column added
4. validation_checks.evidence_details - Column added
5. validation_checks.candidate_documents - Column added
6. run_documents table - Created with proper foreign keys and indexes
7. Application.postcode query - Fixed to use ExtractedField table with error handling

### ⚠️ **Partial Issues Remaining**:
1. ChangeItem column name mismatch (field_key vs item_key, etc.)

### ❌ **Critical Issues Remaining**:
1. Missing HIL tables (7 tables): officer_overrides, field_resolutions, issue_resolutions, review_decisions, evidence_feedback, resolution_actions, recheck_history
2. Missing model class definitions for ResolutionAction and RecheckHistory

---

## Recommendations

### Immediate Actions:
1. ✅ **DONE**: Run `add_columns.py` to add missing columns
2. ✅ **DONE**: Fix `find_applications_by_postcode()` to search correct table
3. **TODO**: Fix ChangeItem column names - align model with database OR alter table
4. **TODO**: Create missing HIL tables OR remove unused models from db.py

### Long-term Solutions:
1. **Use Alembic migrations**: Instead of manual ALTER TABLE scripts, use proper migration system already configured
2. **Schema validation on startup**: Add check that verifies DB schema matches models before accepting requests
3. **Graceful degradation**: Wrap all field access in try/catch, skip missing fields instead of crashing (as user requested)
4. **Remove dead code**: If HIL features not implemented, remove the unused models to prevent confusion

---

## Database Connection Info
- **Host**: planproof-dev-pgflex-8016.postgres.database.azure.com
- **Database**: planproof_dev
- **Connection String**: Read from .env file `DATABASE_URL`

---

*Generated: 2024 - Based on actual PostgreSQL schema query*
