# Repository Structure Proposal - PlanProof

## Executive Summary

This proposal outlines a professional-grade repository reorganization for PlanProof to achieve:
- **Clear separation of concerns** (backend, frontend, infrastructure)
- **Improved discoverability** (find what you need in seconds)
- **Professional presentation** (production-ready open source project)
- **Easy onboarding** (new developers up and running in 5 minutes)
- **Enterprise standards** (follows industry best practices)

---

## 🎯 Proposed Repository Structure

```
planproof/
├── README.md                          # Main project documentation
├── LICENSE                            # MIT License
├── .gitignore                         # Git ignore patterns
├── .dockerignore                      # Docker ignore patterns
├── .env.example                       # Environment template with comments
├── docker-compose.yml                 # Production Docker compose
├── docker-compose.dev.yml             # Development Docker compose
├── Makefile                           # Common commands (make install, make test, etc.)
│
├── backend/                           # Python Backend (FastAPI + Business Logic)
│   ├── README.md                      # Backend-specific setup guide
│   ├── Dockerfile                     # Backend Docker image
│   ├── pyproject.toml                 # Modern Python project config
│   ├── requirements.txt               # Production dependencies
│   ├── requirements-dev.txt           # Development dependencies
│   ├── alembic.ini                    # Database migrations config
│   ├── main.py                        # FastAPI app entry point
│   ├── run_api.py                     # Development server runner
│   │
│   ├── alembic/                       # Database migrations
│   │   ├── versions/                  # Migration scripts
│   │   └── env.py                     # Alembic environment
│   │
│   ├── planproof/                     # Main Python package
│   │   ├── __init__.py
│   │   ├── config.py                  # Configuration management
│   │   ├── db.py                      # Database models (SQLAlchemy)
│   │   ├── main.py                    # FastAPI app initialization
│   │   │
│   │   ├── api/                       # REST API endpoints
│   │   │   ├── __init__.py
│   │   │   ├── v1/                    # API version 1
│   │   │   │   ├── __init__.py
│   │   │   │   ├── applications.py    # Application endpoints
│   │   │   │   ├── submissions.py     # Submission endpoints
│   │   │   │   ├── runs.py            # Run endpoints
│   │   │   │   ├── documents.py       # Document endpoints
│   │   │   │   └── health.py          # Health check
│   │   │   └── dependencies.py        # FastAPI dependencies
│   │   │
│   │   ├── services/                  # Business logic services
│   │   │   ├── __init__.py
│   │   │   ├── application_service.py
│   │   │   ├── submission_service.py
│   │   │   ├── document_service.py
│   │   │   ├── storage_service.py     # Azure Blob Storage
│   │   │   └── ai_service.py          # Azure OpenAI integration
│   │   │
│   │   ├── pipeline/                  # Processing pipeline
│   │   │   ├── __init__.py
│   │   │   ├── ingest.py              # Document ingestion
│   │   │   ├── extract.py             # Field extraction
│   │   │   ├── validate.py            # Validation engine
│   │   │   ├── validators/            # Validation modules
│   │   │   │   ├── __init__.py
│   │   │   │   ├── constants.py
│   │   │   │   ├── field_validators.py
│   │   │   │   ├── document_validators.py
│   │   │   │   └── consistency_validators.py
│   │   │   └── formatters/            # Output formatters
│   │   │       └── field_formatter.py
│   │   │
│   │   ├── rules/                     # Validation rules catalog
│   │   │   ├── __init__.py
│   │   │   ├── catalog.py             # Rule catalog parser
│   │   │   └── README.md              # Rule authoring guide
│   │   │
│   │   ├── models/                    # Pydantic schemas
│   │   │   ├── __init__.py
│   │   │   ├── application.py
│   │   │   ├── submission.py
│   │   │   ├── document.py
│   │   │   └── validation.py
│   │   │
│   │   └── utils/                     # Utility functions
│   │       ├── __init__.py
│   │       ├── azure_client.py
│   │       ├── pdf_utils.py
│   │       └── text_processing.py
│   │
│   ├── tests/                         # Backend tests
│   │   ├── __init__.py
│   │   ├── conftest.py                # Pytest fixtures
│   │   ├── unit/                      # Unit tests
│   │   │   ├── test_validators.py
│   │   │   ├── test_extractors.py
│   │   │   └── test_services.py
│   │   └── integration/               # Integration tests
│   │       ├── test_api.py
│   │       └── test_pipeline.py
│   │
│   └── scripts/                       # Backend utility scripts
│       ├── build_rule_catalog.py
│       ├── db_init.py
│       └── seed_data.py
│
├── frontend/                          # React Frontend (Vite + TypeScript)
│   ├── README.md                      # Frontend-specific setup guide
│   ├── Dockerfile                     # Frontend Docker image
│   ├── nginx.conf                     # Production nginx config
│   ├── package.json                   # Node.js dependencies
│   ├── package-lock.json
│   ├── tsconfig.json                  # TypeScript config
│   ├── vite.config.ts                 # Vite bundler config
│   ├── index.html                     # HTML entry point
│   │
│   ├── public/                        # Static assets
│   │   ├── favicon.ico
│   │   └── logo.svg
│   │
│   ├── src/                           # Source code
│   │   ├── main.tsx                   # React entry point
│   │   ├── App.tsx                    # Main App component
│   │   ├── theme.ts                   # MUI theme configuration
│   │   │
│   │   ├── api/                       # API client
│   │   │   ├── client.ts              # Axios configuration
│   │   │   ├── errorUtils.ts          # Error handling
│   │   │   └── types.ts               # TypeScript interfaces
│   │   │
│   │   ├── pages/                     # Page components
│   │   │   ├── Dashboard.tsx
│   │   │   ├── ApplicationDetails.tsx
│   │   │   ├── Results.tsx
│   │   │   ├── HILReview.tsx
│   │   │   └── NotFound.tsx
│   │   │
│   │   ├── components/                # Reusable UI components
│   │   │   ├── DocumentViewer.tsx
│   │   │   ├── ValidationFindingsDisplay.tsx
│   │   │   ├── ExtractedFieldsDisplay.tsx
│   │   │   ├── LLMTransparency.tsx
│   │   │   └── Layout/
│   │   │       ├── Header.tsx
│   │   │       └── Sidebar.tsx
│   │   │
│   │   ├── hooks/                     # Custom React hooks
│   │   │   └── usePolling.ts
│   │   │
│   │   └── utils/                     # Utility functions
│   │       └── formatters.ts
│   │
│   └── tests/                         # Frontend tests
│       ├── unit/                      # Component tests
│       └── e2e/                       # End-to-end tests (Playwright)
│           └── playwright.config.ts
│
├── infrastructure/                    # Infrastructure as Code
│   ├── README.md                      # Deployment guide
│   ├── docker/                        # Docker configurations
│   │   ├── backend.Dockerfile
│   │   ├── frontend.Dockerfile
│   │   └── nginx.conf
│   │
│   ├── terraform/                     # Azure infrastructure (future)
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   │
│   └── scripts/                       # Deployment scripts
│       ├── deploy-production.sh
│       └── setup-azure.sh
│
├── artifacts/                         # Project artifacts (not code)
│   ├── rule_catalog.json              # Validation rules catalog
│   ├── validation_requirements.md    # Business rules documentation
│   └── sample_data/                   # Sample test data
│       ├── test_documents/
│       └── test_submissions/
│
├── docs/                              # Project documentation
│   ├── README.md                      # Documentation index
│   ├── 01-getting-started/
│   │   ├── installation.md
│   │   ├── quickstart.md
│   │   └── configuration.md
│   │
│   ├── 02-architecture/
│   │   ├── overview.md
│   │   ├── backend-architecture.md
│   │   ├── frontend-architecture.md
│   │   ├── database-schema.md
│   │   └── data-flow.md
│   │
│   ├── 03-api/
│   │   ├── api-reference.md
│   │   ├── authentication.md
│   │   └── integration-guide.md
│   │
│   ├── 04-development/
│   │   ├── contributing.md
│   │   ├── coding-standards.md
│   │   ├── testing-guide.md
│   │   └── adding-validation-rules.md
│   │
│   ├── 05-deployment/
│   │   ├── docker-deployment.md
│   │   ├── azure-deployment.md
│   │   └── production-checklist.md
│   │
│   └── 06-troubleshooting/
│       ├── common-issues.md
│       ├── debugging.md
│       └── faq.md
│
└── .github/                           # GitHub specific files
    ├── workflows/                     # CI/CD pipelines
    │   ├── backend-tests.yml
    │   ├── frontend-tests.yml
    │   └── deploy-production.yml
    │
    ├── ISSUE_TEMPLATE/
    │   ├── bug_report.md
    │   └── feature_request.md
    │
    ├── PULL_REQUEST_TEMPLATE.md
    └── CODEOWNERS
```

---

## 📋 Files to MOVE (from root to proper locations)

### Move to `backend/scripts/`:
- `add_columns.py`
- `check_runs.py`
- `check_schema.py`
- `fix_existing_runs.py`
- `fix_schema.py`
- `validate_schema.py`
- `test_*.py` (all test files at root)

### Move to `backend/`:
- `main.py`
- `run_api.py`
- `alembic/` and `alembic.ini`
- `planproof/` package
- `pyproject.toml`
- `requirements*.txt`

### Move to `infrastructure/scripts/`:
- `setup-dev.ps1` / `setup-dev.sh`
- `start_api.ps1` / `start_servers.sh`
- `start-docker-api.*`
- `provision-storage.ps1`
- `fix-cors.ps1`
- `test-tunnel-deployment.sh`
- `test_ui_automated.sh`

### Move to `infrastructure/docker/`:
- `Dockerfile` → `backend.Dockerfile`
- `Dockerfile.api` → (consolidate with above)
- `docker-entrypoint.sh`
- Frontend `Dockerfile` → `frontend.Dockerfile`

### Move to `artifacts/`:
- `artefacts/` → rename to `artifacts/`
- `data/` → `artifacts/sample_data/`
- `runs/` → (consider if needed, might be runtime data)

### Move to `docs/`:
All the uppercase `.md` files in root should be organized into docs:
- Documentation files (all the implementation guides, status docs)
- Setup guides
- Architecture docs

### ARCHIVE (move to `archive/` or delete):
- `CURRENT_STATUS.md` (outdated)
- `FIXES_SUMMARY.md` (outdated)
- `IMPLEMENTATION_COMPLETE.md` (outdated)
- `IMPLEMENTATION_SUMMARY.md` (outdated)
- `PR_DESCRIPTION.md` (temporary)
- `TEST_RESULTS.md` (outdated)
- `TESTING_COMPLETE.md` (outdated)
- `UX_IMPROVEMENTS_SUMMARY.md` (outdated)
- `SCHEMA_COMPARISON.md` (outdated)
- `REPOSITORY_REORGANIZATION.md` (this was a previous proposal)

---

## 🎨 New README.md Structure

```markdown
# PlanProof - AI-Powered Planning Application Validation

<div align="center">

**🏛️ Enterprise-Grade Planning Application Processing System 🏛️**

[![CI/CD](https://github.com/sgshaji/PlanProof/workflows/CI/badge.svg)](https://github.com/sgshaji/PlanProof/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178c6.svg)](https://www.typescriptlang.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Automate 80%+ of planning validation with 100% auditability**

[🚀 Quick Start](#quick-start) • [📖 Docs](docs/) • [🏗️ Architecture](docs/02-architecture/overview.md) • [🔌 API](docs/03-api/api-reference.md) • [🤝 Contributing](docs/04-development/contributing.md)

</div>

---

## 🎯 What is PlanProof?

PlanProof automates UK planning application validation using AI and rule-based processing. Built for planning authorities who need:

- ✅ **80%+ automation** while maintaining 100% auditability
- 💰 **Cost efficiency** - deterministic-first approach minimizes AI costs
- 🔍 **Evidence-backed decisions** - every finding linked to source documents
- 👥 **Human oversight** - officers retain full control with override capabilities
- 🚀 **Fast deployment** - Docker-based setup in under 5 minutes

---

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| **📄 Document Processing** | OCR and extraction from complex PDF submissions |
| **🤖 30+ Validation Rules** | Automated checks for completeness, consistency, and compliance |
| **📊 Evidence Linking** | Every finding includes page numbers and text snippets |
| **🔄 Version Tracking** | Full modification history (V0 → V1 → V2) with delta detection |
| **👥 Modern UI** | React-based interface for planning officers |
| **🔌 REST API** | Complete API for integration with existing systems |

---

## 🛠️ Technology Stack

**Backend:**
- Python 3.11+ with FastAPI
- PostgreSQL 13+ (with PostGIS)
- Azure OpenAI (GPT-4)
- Azure Document Intelligence
- Azure Blob Storage

**Frontend:**
- React 18 with TypeScript
- Material-UI (MUI)
- Vite build tool

**Infrastructure:**
- Docker & Docker Compose
- Nginx (production)
- GitHub Actions (CI/CD)

---

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Azure account with:
  - Azure OpenAI (GPT-4 deployment)
  - Azure Document Intelligence
  - Azure Blob Storage
  - Azure Database for PostgreSQL (or local PostgreSQL)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/sgshaji/PlanProof.git
   cd PlanProof
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your Azure credentials
   ```

3. **Start with Docker** (Recommended)
   ```bash
   docker-compose up -d
   ```

4. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000/docs
   - Database: localhost:5432

### Manual Setup

See [Installation Guide](docs/01-getting-started/installation.md) for detailed instructions.

---

## 📖 Documentation

- **Getting Started**
  - [Installation Guide](docs/01-getting-started/installation.md)
  - [Quick Start Tutorial](docs/01-getting-started/quickstart.md)
  - [Configuration Guide](docs/01-getting-started/configuration.md)

- **Architecture**
  - [System Overview](docs/02-architecture/overview.md)
  - [Backend Architecture](docs/02-architecture/backend-architecture.md)
  - [Database Schema](docs/02-architecture/database-schema.md)

- **API Reference**
  - [API Documentation](docs/03-api/api-reference.md)
  - [Integration Guide](docs/03-api/integration-guide.md)

- **Development**
  - [Contributing Guide](docs/04-development/contributing.md)
  - [Testing Guide](docs/04-development/testing-guide.md)
  - [Adding Validation Rules](docs/04-development/adding-validation-rules.md)

- **Deployment**
  - [Docker Deployment](docs/05-deployment/docker-deployment.md)
  - [Azure Deployment](docs/05-deployment/azure-deployment.md)

---

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](docs/04-development/contributing.md).

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Azure OpenAI and Document Intelligence for AI capabilities
- FastAPI and React communities for excellent frameworks
- UK Planning Inspectorate for validation requirements reference

---

## 📞 Support

- 📧 Email: support@planproof.com
- 💬 GitHub Issues: [Report a bug](https://github.com/sgshaji/PlanProof/issues)
- 📚 Documentation: [docs/](docs/)

---

<div align="center">
Made with ❤️ for UK Planning Authorities
</div>
```

---

## 🎯 Migration Plan

### Phase 1: Preparation (Week 1)
1. Create new directory structure in a branch
2. Move files systematically
3. Update all import paths in code
4. Update configuration files

### Phase 2: Documentation (Week 1-2)
1. Rewrite README.md
2. Organize existing docs into new structure
3. Archive outdated docs
4. Create missing documentation

### Phase 3: Testing (Week 2)
1. Test backend with new structure
2. Test frontend with new structure
3. Test Docker builds
4. Update CI/CD pipelines

### Phase 4: Deployment (Week 2-3)
1. Merge to main branch
2. Update deployment scripts
3. Update production environment
4. Announce changes to team

---

## 📊 Benefits of New Structure

| Before | After |
|--------|-------|
| 50+ files in root | Clean root with 10-15 essential files |
| Unclear technology stack | Clear separation: backend/, frontend/, infrastructure/ |
| Scattered documentation | Organized docs/ with logical hierarchy |
| Hard to find scripts | Consolidated in backend/scripts/ and infrastructure/scripts/ |
| Multiple Docker files without clear purpose | Organized in infrastructure/docker/ |
| README with 566 lines | Concise README pointing to organized docs |
| Test files scattered | All tests in tests/ subdirectories |

---

## ✅ Quality Standards

### Professional Repository Checklist

- ✅ Clear README with badges, quick start, and links
- ✅ Organized documentation in docs/ folder
- ✅ Separate backend and frontend directories
- ✅ Infrastructure as code in dedicated folder
- ✅ All scripts in designated locations
- ✅ Clean root directory (< 15 files)
- ✅ .env.example with clear comments
- ✅ Contributing guide
- ✅ CI/CD workflows
- ✅ Issue and PR templates
- ✅ License file
- ✅ Proper .gitignore and .dockerignore
- ✅ Consistent naming conventions
- ✅ Clear separation of concerns

---

## 🚀 Next Steps

1. **Review this proposal** with the team
2. **Create a `reorganize` branch** to implement changes
3. **Move files systematically** following the structure
4. **Update all imports** and configuration paths
5. **Test thoroughly** before merging
6. **Update documentation** to reflect new structure
7. **Merge to main** and celebrate! 🎉

---

*This proposal follows industry best practices for Python (PEP 518, src layout) and TypeScript/React projects, drawing inspiration from successful open-source projects like FastAPI, Django, and Create React App.*
