# Requirements Assessment: MVP Specification vs Current Implementation

**Date**: 2025-01-XX  
**Assessment Against**: AI Planning Validation Support System (MVP) - Requirements and Architecture Specification v1.0  
**Repository**: PlanProof (AathiraTD/PlanProof)

---

## Executive Summary

This document compares the MVP requirements specification with the current PlanProof implementation. The assessment shows **strong foundational implementation** with core pipeline components complete, but **significant gaps** remain in UI functionality, modification workflows, spatial validation, and advanced rule categories.

**Overall Completion**: ~60% of MVP requirements

**Status Breakdown**:
- ✅ **Fully Implemented**: ~40%
- 🟡 **Partially Implemented**: ~20%
- ❌ **Not Implemented**: ~40%

---

## 1. Architecture Principles Assessment

| Principle | Requirement | Implementation Status | Notes |
|-----------|-------------|----------------------|-------|
| Deterministic-first | Rules + schema-bound extraction default; LLM gated | ✅ **IMPLEMENTED** | `field_mapper.py` uses regex/heuristics; `llm_gate.py` has strict gating logic |
| Evidence-backed | Every extracted value cites page-level evidence | ✅ **IMPLEMENTED** | Evidence table with page, bbox, snippet; linked to ExtractedField |
| Human-in-the-loop | Officers retain decision authority; overrides auditable | 🟡 **PARTIAL** | UI exists but override functionality not implemented |
| Separation of concerns | Modular components (ingestion, extraction, validation, LLM, UI) | ✅ **IMPLEMENTED** | Clear pipeline separation in `planproof/pipeline/` |
| Extensible data model | Versioning + deltas enable modification workflows | 🟡 **PARTIAL** | Schema supports it; delta computation not implemented |

---

## 2. Component-by-Component Assessment

### 2.1 Document Ingestion and Tiered OCR

**Requirement**: Tiered extraction approach (Tier 1: text PDFs, Tier 2: Azure DI, Tier 3: Tesseract fallback)

| Tier | Status | Implementation |
|------|--------|----------------|
| Tier 1 (Born-digital PDFs) | ✅ **IMPLEMENTED** | Text extraction via `docintel.py` |
| Tier 2 (Azure Document Intelligence) | ✅ **IMPLEMENTED** | `docintel.py` uses Azure DI prebuilt-layout model |
| Tier 3 (Tesseract fallback) | ❌ **NOT IMPLEMENTED** | No Tesseract integration found |

**Evidence Output**: ✅ Page-level outputs with bounding boxes and snippets are produced.

**Gap**: Missing Tesseract OCR fallback for scenarios where Azure DI is unavailable/restricted.

---

### 2.2 Document Classification

**Requirement**: Classify documents into known types with confidence and evidence.

**Required Types**:
- ✅ Application Form
- ✅ Site Plan
- ❌ Location Plan (not explicitly classified)
- ❌ Existing Floor Plans (not explicitly classified)
- ❌ Proposed Floor Plans (not explicitly classified)
- ❌ Existing Elevations (not explicitly classified)
- ❌ Proposed Elevations (not explicitly classified)
- ✅ Design & Access Statement (as `design_statement`)
- ✅ Other Supporting Document (as `unknown`)

**Current Implementation**: `field_mapper.py` classifies into: `application_form`, `site_plan`, `drawing`, `design_statement`, `heritage`, `unknown`

**Gap**: Missing explicit classification for Location Plan, Floor Plans (existing/proposed), and Elevations (existing/proposed).

---

### 2.3 Evidence-Backed Extraction

**Requirement**: Extract canonical fields into Field Dictionary; link values to Evidence records.

| Feature | Status | Implementation |
|--------|--------|----------------|
| Field extraction with evidence links | ✅ **IMPLEMENTED** | `field_mapper.py` extracts fields; evidence stored in `evidence` table |
| Value, unit, confidence, extractor tracking | ✅ **IMPLEMENTED** | `ExtractedField` model has these fields |
| Multiple source reconciliation | 🟡 **PARTIAL** | Schema supports it; conflict detection logic mentioned but not fully implemented |
| Conflict flagging with evidence | ❌ **NOT IMPLEMENTED** | No conflict detection/reconciliation code found |

**Gap**: Conflict detection when multiple documents provide different values for the same field.

---

### 2.4 Data Model and Persistence

**Requirement**: Graph-shaped relational schema with all required tables.

**Required Tables**: ✅ **ALL IMPLEMENTED**
- ✅ `applications` (PlanningCase)
- ✅ `submissions`
- ✅ `documents`
- ✅ `pages`
- ✅ `evidence`
- ✅ `extracted_fields`
- ✅ `geometry_features`
- ✅ `spatial_metrics`
- ✅ `change_sets`
- ✅ `change_items`
- ✅ `rules`
- ✅ `validation_checks`
- ✅ `validation_results`

**Storage Strategy**: ✅ Hybrid approach (JSON artefacts in blob storage + relational tables)

**PostGIS Support**: ✅ Schema includes PostGIS geometry columns (though not actively used)

---

### 2.5 Deterministic Rules Validation Engine

**Requirement**: Evaluate configured rules; produce per-rule results with PASS/FAIL/NEEDS_REVIEW.

**Rule Categories Required**:

| Category | Status | Implementation |
|----------|--------|----------------|
| DOCUMENT_REQUIRED | 🟡 **PARTIAL** | Rule catalog exists; no code to check required docs by case type |
| CONSISTENCY | ❌ **NOT IMPLEMENTED** | No code to check field matches across documents |
| MODIFICATION | ❌ **NOT IMPLEMENTED** | No code to verify parent case references or delta completeness |
| SPATIAL | ❌ **NOT IMPLEMENTED** | No spatial rules executed even when geometry/metrics exist |

**Current Rule Catalog**: Only 4 rules in `artefacts/rule_catalog.json`:
- R1: Site Address Validation
- R1-SITE-NOTICE: Site Notice Supporting Evidence
- R2: Proposed Use Validation
- R3: Application Reference

**Validation Engine**: ✅ `validate.py` loads rules and evaluates them, but only checks required fields (not category-specific logic).

**Gap**: Missing implementation of category-specific validation logic (DOCUMENT_REQUIRED, CONSISTENCY, MODIFICATION, SPATIAL).

---

### 2.6 Delta Computation for Modifications

**Requirement**: Compute ChangeSet between V0 and V1+ submissions; generate ChangeItems.

| Feature | Status | Implementation |
|--------|--------|----------------|
| ChangeSet computation | ❌ **NOT IMPLEMENTED** | Tables exist (`change_sets`, `change_items`) but no code computes deltas |
| Field deltas | ❌ **NOT IMPLEMENTED** | No code compares field values between submissions |
| Document deltas | ❌ **NOT IMPLEMENTED** | No code compares document sets (added/removed/replaced) |
| Spatial metric deltas | ❌ **NOT IMPLEMENTED** | No code compares spatial metrics |
| Significance scoring | ❌ **NOT IMPLEMENTED** | `significance_score` column exists but never populated |
| Requires validation flag | ❌ **NOT IMPLEMENTED** | `requires_validation` column exists but never populated |

**Schema Support**: ✅ Database schema fully supports modification workflow (parent-child relationships, ChangeSet/ChangeItem tables).

**Gap**: Complete delta computation engine missing.

---

### 2.7 Spatial Support (MVP Key Measurements)

**Requirement**: Support outline geometry + derived metrics; execute spatial rules when metrics exist.

| Feature | Status | Implementation |
|--------|--------|----------------|
| GeometryFeature creation | ❌ **NOT IMPLEMENTED** | Table exists; no code creates geometry features |
| SpatialMetric computation | ❌ **NOT IMPLEMENTED** | Table exists; no code computes metrics (distance, area, projection) |
| Spatial rule execution | ❌ **NOT IMPLEMENTED** | No spatial validation rules implemented |
| PostGIS queries | ❌ **NOT IMPLEMENTED** | PostGIS extension enabled but no spatial queries |

**Schema Support**: ✅ `geometry_features` and `spatial_metrics` tables exist with PostGIS geometry columns.

**Gap**: Complete spatial feature pipeline missing (creation, computation, validation).

---

### 2.8 Gated LLM Assistance

**Requirement**: LLM only invoked when extraction confidence is low, conflicts detected, or free-text interpretation needed.

| Feature | Status | Implementation |
|--------|--------|----------------|
| Gating logic | ✅ **IMPLEMENTED** | `llm_gate.py` has strict gating conditions |
| Structured JSON output | ✅ **IMPLEMENTED** | LLM outputs structured JSON with citations |
| Confidence tracking | ✅ **IMPLEMENTED** | LLM outputs include confidence scores |
| Evidence citations | ✅ **IMPLEMENTED** | LLM outputs cite evidence IDs/snippets |
| Advisory-only (reviewable) | ✅ **IMPLEMENTED** | LLM outputs stored but not auto-applied |

**Gating Conditions** (from `llm_gate.py`):
- ✅ Missing field has `error` severity
- ✅ Field is extractable from document type
- ✅ Document has sufficient text coverage
- ✅ Field hasn't been resolved in this run

**Status**: ✅ **FULLY IMPLEMENTED** - This is one of the strongest areas of the implementation.

---

### 2.9 Human-in-the-Loop (HITL) UI

**Requirement**: Enable officers to review, verify, and override system output.

**Required Screens/Areas**:

| Screen/Area | Requirement | Status | Implementation |
|------------|-------------|--------|----------------|
| Case & Submission overview | Case metadata, version history, status, key flags | ❌ **NOT IMPLEMENTED** | No case overview screen |
| Documents viewer | Document list, page thumbnails, zoom, search | ❌ **NOT IMPLEMENTED** | No document viewer with thumbnails/zoom |
| Extracted fields | Field name, value, unit, confidence, sources; filter by confidence | ❌ **NOT IMPLEMENTED** | No extracted fields viewer |
| Validation results | Rule list, PASS/FAIL/REVIEW, severity, explanation; drilldown to evidence | 🟡 **PARTIAL** | `results.py` shows findings but no evidence navigation |
| Delta view (mods) | ChangeSet summary, ChangeItems, significance, impacted rules | ❌ **NOT IMPLEMENTED** | No delta view |
| Decision & export | Officer decision, notes, timestamps, audit trail; override, request-info, export | 🟡 **PARTIAL** | Export exists (JSON/ZIP); override/request-info missing |

**Current UI Implementation**:
- ✅ Upload page (`upload.py`) - Basic file upload
- ✅ Status page (`status.py`) - Run status tracking
- ✅ Results page (`results.py`) - Validation findings display with export

**Gaps**:
1. No document viewer with page thumbnails, zoom, search
2. No evidence navigation (jump to bounding boxes from validation failures)
3. No officer override functionality with notes/audit trail
4. No request-info workflow
5. No case/submission overview screen
6. No extracted fields viewer
7. No delta view for modifications
8. No comparison view (V0 vs V1+)

---

## 3. Non-Functional Requirements Assessment

| ID | Requirement | Status | Notes |
|----|-------------|--------|-------|
| NFR-01 | Auditability: every result traceable to evidence | ✅ **IMPLEMENTED** | Evidence links exist; audit trail in database |
| NFR-02 | Security: RBAC, least privilege, encryption | ❌ **NOT IMPLEMENTED** | No RBAC; no security features implemented |
| NFR-03 | Resilience: failures don't lose data; partial outputs preserved | 🟡 **PARTIAL** | Run tracking exists; partial failure handling unclear |
| NFR-04 | Deterministic-first: avoid LLM calls unless gated | ✅ **IMPLEMENTED** | Strong gating logic in `llm_gate.py` |
| NFR-05 | Observability: stage timings, errors, trace IDs | 🟡 **PARTIAL** | Logging exists; no Application Insights integration |
| NFR-06 | Configurability: rules updated without code redeploy | 🟡 **PARTIAL** | Rules in JSON; no UI/mechanism to update without rebuild |

---

## 4. Open Design Decisions - Current Choices

| Decision | Requirement Default | Current Implementation | Match? |
|----------|-------------------|----------------------|--------|
| UI framework | Streamlit (preferred) | ✅ Streamlit | ✅ **MATCHES** |
| Search/RAG layer | Postgres full-text (MVP) | ❌ Not implemented | ⚠️ **NOT YET** |
| Orchestration | Synchronous with checkpointing | ✅ Synchronous pipeline | ✅ **MATCHES** |
| Geometry capture | Manual/assisted outline input | ❌ Not implemented | ⚠️ **NOT YET** |
| Rule authoring | JSON/YAML configs + Python evaluators | ✅ JSON + Python | ✅ **MATCHES** |
| LLM assist | Enabled but gated | ✅ Enabled and gated | ✅ **MATCHES** |

---

## 5. Verification and Acceptance Criteria

### 5.1 Verification Approach

| Approach | Status | Notes |
|----------|--------|-------|
| Golden-case test set | ✅ **IMPLEMENTED** | `tests/golden/` directory with test fixtures |
| Rule unit tests | ✅ **IMPLEMENTED** | `tests/unit/` has rule tests |
| Evidence integrity checks | 🟡 **PARTIAL** | Evidence links exist; no automated integrity validation |
| Delta tests | ❌ **NOT IMPLEMENTED** | No delta computation to test |
| Usability walkthrough | ❌ **NOT IMPLEMENTED** | No officer workflow testing |

### 5.2 Minimum Acceptance Criteria (MVP)

| Criterion | Status | Notes |
|-----------|--------|-------|
| End-to-end processing → validation report | ✅ **IMPLEMENTED** | Full pipeline works; JSON export available |
| At least one rule per category executes | ❌ **NOT MET** | Only basic field validation; missing CONSISTENCY, MODIFICATION, SPATIAL |
| Modification flow produces ChangeSet | ❌ **NOT MET** | Delta computation not implemented |
| HITL UI supports review, evidence navigation, override, export | 🟡 **PARTIAL** | Review and export exist; evidence navigation and override missing |

**Overall MVP Acceptance**: ❌ **NOT MET** - Missing critical UI features and rule categories.

---

## 6. Critical Gaps Summary

### High Priority (Blocking MVP Acceptance)

1. **Delta Computation Engine** - Complete missing implementation for V0 vs V1+ comparison
2. **Evidence Navigation UI** - Officers cannot jump from validation failures to evidence locations
3. **Officer Override Functionality** - No way to override decisions with notes/audit trail
4. **Rule Category Implementation** - CONSISTENCY, MODIFICATION, SPATIAL categories not implemented
5. **Document Viewer** - No way to view documents with thumbnails, zoom, search

### Medium Priority (Important for Full MVP)

6. **Case/Submission Overview Screen** - Missing metadata, version history, status display
7. **Extracted Fields Viewer** - No UI to review extracted fields with confidence filtering
8. **Request-Info Workflow** - No status tracking for submissions needing more information
9. **Conflict Detection** - No reconciliation when multiple sources provide different values
10. **Tesseract OCR Fallback** - Missing Tier 3 OCR for restricted environments

### Lower Priority (Can be deferred)

11. **Spatial Feature Pipeline** - Geometry creation, metric computation, spatial rules
12. **RBAC/Security** - No role-based access control
13. **Dashboards** - No team lead dashboard for consistency/throughput
14. **Search Functionality** - No full-text search across documents
15. **Application Insights Integration** - No monitoring dashboards

---

## 7. Recommendations

### Immediate Actions (Next Sprint)

1. **Implement Evidence Navigation**
   - Add clickable evidence links in results page
   - Create document viewer with page navigation
   - Show bounding boxes on document pages

2. **Implement Officer Override**
   - Add override buttons to validation results
   - Create notes/audit trail fields
   - Store override decisions in database

3. **Implement Basic Delta Computation**
   - Compare field values between V0 and V1+
   - Generate ChangeSet and ChangeItems
   - Calculate basic significance scores

4. **Implement DOCUMENT_REQUIRED Rules**
   - Add logic to check required documents by case type
   - Create rule catalog entries for document requirements

### Short-Term (Next 2-3 Sprints)

5. **Complete Modification Workflow**
   - Full delta computation (fields, documents, spatial metrics)
   - Modification UI (link V1+ to V0, delta view)
   - Revalidation targeting based on changes

6. **Implement CONSISTENCY Rules**
   - Cross-document field matching logic
   - Conflict detection and flagging

7. **Enhance UI**
   - Case/submission overview screen
   - Extracted fields viewer
   - Request-info workflow

### Medium-Term (Future Phases)

8. **Spatial Validation**
   - Geometry feature input (manual/assisted)
   - Spatial metric computation
   - Spatial validation rules

9. **Security & Governance**
   - RBAC implementation
   - Encryption at rest/transit
   - Data retention controls

10. **Advanced Features**
    - Full-text search
    - Team lead dashboards
    - Application Insights integration

---

## 8. Conclusion

The PlanProof implementation has a **strong foundation** with:
- ✅ Complete data model and schema
- ✅ Working end-to-end pipeline
- ✅ Evidence-backed extraction
- ✅ Gated LLM assistance
- ✅ Basic UI for upload/status/results

However, **critical gaps** remain that prevent MVP acceptance:
- ❌ Missing delta computation for modifications
- ❌ Incomplete UI for officer review and override
- ❌ Missing rule category implementations (CONSISTENCY, MODIFICATION, SPATIAL)
- ❌ No evidence navigation in UI

**Estimated effort to reach MVP acceptance**: 4-6 weeks focused development on:
1. Delta computation engine (1-2 weeks)
2. UI enhancements (evidence navigation, override, case overview) (2-3 weeks)
3. Rule category implementations (1 week)

The architecture is sound and extensible; the gaps are primarily in feature completion rather than fundamental design issues.

---

**Document prepared by**: AI Assistant  
**Review status**: Ready for stakeholder review

