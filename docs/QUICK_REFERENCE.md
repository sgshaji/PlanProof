# PlanProof Quick Reference

**Fast navigation guide for the reorganized repository**

## 🚀 I Want To...

### Get Started
- **Set up development environment** → [QUICKSTART.md](QUICKSTART.md)
- **Understand the system** → [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **Configure environment** → [config/README.md](config/README.md)

### Work on Code
- **Find main application code** → [planproof/](planproof/)
- **Run tests** → [tests/README.md](tests/README.md) - `pytest`
- **Use scripts** → [scripts/README.md](scripts/README.md)
- **Check test coverage** → `pytest --cov=planproof --cov-report=html`

### Integration & APIs
- **Use REST API** → [docs/API_INTEGRATION_GUIDE.md](docs/API_INTEGRATION_GUIDE.md)
- **Query database** → [docs/QUERY_GUIDE.md](docs/QUERY_GUIDE.md)
- **Run API server** → `python run_api.py`
- **Start web UI** → `python run_ui.py`

### Deploy & Operations
- **Deploy to production** → [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- **Configure production** → [config/production.env.example](config/production.env.example)
- **Troubleshoot issues** → [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
- **Monitor health** → [docs/reports/PRODUCTION_HARDENING_SUMMARY.md](docs/reports/PRODUCTION_HARDENING_SUMMARY.md)

### Find Information
- **Browse all docs** → [docs/README.md](docs/README.md)
- **View code quality** → [docs/reports/CODE_REVIEW_REPORT.md](docs/reports/CODE_REVIEW_REPORT.md)
- **See what changed** → [CHANGELOG.md](CHANGELOG.md)
- **Reorganization details** → [REPOSITORY_REORGANIZATION.md](REPOSITORY_REORGANIZATION.md)

## 📁 Directory Quick Reference

| Directory | Purpose | Key Files |
|-----------|---------|-----------|
| **[planproof/](planproof/)** | Main application code | `db.py`, `storage.py`, `aoai.py`, `secrets_manager.py` |
| **[planproof/api/](planproof/api/)** | REST API endpoints | Route handlers for `/api/v1/*` |
| **[planproof/pipeline/](planproof/pipeline/)** | Document processing | `ingest.py`, `extract.py`, `validate.py` |
| **[planproof/ui/](planproof/ui/)** | Streamlit web UI | Dashboard, results, upload pages |
| **[tests/](tests/)** | Test suite (382 tests) | `conftest.py`, unit/, integration/, golden/ |
| **[config/](config/)** | Environment configs | `.env.example`, `production.env.example` |
| **[docs/](docs/)** | Documentation | Architecture, API, deployment guides |
| **[docs/reports/](docs/reports/)** | Generated reports | Code review, production hardening |
| **[scripts/](scripts/)** | Utility scripts | DB tools, manual tests, analysis |
| **[alembic/](alembic/)** | Database migrations | Schema version control |
| **[artefacts/](artefacts/)** | Rule catalogs | Validation rule definitions |

## 🔧 Common Commands

### Development
```bash
# Setup
.\setup-dev.ps1          # Windows
./setup-dev.sh           # Linux/Mac

# Run services
python run_ui.py         # Streamlit UI (port 8501)
python run_api.py        # REST API (port 8000)

# Testing
pytest                   # Run all tests
pytest -m unit           # Unit tests only
pytest --cov=planproof   # With coverage

# Database
alembic upgrade head     # Run migrations
python scripts/db/create_tables.py  # Create tables
```

### Configuration
```bash
# Development
cp config/.env.example .env
# Edit .env with your settings

# Production
cp config/production.env.example .env.production
# Replace all CHANGE_ME values
```

### Scripts
```bash
# Manual tests (require running services)
python scripts/manual-tests/test_api.py
python scripts/manual-tests/test_db_connection.py

# Utilities
python scripts/smoke_test.py
python scripts/build_rule_catalog.py
```

## 📚 Documentation by Role

### 👨‍💻 Developer
1. [README.md](README.md) - Project overview
2. [docs/setup_guide.md](docs/setup_guide.md) - Setup instructions
3. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - System design
4. [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) - Contribution guidelines
5. [tests/README.md](tests/README.md) - Testing guide

### 🚀 DevOps / SRE
1. [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) - Production deployment
2. [config/production.env.example](config/production.env.example) - Production config
3. [docs/reports/PRODUCTION_HARDENING_SUMMARY.md](docs/reports/PRODUCTION_HARDENING_SUMMARY.md) - Production setup
4. [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) - Issue resolution
5. [docs/DATABASE_CONNECTION_FIX.md](docs/DATABASE_CONNECTION_FIX.md) - DB troubleshooting

### 🔌 API Consumer / Integrator
1. [docs/API_INTEGRATION_GUIDE.md](docs/API_INTEGRATION_GUIDE.md) - Complete API reference
2. [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - System overview
3. [QUICKSTART.md](QUICKSTART.md) - Quick start guide

### 🗄️ Database Administrator
1. [docs/QUERY_GUIDE.md](docs/QUERY_GUIDE.md) - Query patterns
2. [docs/DATABASE_CONNECTION_FIX.md](docs/DATABASE_CONNECTION_FIX.md) - Connection troubleshooting
3. [scripts/db/](scripts/db/) - Database management scripts
4. [alembic/versions/](alembic/versions/) - Migration history

## 🆘 Troubleshooting Quick Links

| Problem | Solution |
|---------|----------|
| Can't connect to database | [docs/DATABASE_CONNECTION_FIX.md](docs/DATABASE_CONNECTION_FIX.md) |
| API returns errors | [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) |
| Tests failing | [tests/README.md](tests/README.md#troubleshooting) |
| Configuration issues | [config/README.md](config/README.md#troubleshooting) |
| Performance problems | [docs/PERFORMANCE_TROUBLESHOOTING.md](docs/PERFORMANCE_TROUBLESHOOTING.md) |
| Deployment issues | [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) |

## 📊 Project Status

- **Version:** 1.0.0 (Production Ready)
- **Tests:** 382 tests, 85%+ coverage
- **Code Quality:** 84.1/100 (B+)
- **Production:** Hardened with secrets management, alerting, monitoring

## 🔗 External Resources

- **Azure OpenAI:** https://azure.microsoft.com/en-us/products/ai-services/openai-service
- **Azure Document Intelligence:** https://azure.microsoft.com/en-us/products/ai-services/ai-document-intelligence
- **FastAPI Docs:** https://fastapi.tiangolo.com/
- **Streamlit Docs:** https://docs.streamlit.io/
- **Pytest Docs:** https://docs.pytest.org/

## 🎯 Next Steps

**New to the project?**
1. Read [README.md](README.md)
2. Follow [QUICKSTART.md](QUICKSTART.md)
3. Review [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
4. Check [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md)

**Ready to contribute?**
1. Set up environment: `.\setup-dev.ps1`
2. Run tests: `pytest`
3. Read [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md)
4. Pick an issue and start coding!

**Deploying to production?**
1. Read [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
2. Configure [config/production.env.example](config/production.env.example)
3. Review [docs/reports/PRODUCTION_HARDENING_SUMMARY.md](docs/reports/PRODUCTION_HARDENING_SUMMARY.md)
4. Follow deployment checklist

---

**Need help?** Check [docs/README.md](docs/README.md) for comprehensive documentation index.
