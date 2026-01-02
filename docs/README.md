# Documentation Index

This directory contains comprehensive documentation for the PlanProof system.

## Quick Navigation

### 📋 Getting Started
- **[../README.md](../README.md)** - Project overview and quick start
- **[../QUICKSTART.md](../QUICKSTART.md)** - 5-minute setup guide
- **[setup_guide.md](setup_guide.md)** - Detailed setup instructions

### 🏗️ Architecture & Design
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture overview
- **[API_INTEGRATION_GUIDE.md](API_INTEGRATION_GUIDE.md)** - REST API documentation
- **[QUERY_GUIDE.md](QUERY_GUIDE.md)** - Database query patterns
- **[NEW_UI_IMPLEMENTATION.md](NEW_UI_IMPLEMENTATION.md)** - UI architecture
- **[ENHANCED_ISSUE_MODEL.md](ENHANCED_ISSUE_MODEL.md)** - Validation issue format

### 🚀 Deployment
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Production deployment guide
- **[deployment/](deployment/)** - Deployment-specific documentation
  - Infrastructure as Code templates
  - Container orchestration configs
  - CI/CD pipeline documentation

### 🛠️ Development
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Contributing guidelines
- **[../CHANGELOG.md](../CHANGELOG.md)** - Version history and changes
- **[PART_2_COMPLETE.md](PART_2_COMPLETE.md)** - UI components implementation
- **[PART_3_COMPLETE.md](PART_3_COMPLETE.md)** - Resolution tracking implementation

### 🔧 Troubleshooting & Maintenance
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common issues and solutions
- **[DATABASE_CONNECTION_FIX.md](DATABASE_CONNECTION_FIX.md)** - Database troubleshooting
- **[ERROR_TROUBLESHOOTING.md](ERROR_TROUBLESHOOTING.md)** - Error tracking and debugging
- **[PERFORMANCE_TROUBLESHOOTING.md](PERFORMANCE_TROUBLESHOOTING.md)** - Performance optimization

### 📊 Reports & Analysis
- **[reports/](reports/)** - Generated reports and analysis
  - Code quality reviews
  - Performance benchmarks
  - Production readiness assessments

## Document Catalog

### Core Documentation

| Document | Purpose | Audience |
|----------|---------|----------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design and components | Developers, Architects |
| [API_INTEGRATION_GUIDE.md](API_INTEGRATION_GUIDE.md) | REST API reference | API consumers, Frontend devs |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Production deployment | DevOps, SREs |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Development workflow | Contributors |
| [setup_guide.md](setup_guide.md) | Installation and configuration | New developers |

### Technical Guides

| Document | Purpose | When to Use |
|----------|---------|-------------|
| [QUERY_GUIDE.md](QUERY_GUIDE.md) | Database query patterns | Writing complex queries |
| [DATABASE_CONNECTION_FIX.md](DATABASE_CONNECTION_FIX.md) | DB troubleshooting | Connection issues |
| [NEW_UI_IMPLEMENTATION.md](NEW_UI_IMPLEMENTATION.md) | UI architecture | Working on frontend |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Common issues | Debugging problems |
| [ENHANCED_ISSUE_MODEL.md](ENHANCED_ISSUE_MODEL.md) | Validation format | Working on validation |

### Generated Reports

Reports in `reports/` are generated from automated analysis:
- **CODE_REVIEW_REPORT.md** - Comprehensive code quality analysis
- **PRODUCTION_HARDENING_SUMMARY.md** - Production readiness assessment

> ⚠️ **Note:** Reports may be regenerated and should not be manually edited.

## Quick Links by Role

### New Developer
1. [../README.md](../README.md) - Project overview
2. [../QUICKSTART.md](../QUICKSTART.md) - Quick setup
3. [setup_guide.md](setup_guide.md) - Detailed setup
4. [CONTRIBUTING.md](CONTRIBUTING.md) - How to contribute
5. [ARCHITECTURE.md](ARCHITECTURE.md) - System design

### DevOps Engineer
1. [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment guide
2. [deployment/](deployment/) - Infrastructure docs
3. [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Issue resolution
4. [reports/PRODUCTION_HARDENING_SUMMARY.md](reports/PRODUCTION_HARDENING_SUMMARY.md) - Production setup

### API Consumer
1. [API_INTEGRATION_GUIDE.md](API_INTEGRATION_GUIDE.md) - API reference
2. [ARCHITECTURE.md](ARCHITECTURE.md) - System overview
3. [../QUICKSTART.md](../QUICKSTART.md) - Quick start

### Database Administrator
1. [QUERY_GUIDE.md](QUERY_GUIDE.md) - Query patterns
2. [DATABASE_CONNECTION_FIX.md](DATABASE_CONNECTION_FIX.md) - Troubleshooting
3. [../scripts/db/](../scripts/db/) - DB management scripts

### Development Documentation

**Enhanced Issue Model** - Detailed specification for the enhanced validation issue format, including data structures, user messaging, evidence tracking, and resolution workflows.

**Part 2 Implementation** - Documentation of completed UI components for enhanced issues, including issue cards, bulk actions, resolution tracking, and action handlers.

**Part 3 Implementation** - Documentation of completed resolution service, auto-recheck functionality, database schema updates, and notification services.

**Contributing Guide** - Code style guidelines, branching strategy, testing requirements, and pull request process.

### Operations Documentation

**Deployment** - Production deployment checklist, Docker configuration, environment variables, database migrations, and Azure resource setup.

**Troubleshooting** - Solutions for common runtime issues, configuration problems, Azure service errors, and database connectivity.

**Error Troubleshooting** - Guide for diagnosing run failures, understanding error messages, using diagnostic tools, and tracking validation issues.

**Performance Guide** - Techniques for optimizing LLM calls, database queries, document processing, and overall system performance.

**Query Guide** - SQL query examples for common reporting needs, analytics, audit trails, and system monitoring.

## 🔄 Documentation Updates

This documentation is actively maintained. If you find errors or have suggestions:

1. Check if the issue is already documented in [Troubleshooting](TROUBLESHOOTING.md)
2. See [Contributing Guide](CONTRIBUTING.md) for how to propose documentation changes
3. Create an issue or pull request with your improvements

---

**Last Updated**: 2026-01-01
