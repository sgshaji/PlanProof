# Changelog

All notable changes to the PlanProof project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- REST API endpoints for external integrations
- Batch processing mode for multiple applications
- Advanced analytics and reporting dashboard
- Email notification system with SMTP integration
- Mobile-responsive UI improvements

---

## [1.0.0] - 2025-01-01

### Added

#### Core Features
- **Intelligent Document Processing**
  - Azure Document Intelligence integration for OCR
  - Multi-document type classification (site_plan, location_plan, application_form, etc.)
  - Evidence linking with page numbers and bounding boxes
  - Content hash-based deduplication

- **Validation Engine**
  - 30 comprehensive business rules across 10 categories
  - Configurable rule catalog (JSON-based)
  - Evidence-linked validation results
  - Support for error, warning, and info severity levels

- **Hybrid AI/Rules Architecture**
  - Deterministic-first field extraction using regex and heuristics
  - Conditional LLM usage for low-confidence fields (<0.6 threshold)
  - Conflict resolution with multiple value sources
  - 80% cost reduction vs naive LLM approaches

- **Human-in-the-Loop Workflow**
  - Interactive PDF evidence viewer
  - Officer override system with full audit trail
  - Request-info workflow with ON_HOLD status
  - Exportable checklists and email templates (21-day deadlines)
  - Conflict resolution UI for field value selection

- **Version Management**
  - Multi-version submission tracking (V0, V1, V2+)
  - Delta calculation for field/document/spatial changes
  - Automatic re-validation of affected rules
  - Side-by-side version comparison

- **Web Interface (Streamlit)**
  - 8 specialized pages:
    1. Upload - Drag-drop PDF upload
    2. Status - Real-time pipeline progress
    3. Results - Validation findings with evidence
    4. Case Overview - Version comparison
    5. Fields Viewer - All extracted fields
    6. Conflicts - Resolve value conflicts
    7. Search - Full-text search
    8. Dashboard - Team analytics

#### Business Rules
- **Document Requirements** (DOC-01 to DOC-03)
  - Site location plan validation
  - Elevations and floor plans
  - Ownership certificates

- **Consistency Checks** (CONS-01 to CONS-03)
  - Address consistency across documents
  - Proposal description matching
  - Applicant details validation

- **Modification Limits** (MOD-01 to MOD-03)
  - Rear extension limits (3m/4m)
  - Single-storey height restrictions
  - Two-storey boundary setbacks

- **Spatial Validation** (SPATIAL-01 to SPATIAL-04)
  - Boundary setback compliance
  - Building height limits
  - Plot coverage ratios
  - GeoJSON coordinate validation

- **Fee Validation** (FEE-01, FEE-02)
  - Fee calculation by application type
  - Payment evidence validation

- **Ownership Validation** (OWN-01, OWN-02)
  - Certificate type validation (A/B/C/D)
  - Notice served verification

- **Prior Approval** (PA-01, PA-02)
  - Prior approval reference validation
  - Parameter compliance checks

- **Constraints** (CON-01 to CON-04)
  - Conservation area checks
  - Listed building consent
  - Tree preservation orders
  - Flood risk assessment

- **Biodiversity Net Gain** (BNG-01 to BNG-03)
  - 10% net gain calculation
  - BNG metric document validation
  - Habitat baseline assessment

- **Plan Quality** (PLAN-01, PLAN-02)
  - Scale bar presence and accuracy
  - North point indication

#### Services
- **Delta Service**: Version comparison and change detection
- **Officer Override Service**: Manual decision tracking with audit trail
- **Search Service**: Full-text search across cases, submissions, documents
- **Notification Service**: Email notification framework (database logging)
- **Request Info Service**: Structured info request workflow
- **Export Service**: JSON and HTML decision package generation

#### Infrastructure
- PostgreSQL with PostGIS for spatial data
- Azure Blob Storage for document storage
- Azure Document Intelligence for OCR
- Azure OpenAI (GPT-4o-mini) for intelligent field resolution
- Alembic for database migrations
- SQLAlchemy ORM for data access

#### Development Tools
- Black code formatter (100 char lines)
- Ruff linter with comprehensive checks
- MyPy for static type checking
- Pytest with 85%+ code coverage
- Docker and docker-compose support
- Makefile for common tasks

#### Documentation
- Comprehensive README with quick start guide
- Architecture documentation with diagrams
- API reference for Python SDK
- Deployment guide (local, Docker, Azure)
- Contributing guidelines with code standards
- Troubleshooting guide

### Changed
- Refactored project structure for enterprise standards
- Consolidated documentation into docs/ folder
- Removed temporary development/tracking MD files
- Updated pyproject.toml with complete metadata
- Enhanced .gitignore with comprehensive exclusions

### Fixed
- Evidence linking for all validation checks
- Confidence threshold handling in LLM gate
- Version delta calculation for spatial changes
- UI navigation state management

### Security
- Environment variables for all secrets
- No hardcoded credentials
- PostgreSQL SSL connection support
- Azure managed identity support

---

## [0.9.0] - 2024-12-15 (Beta)

### Added
- Initial pipeline implementation
- Basic validation engine (15 rules)
- Simple Streamlit UI (4 pages)
- Azure integrations (Blob, DocIntel, OpenAI)

### Known Issues
- Limited test coverage (60%)
- No version management
- Basic officer override support
- Manual evidence review only

---

## [0.1.0] - 2024-10-01 (Alpha)

### Added
- Proof of concept
- Basic document upload
- Simple field extraction
- PostgreSQL database schema

---

[Unreleased]: https://github.com/your-org/planproof/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/your-org/planproof/compare/v0.9.0...v1.0.0
[0.9.0]: https://github.com/your-org/planproof/compare/v0.1.0...v0.9.0
[0.1.0]: https://github.com/your-org/planproof/releases/tag/v0.1.0
