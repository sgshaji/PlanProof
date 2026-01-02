# PlanProof UX Revamp - Implementation Status

**Date:** January 2, 2026  
**Commit:** f7b3f73

## ✅ COMPLETED (Phase 1 - Backend Foundation)

### 1. Database Schema Updates
- ✅ Added `ReviewDecision` model for HIL workflow
  - `validation_check_id`, `reviewer_id`, `decision`, `comment`, `reviewed_at`
- ✅ Updated `Run.status` to include `'reviewed'` state

### 2. Backend API - ApplicationDetails Endpoint
- ✅ `GET /api/v1/applications/id/{id}` - Full application details with run history
  - Returns app metadata, all runs, documents per run, validation summary
  - Supports case-first navigation

## 🚧 IN PROGRESS / REMAINING WORK

### Phase 2: Backend API Endpoints (Estimated: 30-45 min)

#### A. HIL Review Endpoints (`planproof/api/routes/review.py` - NEW FILE)
```python
POST /api/v1/runs/{run_id}/findings/{check_id}/review
  Body: { decision: "accept"|"reject"|"need_info", comment: str, reviewer_id: str }
  Creates ReviewDecision record

GET /api/v1/runs/{run_id}/review-status
  Returns: { total_findings, reviewed_count, pending_count, decisions: [...] }

POST /api/v1/runs/{run_id}/complete-review
  Updates run.status to 'reviewed', triggers report generation
```

#### B. Document Operations
```python
POST /api/v1/runs/{run_id}/reclassify_document
  Body: { document_id: int, document_type: str }
  Override detected document classification

GET /api/v1/runs/{run_id}/documents
  List all documents in a run with details
```

### Phase 3: Frontend Pages (Estimated: 1-2 hours)

#### A. ApplicationDetails.tsx (NEW)
**Route:** `/applications/:applicationId`

**Features:**
- Display application metadata (ref, applicant, date)
- Run history table:
  - Run ID, Start/Complete time, Status, Document count
  - Validation summary (pass/fail/warn/needs_review counts)
  - Actions: [View Results] [Download Report]
- "Upload New Version" button → NewApplication with prefilled ref
- Future: Run comparison feature

**API Calls:**
- `GET /api/v1/applications/id/{id}`

#### B. HILReview.tsx (NEW)
**Route:** `/applications/:applicationId/runs/:runId/review`

**Features:**
- Progress bar: "3 of 12 findings reviewed"
- Sidebar: List of all needs_review findings with status icons
- Main panel per finding:
  - Rule details, severity, message, evidence
  - Decision radio buttons: Accept / Reject / Need More Info
  - Comment textarea (required for Reject/Need Info)
  - Navigation: [Previous] [Next] [Skip]
  - [Save & Continue] button
- At end: [Complete Review] button
- Officer-only access (add auth check)

**API Calls:**
- `GET /api/v1/runs/{runId}/results` - Get findings
- `POST /api/v1/runs/{runId}/findings/{checkId}/review` - Save decision
- `GET /api/v1/runs/{runId}/review-status` - Track progress
- `POST /api/v1/runs/{runId}/complete-review` - Finalize

#### C. Update Results.tsx → RunResults.tsx
**New Route:** `/applications/:applicationId/runs/:runId`

**Changes:**
- Accept both `applicationId` and `runId` from route params
- Remove "Enter Run ID" fallback
- Add document list section with reclassification option
- Display extracted fields in grouped table format
- Group findings by severity (Critical/Warning/Info)
- Add actionable CTAs per finding type:
  - Missing doc → [Upload Document]
  - Misclassification → [Confirm/Override Type]
  - BNG → [Declare Applicability/Exemption]
- Add [Start HIL Review] button if `needs_review > 0`
- Show review progress if partially reviewed
- Add "Back to Application" link

#### D. Update MyCases.tsx
**Changes:**
- Change button text: "View Details" → "Open Case"
- Update navigation: `onClick={() => navigate(`/applications/${caseItem.id}`)}`
- Already shows run_count - keep this

#### E. Update NewApplication.tsx
**Changes:**
- After upload success:
  - Get `application_id` from first response (or from 409 conflict lookup)
  - Redirect to `/applications/${application_id}` instead of `/results/${runId}`
- Update success message: "Documents uploaded! View processing status in Application Details."

### Phase 4: Routing & Integration (Estimated: 15 min)

#### A. Update App.tsx Routes
```typescript
<Route path="/" element={<Navigate to="/new-application" replace />} />
<Route path="/new-application" element={<NewApplication />} />
<Route path="/my-cases" element={<MyCases />} />
<Route path="/applications/:applicationId" element={<ApplicationDetails />} />
<Route path="/applications/:applicationId/runs/:runId" element={<RunResults />} />
<Route path="/applications/:applicationId/runs/:runId/review" element={<HILReview />} />
<Route path="/all-runs" element={<AllRuns />} />
<Route path="/dashboard" element={<Dashboard />} />

// DEPRECATED - keep for backward compat temporarily
<Route path="/results/:runId?" element={<Results />} />
```

#### B. Update API Client (frontend/src/api/client.ts)
```typescript
// Add new methods:
getApplicationDetails(applicationId: number)
submitReviewDecision(runId: number, checkId: number, decision: object)
getReviewStatus(runId: number)
completeReview(runId: number)
reclassifyDocument(runId: number, documentId: number, docType: string)
getRunDocuments(runId: number)
```

### Phase 5: Testing & Polish (Estimated: 30 min)

#### End-to-End Flow Test
1. Upload documents → Redirects to ApplicationDetails
2. Click "Open Case" from My Cases → ApplicationDetails
3. Click "View Results" on a run → RunResults
4. Click "Start HIL Review" → HILReview
5. Review all findings → Complete Review
6. Verify run status = 'reviewed'
7. Download report (future)

#### Edge Cases
- No runs exist for application
- Run still processing
- All findings already reviewed
- Error handling for failed API calls
- Loading states for async operations

## 📊 Progress Summary

**Completed:** 2/12 tasks (17%)  
**Backend:** 2/4 endpoints done (50%)  
**Frontend:** 0/5 pages done (0%)  
**Routing:** 0/2 done (0%)  
**Testing:** 0/1 done (0%)

**Estimated Time Remaining:** 2-3 hours for full implementation

## 🎯 Next Steps

1. **Implement Phase 2A** - HIL Review API endpoints (highest priority)
2. **Implement Phase 3A** - ApplicationDetails page (user-facing, critical)
3. **Implement Phase 3C** - Update Results.tsx (fixes immediate UX issue)
4. **Implement Phase 3D** - Update MyCases (quick fix)
5. **Implement Phase 4** - Routing & API client
6. **Implement Phase 3B** - HIL Review page (officer workflow)
7. **Testing & Polish**

## 📝 Notes

- All backend changes are backward compatible
- Old `/results/:runId` route kept temporarily for compatibility
- Database migration may be needed for ReviewDecision table
- Consider adding auth middleware for HIL Review page
- Future: Run comparison, document version tracking

---

**Last Updated:** Commit f7b3f73  
**Next Commit Target:** Phase 2A (HIL Review endpoints)
