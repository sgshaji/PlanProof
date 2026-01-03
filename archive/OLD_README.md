# PlanProof - AI-Powered Planning Application Validation

<div align="center">

**🏛️ Automated Planning Application Processing & Validation System 🏛️**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Azure](https://img.shields.io/badge/azure-enabled-0078D4.svg)](https://azure.microsoft.com/)
[![PostgreSQL](https://img.shields.io/badge/postgresql-13+-336791.svg)](https://www.postgresql.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-UI-FF4B4B.svg)](https://streamlit.io/)

**Automate 80%+ of planning validation with 100% auditability**

[🚀 Quick Start](#-quick-start) • [📖 Documentation](docs/) • [🏗️ Architecture](docs/ARCHITECTURE.md) • [🔌 API Guide](docs/API_INTEGRATION_GUIDE.md)

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [Quick Start](#-quick-start)
- [Architecture](#-architecture)
- [API Integration](#-api-integration)
- [Development](#-development)
- [Deployment](#-deployment)
- [Documentation](#-documentation)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🎯 Overview

**PlanProof** is an enterprise-grade AI validation system designed for UK planning authorities to automate the review of planning applications. It combines deterministic rule-based validation with intelligent AI processing to deliver accuracy, auditability, and cost-efficiency.

### The Challenge

Planning authorities process thousands of applications annually, each requiring:
- Manual extraction of data from complex PDFs
- Validation against 30+ planning regulations
- Evidence-backed decision making with audit trails
- Version tracking and change detection for revisions
- Officer oversight and override capabilities
- Cost-effective processing at scale

### The Solution

PlanProof automates **80%+ of the validation process** while maintaining:

| Feature | Benefit |
|---------|---------|
| **100% Auditability** | Every decision linked to source evidence with page references |
| **Cost Efficiency** | Deterministic-first approach minimizes AI costs (80% reduction) |
| **Human-in-the-Loop** | Officers retain full control with override capabilities |
| **Enterprise Grade** | PostgreSQL + Azure + Docker = scalable and secure |
| **Fast Setup** | Get running in under 5 minutes |
| **Extensible** | Add validation rules in minutes with Python |

---

## ✨ Key Features

### 🎯 Core Capabilities

- **📄 PDF Processing**: Extract text, tables, and metadata from complex planning documents
- **🤖 AI Validation**: 30+ automated validation rules with GPT-4 fallback for complex cases
- **📊 Evidence Linking**: Every finding includes source document, page number, and bounding box
- **🔄 Version Tracking**: Full V0 → V1 → V2 modification tracking with delta computation
- **👥 Officer Interface**: Modern web UI for review, override, and decision-making
- **🔌 REST API**: Complete API for integration with existing planning systems

### 🏗️ Technical Stack

```
Frontend:    Streamlit (Web UI) + REST API
Backend:     FastAPI + Python 3.11+
Database:    PostgreSQL 13+ with PostGIS
AI Services: Azure OpenAI (GPT-4) + Azure Document Intelligence
Storage:     Azure Blob Storage
Deployment:  Docker + Azure App Service
```

### 📈 Validation Pipeline

```
1. Ingest      → Upload PDF to Azure Blob Storage
2. Extract     → Azure Document Intelligence OCR
3. Map Fields  → Deterministic extractors (80% of fields)
4. Validate    → 30+ business rules with evidence linking
5. LLM Gate    → GPT-4 only for complex/missing fields
6. Report      → Interactive UI with override capabilities
```

---

## 🚀 Quick Start

### 🐳 Option 1: Docker (Recommended)

**Fastest way to get started - everything in containers!**

```bash
# Clone repository
git clone https://github.com/sgshaji/PlanProof.git
cd PlanProof

# Make sure .env file exists with Azure credentials

# Start everything
docker-compose up -d

# View logs
docker-compose logs -f
```

**Done!** 🎉 Access the app:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000/docs

📖 **Full Docker Guide**: [DOCKER_SETUP.md](./DOCKER_SETUP.md)

---

### 🔧 Option 2: Manual Setup

Prerequisites

- Python 3.11 or higher
- Node.js 18+
- Azure account (OpenAI + Document Intelligence + Blob Storage)
- Git

### 1. Clone Repository

```bash
git clone https://github.com/sgshaji/PlanProof.git
cd planproof
```

### 2. Backend Setup

**Windows:**
```powershell
# Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -e .

# Start backend
python run_api.py
```

**Linux/Mac:**
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .

# Start backend
python run_api.py
```

### 3. Configure Environment

Make sure your `.env` file contains:

```bash
# Azure PostgreSQL (already configured)
DATABASE_URL=postgresql://...

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-instance.openai.azure.com
AZURE_OPENAI_API_KEY=your-key-here
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o-mini

# Azure Document Intelligence
AZURE_DOCINTEL_ENDPOINT=https://your-instance.cognitiveservices.azure.com
AZURE_DOCINTEL_KEY=your-key-here

# Azure Storage
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;...
```

### 4. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs on: http://localhost:3000

### 5. Database Setup (if needed)

```bash
# Run migrations
alembic upgrade head

# Verify connection
python tests/integration/test_db_connection.py
```

### 5. Start Services

**Web UI:**
```bash
python run_ui.py
# Open browser to http://localhost:8501
```

**REST API:**
```bash
python run_api.py
# API available at http://localhost:8000
# Docs at http://localhost:8000/api/docs
```

### 6. Troubleshooting

**CORS Errors** (frontend can't connect to backend):
```powershell
# Run the diagnostic tool
.\fix-cors.ps1

# Or see the complete guide
# CORS_FIX_GUIDE.md
```

Common issues:
- Backend not running → `python run_api.py`
- Missing CORS configuration → Add `API_CORS_ORIGINS` to `.env`
- Wrong port → Verify frontend uses `http://localhost:8000`

See [CORS_FIX_GUIDE.md](CORS_FIX_GUIDE.md) for detailed troubleshooting.

---

## 🏗️ Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                        Web UI / REST API                     │
│              (Streamlit + FastAPI)                           │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                    Orchestration Layer                       │
│   • run_orchestrator.py - Document processing workflow      │
│   • modification_workflow.py - V0 → V1 delta computation    │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                    Pipeline Services                         │
│   • ingest.py    - PDF upload & storage                     │
│   • extract.py   - OCR & text extraction                    │
│   • validate.py  - Rule-based validation                    │
│   • llm_gate.py  - Selective AI processing                  │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                   External Services                          │
│   • Azure Blob Storage - Document storage                   │
│   • Azure Document Intelligence - OCR                       │
│   • Azure OpenAI (GPT-4) - AI validation                    │
│   • PostgreSQL + PostGIS - Data persistence                 │
└─────────────────────────────────────────────────────────────┘
```

### Database Schema

Key tables:
- `applications` - Planning applications (case level)
- `submissions` - Submission versions (V0, V1, V2)
- `documents` - Uploaded PDFs with metadata
- `validation_checks` - Individual validation results
- `change_sets` - Modification deltas between versions
- `runs` - Processing job tracking

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed schema.

---

## 🔌 API Integration

### REST API Endpoints

```bash
# Upload document for processing
POST /api/v1/applications/{ref}/documents
→ Returns: run_id

# Check processing status
GET /api/v1/runs/{run_id}/status
→ Returns: status (pending|completed|failed)

# Get validation results
GET /api/v1/applications/{ref}/results
→ Returns: findings, summary, evidence

# List applications
GET /api/v1/applications
```

### Example: Process Document

```python
import requests

# Upload document
response = requests.post(
    "http://localhost:8000/api/v1/applications/APP-2024-001/documents",
    files={"file": open("planning_app.pdf", "rb")},
    data={"document_type": "application_form"}
)

run_id = response.json()["run_id"]

# Get results
results = requests.get(
    f"http://localhost:8000/api/v1/applications/APP-2024-001/results"
).json()

print(f"Validation: {results['summary']}")
# {'pass': 25, 'fail': 3, 'warning': 2}
```

📖 **Complete API Guide**: [docs/API_INTEGRATION_GUIDE.md](docs/API_INTEGRATION_GUIDE.md)

---

## 💻 Development

### Project Structure

```
planproof/
├── planproof/              # Main application code
│   ├── api/               # REST API routes
│   ├── pipeline/          # Document processing pipeline
│   ├── ui/                # Streamlit web interface
│   ├── services/          # Business services layer
│   ├── db.py              # Database models & ORM
│   ├── storage.py         # Azure Blob Storage client
│   ├── docintel.py        # Azure Document Intelligence
│   ├── aoai.py            # Azure OpenAI client
│   ├── secrets_manager.py # Production secrets management (Key Vault)
│   ├── alerting.py        # Multi-channel alerting system
│   ├── health_monitor.py  # System health monitoring
│   └── config.py          # Configuration management
├── tests/                 # Test suite (382 tests)
│   ├── unit/              # Unit tests (fast, isolated)
│   ├── integration/       # Integration tests (require services)
│   ├── golden/            # Snapshot/approval tests
│   ├── fixtures/          # Test data
│   └── conftest.py        # Pytest configuration
├── docs/                  # Documentation
│   ├── reports/           # Generated analysis reports
│   ├── deployment/        # Deployment guides
│   └── *.md               # Technical documentation
├── config/                # Configuration templates
│   ├── .env.example       # Development config
│   └── production.env.example  # Production config template
├── scripts/               # Utility scripts
│   ├── manual-tests/      # Manual test scripts
│   ├── db/                # Database management
│   ├── analysis/          # Analysis scripts
│   └── utilities/         # Development utilities
├── alembic/               # Database migrations
├── artefacts/             # Rule catalogs & configs
├── run_ui.py              # Streamlit entry point
├── run_api.py             # FastAPI entry point
└── pyproject.toml         # Project configuration
```

**Key Directories:**
- **[planproof/](planproof/)** - Core application code (pipeline, API, UI, services)
- **[tests/](tests/)** - 382 automated tests ([README](tests/README.md))
- **[docs/](docs/)** - Comprehensive documentation ([Index](docs/README.md))
- **[config/](config/)** - Environment configs ([Guide](config/README.md))
- **[scripts/](scripts/)** - Development utilities ([README](scripts/README.md))

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=planproof --cov-report=html

# Run specific test
pytest tests/unit/test_validate_rules.py
```

### Adding Validation Rules

1. Edit `artefacts/rule_catalog.json`:

```json
{
  "rule_id": "R-NEW-001",
  "title": "My New Rule",
  "category": "completeness",
  "severity": "error",
  "validator_fn": "validate_my_rule"
}
```

2. Implement in `planproof/pipeline/validate.py`:

```python
def validate_my_rule(extraction: Dict, context: Dict) -> Dict:
    """Validate my new requirement."""
    # Your validation logic
    return {
        "status": "pass|fail|warning",
        "message": "Explanation",
        "evidence": [...]
    }
```

---

## 🚢 Deployment

### Docker Deployment

```bash
# Build image
docker build -t planproof:latest .

# Run with docker-compose
docker-compose up -d
```

### Azure App Service

```bash
# Deploy API
az webapp up --name planproof-api --runtime "PYTHON:3.11"

# Deploy UI
az webapp up --name planproof-ui --runtime "PYTHON:3.11"
```

### Environment Variables

Required in production:
```bash
DATABASE_URL=postgresql://...
AZURE_OPENAI_ENDPOINT=https://...
AZURE_OPENAI_API_KEY=...
AZURE_DOCINTEL_ENDPOINT=https://...
AZURE_DOCINTEL_KEY=...
AZURE_STORAGE_CONNECTION_STRING=...
ENABLE_DB_WRITES=true
ENABLE_LLM_GATE=true
```

📖 **Deployment Guide**: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture & design decisions |
| [API_INTEGRATION_GUIDE.md](docs/API_INTEGRATION_GUIDE.md) | Complete REST API documentation |
| [DEPLOYMENT.md](docs/DEPLOYMENT.md) | Production deployment guide |
| [CONTRIBUTING.md](docs/CONTRIBUTING.md) | Contribution guidelines |
| [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Common issues & solutions |
| [CORS_FIX_GUIDE.md](CORS_FIX_GUIDE.md) | **CORS error troubleshooting** (frontend-backend connection) |
| [NEW_UI_IMPLEMENTATION.md](docs/NEW_UI_IMPLEMENTATION.md) | UI features & modification tracking |
| [DATABASE_CONNECTION_FIX.md](docs/DATABASE_CONNECTION_FIX.md) | Database setup troubleshooting |
| [QUICKSTART.md](QUICKSTART.md) | Rapid setup guide |
| [CHANGELOG.md](CHANGELOG.md) | Version history |

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](docs/CONTRIBUTING.md) for:

- Code style guidelines
- Pull request process
- Testing requirements
- Development workflow

### Quick Contribution Guide

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Make changes and add tests
4. Run tests (`pytest`)
5. Commit (`git commit -m 'Add amazing feature'`)
6. Push (`git push origin feature/amazing-feature`)
7. Open Pull Request

---

## 📊 Project Status

**Current Version**: 1.0.0 (Production Ready)

**Recent Updates**:
- ✅ **Production Hardening** - Azure Key Vault secrets management
- ✅ **Multi-Channel Alerting** - Email, Azure Monitor, Webhooks, Logs
- ✅ **Health Monitoring** - System metrics and component health checks
- ✅ **Test Suite** - 382 automated tests with 85%+ coverage
- ✅ Complete REST API implementation
- ✅ New UI with modification tracking (V0 → V1 → V2)
- ✅ Database connection fixes (psycopg v3)
- ✅ Delta visualization for application changes
- ✅ Comprehensive documentation and repository organization

**Test Coverage**: 85%+ (382 tests)
**Code Quality**: 84.1/100 (B+) - [View Report](docs/reports/CODE_REVIEW_REPORT.md)
**Production Readiness**: Hardened - [View Summary](docs/reports/PRODUCTION_HARDENING_SUMMARY.md)

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Bristol City Council** - Requirements and domain expertise
- **Azure OpenAI** - GPT-4 integration
- **Azure Document Intelligence** - OCR capabilities
- **Streamlit** - Rapid UI development
- **FastAPI** - Modern API framework

---

## 📞 Support

- **Documentation**: [docs/](docs/)
- **Issues**: [GitHub Issues](https://github.com/your-org/planproof/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/planproof/discussions)

---

<div align="center">

**Made with ❤️ for UK Planning Authorities**

[⬆ Back to Top](#planproof---ai-powered-planning-application-validation)

</div>
