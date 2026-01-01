# Enhanced Issue Model Specification

## Current Output Format (from validation_83.json)

```json
{
  "status": "fail",
  "severity": "error",
  "message": "Missing required documents: application_form",
  "missing_fields": ["application_form"],
  "evidence": {
    "evidence_snippets": [...],
    "present_documents": [],
    "missing_documents": ["application_form"]
  }
}
```

**Problems:**
- Generic message
- No actionable guidance
- No candidate suggestions
- No resolution tracking

---

## Target Enhanced Format

```json
{
  "issue_id": "DOC-001-APP-FORM",
  "rule_id": "DOC-01",
  "status": "fail",
  "severity": "error",
  "category": "document_missing",
  
  "who_can_fix": "applicant",  // or "officer", "either"
  
  "user_message": {
    "title": "Application form missing",
    "subtitle": "Required",
    "description": "We couldn't find the completed planning application form in your upload. This is required to validate the application.",
    "impact": "Your application cannot proceed without this document."
  },
  
  "what_we_checked": {
    "summary": "We searched for documents containing application form fields, signatures, or titled 'Application Form', '1APP', 'Planning Application Form'",
    "methods": ["document_classification", "text_pattern_matching", "form_field_detection"],
    "documents_scanned": 3,
    "confidence_threshold": 0.7
  },
  
  "evidence": {
    "candidates": [
      {
        "document_id": 82,
        "filename": "Document-92C2F0E3D233D9722023BD0BAA17C379.pdf",
        "confidence": 0.45,
        "reason": "Contains form-like structure but missing key fields",
        "preview_snippet": "APPLICATION TO DEMOLISH A BUILDING..."
      }
    ],
    "checked_locations": [
      "All uploaded PDFs",
      "Document metadata",
      "Text content analysis"
    ]
  },
  
  "required_upload_types": ["application_form"],
  
  "actions": {
    "primary": {
      "type": "upload",
      "label": "Upload Application Form",
      "accepts": ".pdf",
      "expected_filename_patterns": [
        "*application*form*.pdf",
        "*1APP*.pdf",
        "*planning*form*.pdf"
      ],
      "help_text": "Upload the completed planning application form PDF",
      "example": "Application_Form_2025.pdf"
    },
    "secondary": [
      {
        "type": "confirm_candidate",
        "label": "Confirm Document-92C2F0E3D233D9722023BD0BAA17C379.pdf as Application Form",
        "document_id": 82,
        "enabled": true
      },
      {
        "type": "mark_not_required",
        "label": "This application doesn't require an application form",
        "requires_reason": true,
        "requires_officer_approval": true,
        "enabled": false,
        "disabled_reason": "Application forms are mandatory for all application types"
      }
    ]
  },
  
  "resolution": {
    "status": "pending",  // or "resolved", "officer_review", "user_acknowledged"
    "resolved_at": null,
    "resolved_by": null,
    "resolution_method": null,  // "upload", "confirmation", "override"
    "recheck_rules": ["DOC-01", "PA-02"],  // Rules to re-run after fix
    "dependent_issues": ["PA-02-MISSING-PA-DOCS"]  // Other issues that may resolve
  },
  
  "metadata": {
    "created_at": "2025-12-31T08:12:05Z",
    "updated_at": "2025-12-31T08:12:05Z",
    "recheck_count": 0,
    "user_viewed": false,
    "user_dismissed": false
  }
}
```

---

## Example: All 10 Issues in Enhanced Format

### 1. Missing Application Form

```json
{
  "issue_id": "DOC-001-APP-FORM",
  "rule_id": "DOC-01",
  "status": "fail",
  "severity": "error",
  "category": "document_missing",
  "who_can_fix": "applicant",
  "user_message": {
    "title": "Application form missing",
    "subtitle": "Required",
    "description": "We couldn't find the completed planning application form.",
    "impact": "Your application cannot proceed without this document."
  },
  "actions": {
    "primary": {
      "type": "upload",
      "label": "Upload Application Form",
      "accepts": ".pdf"
    }
  },
  "required_upload_types": ["application_form"],
  "resolution": {
    "recheck_rules": ["DOC-01", "PA-02"]
  }
}
```

### 2. Missing Site Plan

```json
{
  "issue_id": "DOC-002-SITE-PLAN",
  "rule_id": "DOC-02",
  "status": "fail",
  "severity": "error",
  "category": "document_missing",
  "who_can_fix": "applicant",
  "user_message": {
    "title": "Site plan missing",
    "subtitle": "Required",
    "description": "We didn't detect a site plan showing the proposed works on the site boundary.",
    "impact": "Site plans are required to show the location and extent of works."
  },
  "what_we_checked": {
    "summary": "We looked for drawings titled: Site Plan, Proposed Site Plan, Block Plan, scales 1:200/1:500, red-line boundary"
  },
  "actions": {
    "primary": {
      "type": "upload",
      "label": "Upload Site Plan",
      "help_text": "Upload a site plan at scale 1:200 or 1:500 showing the site boundary",
      "example": "Site_Plan_1-500.pdf"
    }
  },
  "required_upload_types": ["site_plan"]
}
```

### 3. Missing Elevations

```json
{
  "issue_id": "DOC-003-ELEVATION",
  "rule_id": "DOC-03",
  "status": "fail",
  "severity": "error",
  "category": "document_missing",
  "who_can_fix": "applicant",
  "user_message": {
    "title": "Elevations missing",
    "subtitle": "Required",
    "description": "Elevation drawings (front/side/rear) weren't found. These show the external appearance of the proposal.",
    "impact": "Elevations are required to assess the visual impact of the development."
  },
  "actions": {
    "primary": {
      "type": "upload",
      "label": "Upload Elevations",
      "help_text": "Upload elevation drawings for all affected sides",
      "example": "Proposed_Elevations.pdf"
    }
  },
  "required_upload_types": ["elevation"]
}
```

### 4. Missing Floor Plans

```json
{
  "issue_id": "DOC-004-FLOOR-PLAN",
  "rule_id": "DOC-04",
  "status": "fail",
  "severity": "error",
  "category": "document_missing",
  "who_can_fix": "applicant",
  "user_message": {
    "title": "Floor plans missing",
    "subtitle": "Required",
    "description": "Floor plan drawings weren't found. These show internal layout by level.",
    "impact": "Floor plans are required to understand the proposed internal arrangement."
  },
  "actions": {
    "primary": {
      "type": "upload",
      "label": "Upload Floor Plans",
      "help_text": "Upload floor plans for each level (ground/first/loft)",
      "example": "Floor_Plans_All_Levels.pdf"
    }
  },
  "required_upload_types": ["floor_plan"]
}
```

### 5. Missing Design Statement

```json
{
  "issue_id": "DOC-005-DESIGN-STMT",
  "rule_id": "DOC-05",
  "status": "fail",
  "severity": "warning",
  "category": "document_missing",
  "who_can_fix": "applicant",
  "user_message": {
    "title": "Design & Access Statement not found",
    "subtitle": "Optional but recommended",
    "description": "This isn't always required, but it often helps avoid follow-up requests.",
    "impact": "May result in additional information requests during assessment."
  },
  "actions": {
    "primary": {
      "type": "upload",
      "label": "Upload Design Statement",
      "optional": true
    },
    "secondary": [
      {
        "type": "mark_not_required",
        "label": "Not provided (optional for this application)",
        "enabled": true
      }
    ]
  },
  "required_upload_types": ["design_statement"]
}
```

### 6. Missing Location Plan

```json
{
  "issue_id": "DOC-006-LOCATION",
  "rule_id": "DOC-06",
  "status": "fail",
  "severity": "error",
  "category": "document_missing",
  "who_can_fix": "applicant",
  "user_message": {
    "title": "Location plan missing",
    "subtitle": "Required",
    "description": "We didn't find a location plan (usually 1:1250 or 1:2500) showing the site with a red outline.",
    "impact": "Location plans are legally required for all applications."
  },
  "what_we_checked": {
    "summary": "We searched for 'Location Plan', 'Site Location Plan', OS map tiles, scales 1:1250/1:2500"
  },
  "actions": {
    "primary": {
      "type": "upload",
      "label": "Upload Location Plan",
      "help_text": "Upload an Ordnance Survey based plan at 1:1250 or 1:2500 with site outlined in red",
      "example": "Location_Plan_1-1250.pdf"
    }
  },
  "required_upload_types": ["location_plan"],
  "resolution": {
    "recheck_rules": ["DOC-06", "PA-02"]
  }
}
```

### 7. Not Registered in M3

```json
{
  "issue_id": "PA-001-M3-REG",
  "rule_id": "PA-01",
  "status": "fail",
  "severity": "error",
  "category": "officer_action_required",
  "who_can_fix": "officer",
  "user_message": {
    "title": "M3 registration not confirmed",
    "subtitle": "Officer check required",
    "description": "Prior Approval cases require manual registration in M3. Please confirm registration status.",
    "impact": "Application cannot proceed until M3 registration is confirmed.",
    "officer_note": true
  },
  "actions": {
    "primary": {
      "type": "officer_confirm",
      "label": "Confirm M3 Registration",
      "requires_officer_role": true,
      "requires_m3_reference": true
    }
  },
  "resolution": {
    "status": "awaiting_officer"
  }
}
```

### 8. Missing PA Required Docs

```json
{
  "issue_id": "PA-002-REQ-DOCS",
  "rule_id": "PA-02",
  "status": "fail",
  "severity": "error",
  "category": "document_missing",
  "who_can_fix": "applicant",
  "user_message": {
    "title": "Prior Approval mandatory documents missing",
    "subtitle": "Required",
    "description": "Prior Approval applications must include: Application Form and Location Plan. One or both are missing.",
    "impact": "Prior Approval cannot be determined without these mandatory documents."
  },
  "missing_items": [
    {
      "type": "application_form",
      "label": "Application Form",
      "status": "missing",
      "links_to": "DOC-001-APP-FORM"
    },
    {
      "type": "location_plan",
      "label": "Location Plan",
      "status": "missing",
      "links_to": "DOC-006-LOCATION"
    }
  ],
  "actions": {
    "primary": {
      "type": "bulk_upload",
      "label": "Upload Missing PA Documents",
      "required_types": ["application_form", "location_plan"]
    }
  },
  "resolution": {
    "depends_on": ["DOC-001-APP-FORM", "DOC-006-LOCATION"],
    "auto_resolve": true
  }
}
```

### 9. BNG Applicability Not Determined

```json
{
  "issue_id": "BNG-001-APPLICABILITY",
  "rule_id": "BNG-01",
  "status": "fail",
  "severity": "warning",
  "category": "information_missing",
  "who_can_fix": "applicant",
  "user_message": {
    "title": "Biodiversity Net Gain (BNG) status not stated",
    "subtitle": "Clarification needed",
    "description": "We couldn't find a clear statement on whether BNG applies or is exempt. This often triggers follow-up during validation.",
    "impact": "May delay application assessment.",
    "context": "Since February 2024, most developments require 10% biodiversity net gain or must demonstrate exemption."
  },
  "actions": {
    "primary": {
      "type": "select_option",
      "label": "Specify BNG Status",
      "options": [
        {
          "value": "applies",
          "label": "BNG applies to this development",
          "next_action": "upload_bng_assessment"
        },
        {
          "value": "exempt",
          "label": "Claim BNG exemption",
          "next_action": "provide_exemption_reason"
        },
        {
          "value": "not_sure",
          "label": "Not sure - request guidance",
          "next_action": "officer_review"
        }
      ]
    }
  },
  "resolution": {
    "recheck_rules": ["BNG-01", "BNG-02", "BNG-03"]
  }
}
```

### 10. BNG Exemption Reason Missing

```json
{
  "issue_id": "BNG-003-EXEMPTION",
  "rule_id": "BNG-03",
  "status": "fail",
  "severity": "warning",
  "category": "information_missing",
  "who_can_fix": "applicant",
  "user_message": {
    "title": "BNG exemption reason missing",
    "subtitle": "Justification required",
    "description": "You've indicated BNG is exempt, but we couldn't find the exemption reason. Please provide the specific exemption basis.",
    "impact": "Exemption claims must be justified to avoid assessment delays."
  },
  "evidence": {
    "what_we_found": {
      "snippet": "BNG not applicable",
      "source": "extraction_83.json",
      "confidence": 0.7
    }
  },
  "actions": {
    "primary": {
      "type": "provide_text",
      "label": "Provide Exemption Reason",
      "help_text": "Explain why BNG does not apply to this development",
      "examples": [
        "Householder application (residential extension)",
        "Site area under 25 square metres",
        "Self-build or custom housebuilding",
        "Development of existing dwelling"
      ],
      "max_length": 500
    },
    "secondary": [
      {
        "type": "upload",
        "label": "Upload BNG Exemption Statement",
        "optional": true
      }
    ]
  }
}
```

---

## Implementation: Issue Aggregation & Smart Grouping

### Group Related Issues

```json
{
  "issue_groups": [
    {
      "group_id": "missing-core-docs",
      "title": "Missing Core Documents",
      "severity": "error",
      "count": 5,
      "issues": ["DOC-001-APP-FORM", "DOC-002-SITE-PLAN", "DOC-006-LOCATION", ...],
      "bulk_action": {
        "type": "bulk_upload",
        "label": "Upload All Required Documents"
      }
    },
    {
      "group_id": "bng-clarification",
      "title": "BNG Clarification Needed",
      "severity": "warning",
      "count": 2,
      "issues": ["BNG-001-APPLICABILITY", "BNG-003-EXEMPTION"]
    }
  ]
}
```

### Resolution Tracking

```json
{
  "resolution_progress": {
    "total_issues": 10,
    "blocking_errors": 7,
    "warnings": 3,
    "resolved": 0,
    "pending_user": 8,
    "pending_officer": 2,
    "can_proceed": false
  }
}
```

---

## UI Components Needed

1. **Issue Card Component**
   - Expandable/collapsible
   - Shows status badge (error/warning/resolved)
   - Action buttons
   - Evidence section
   - Resolution timeline

2. **Bulk Action Panel**
   - Upload multiple docs at once
   - Auto-classify and match to issues
   - Show match confidence
   - Confirm/reject suggestions

3. **Resolution Tracker**
   - Progress bar
   - Checklist of issues
   - Quick actions

4. **Officer Panel** (for officer-only issues)
   - Filter by who_can_fix
   - Approval/override controls
   - M3 reference input

---

**Ready to implement?** We can:
1. Update the validation pipeline to output this enhanced format
2. Create the UI components
3. Add the resolution tracking logic
4. Implement auto-recheck on document upload
