# PlanProof

> AI-Powered UK Planning Application Validation System

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![React 18](https://img.shields.io/badge/react-18-blue.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![Azure](https://img.shields.io/badge/Azure-Cloud-blue.svg)](https://azure.microsoft.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

PlanProof is an intelligent validation system for UK planning applications that combines Azure AI services with a comprehensive rules engine to automate initial validation, extract key information, and provide clear actionable findings for planning officers.

## 🌐 Live Demo

**Production Environment (Azure Container Apps)**
- **Application**: [https://planproof-frontend.jollydune-ff843d95.uksouth.azurecontainerapps.io/](https://planproof-frontend.jollydune-ff843d95.uksouth.azurecontainerapps.io/)
- **API**: [https://planproof-backend.jollydune-ff843d95.uksouth.azurecontainerapps.io/](https://planproof-backend.jollydune-ff843d95.uksouth.azurecontainerapps.io/)
- **API Documentation**: [https://planproof-backend.jollydune-ff843d95.uksouth.azurecontainerapps.io/api/docs](https://planproof-backend.jollydune-ff843d95.uksouth.azurecontainerapps.io/api/docs)

## 🚀 Key Features

- **Automated Document Analysis**: Extracts planning application data using Azure Document Intelligence
- **30+ Validation Rules**: Comprehensive validation across 11 categories (Field Requirements, Document Requirements, Consistency, Fees, Ownership, Prior Approval, Constraints, BNG, Plan Quality, Modifications, Spatial)
- **Natural Language Findings**: User-friendly validation results categorized by topic, not technical severity
- **Document Intelligence**: Identifies missing documents and suggests alternatives from submission packages
- **Officer-Friendly UX(for testing only)**: Modern React interface designed specifically for planning officers
- **Evidence-Based Validation**: All findings link to specific documents and page numbers
- **Delta Tracking**: Monitors changes across application versions
- **Parent Discovery**: Automatic identification of related planning applications

## 📋 Table of Contents

- [Technology Stack](#technology-stack)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Documentation](#documentation)
- [Development](#development)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)

## 🛠️ Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL 13+ with Alembic migrations
- **AI Services**: 
  - Azure OpenAI (GPT-4)
  - Azure Document Intelligence
- **Storage**: Azure Blob Storage
- **Validation**: Custom rules engine with 30+ validators

### Frontend
- **Framework**: React 18 with TypeScript
- **UI Library**: Material-UI (MUI)
- **Build Tool**: Vite
- **State Management**: React Hooks + Context API

### Infrastructure
- **Containerization**: Docker & Docker Compose
- **Deployment**: Azure-ready configuration
- **CI/CD**: GitHub Actions (coming soon)

## ⚡ Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 13+
- Azure OpenAI access
- Azure Document Intelligence resource

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/planproof.git
   cd planproof
   ```

2. **Set up backend**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   
   # Configure environment variables
   cp ../config/production.env.example .env
   # Edit .env with your Azure credentials
   
   # Initialize database
   alembic upgrade head
   ```

3. **Set up frontend**
   ```bash
   cd frontend
   npm install
   ```

4. **Start development servers**
   ```bash
   # Terminal 1 - Backend
   cd backend
   python run_api.py
   
   # Terminal 2 - Frontend
   cd frontend
   npm run dev
   ```

5. **Access the application**
   - Frontend: http://localhost:5173
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

### Docker Deployment

```bash
docker-compose -f infrastructure/docker/docker-compose.yml up
```

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for production deployment instructions.

## 📁 Project Structure

```
planproof/
├── backend/                    # Python FastAPI backend
│   ├── planproof/             # Core application package
│   │   ├── api/               # FastAPI routes
│   │   ├── pipeline/          # Validation pipeline
│   │   ├── services/          # Business logic services
│   │   └── ...
│   ├── alembic/               # Database migrations
│   ├── tests/                 # Backend tests
│   └── scripts/               # Utility scripts
│
├── frontend/                   # React TypeScript frontend
│   ├── src/
│   │   ├── components/        # Reusable UI components
│   │   ├── pages/             # Page components
│   │   ├── contexts/          # React contexts
│   │   └── services/          # API clients
│   └── ...
│
├── infrastructure/            # Deployment & DevOps
│   ├── docker/                # Dockerfiles & compose files
│   └── scripts/               # Deployment scripts
│
├── docs/                      # Documentation
│   ├── features/              # Feature documentation
│   ├── deployment/            # Deployment guides
│   └── troubleshooting/       # Common issues & fixes
│
├── artifacts/                 # Static assets & data
│   ├── rule_catalog.json      # Validation rules catalog
│   └── sample_data/           # Sample applications
│
└── archive/                   # Historical documentation
```

## 📚 Documentation

### Getting Started
- **[Quick Start Guide](docs/QUICKSTART.md)** - Get up and running in 10 minutes
- **[Local Setup Guide](docs/setup-local.md)** - Detailed local development setup
- **[Quick Reference](docs/QUICK_REFERENCE.md)** - Common commands and workflows

### System Documentation
- **[Architecture Guide](docs/ARCHITECTURE.md)** - System design and components
- **[API Integration Guide](docs/API_INTEGRATION_GUIDE.md)** - Backend API reference
- **[Database Schema Management](docs/DATABASE_SCHEMA_MANAGEMENT.md)** - Alembic migrations and schema
- **[Query Guide](docs/QUERY_GUIDE.md)** - Database queries and optimization

### Deployment & Operations
- **[Deployment Guide](docs/DEPLOYMENT.md)** - General deployment instructions
- **[Azure Container Apps Guide](docs/AZURE_CONTAINER_APPS.md)** - Production Azure deployment
- **[Docker Setup](docs/deployment/docker-setup.md)** - Docker containerization
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues and solutions

### Development
- **[Testing Guide](docs/TESTING_GUIDE.md)** - Running and writing tests
- **[Test Coverage Analysis](docs/TEST_COVERAGE_ANALYSIS.md)** - Coverage reports
- **[Contributing Guide](docs/CONTRIBUTING.md)** - How to contribute
- **[Migration Guide](docs/MIGRATION_GUIDE.md)** - Upgrading between versions
- **[Accessibility](docs/accessibility.md)** - WCAG compliance

### Feature Documentation
- [Address Proposal Fields](docs/features/ADDRESS_PROPOSAL_IMPLEMENTATION.md)
- [Evidence Candidate Docs](docs/features/EVIDENCE_CANDIDATE_DOCS_README.md)
- [Parent Discovery](docs/features/PARENT_DISCOVERY_IMPLEMENTATION.md)
- [Extracted Fields Display](docs/features/EXTRACTED_FIELDS_UI_DISPLAY.md)

## 🔧 Development

### Backend Development

```bash
cd backend

# Run tests
pytest

# Run with hot reload
python run_api.py

# Database migrations
alembic revision --autogenerate -m "Description"
alembic upgrade head

# Code formatting
black planproof/
isort planproof/
```

### Frontend Development

```bash
cd frontend

# Run tests
npm test

# Type checking
npm run type-check

# Linting
npm run lint

# Build for production
npm run build
```

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test

# E2E tests
npm run test:e2e
```

## 🚀 Deployment

### Production (Azure Container Apps)

The application is deployed on Azure Container Apps with auto-scaling capabilities:

- **Location**: UK South (uksouth)
- **Backend**: 1-3 replicas, 1 vCPU, 2GB RAM
- **Frontend**: 1-2 replicas, 0.5 vCPU, 1GB RAM
- **Database**: Azure PostgreSQL Flexible Server
- **Storage**: Azure Blob Storage
- **AI Services**: Azure OpenAI (GPT-4) + Document Intelligence

**Deployment Scripts:**
```bash
# PowerShell (Windows)
.\infrastructure\azure\deploy-azure-aca.ps1

# Bash (Linux/macOS)
./infrastructure/azure/deploy-azure-aca.sh
```

**Manage Deployment:**
```powershell
# View status
az containerapp show --name planproof-backend --resource-group planproof-rg
� Security & Privacy

This is a **private repository**. The application handles sensitive planning data and Azure credentials:

- All Azure credentials stored in `.env` (never committed to git)
- Azure PostgreSQL with SSL/TLS encryption
- Azure Blob Storage with private access
- JWT-based authentication for API access
- CORS configured for specific origins only

## 💰 Cost Estimation

**Azure Monthly Costs (UK South region):**
- Container Apps (Backend): ~£10-15/month
- Container Apps (Frontend): ~£5-10/month
- PostgreSQL Flexible Server: ~£30-40/month
- Blob Storage: ~£1-2/month
- Azure OpenAI: Pay-per-use (variable)
- Document Intelligence: Pay-per-use (variable)

**Total: ~£50-70/month + AI usage**

**Cost Savings:**
```powershell
# Scale to 0 when not in use
az containerapp update --name planproof-backend --resource-group planproof-rg --min-replicas 0
az containerapp update --name planproof-frontend --resource-group planproof-rg --min-replicas 0
```

## 📞 Support

For questions or issues:
- Check [Troubleshooting Guide](docs/TROUBLESHOOTING.md)
- Review [Changelog](docs/CHANGELOG.md) for recent updates
- Contact the development team

---

**Built with ❤️ for UK planning officers | Powered by Azure AI**
az containerapp update --name planproof-backend --resource-group planproof-rg --min-replicas 1
```

### Local Development with Docker

```bash
docker-compose -f infrastructure/docker/docker-compose.yml up -d
```

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) and [docs/AZURE_CONTAINER_APPS.md](docs/AZURE_CONTAINER_APPS.md) for detailed instructions.

## 🤝 Contributing

We welcome contributions! Please see [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- UK Planning Portal for validation requirements
- Azure AI team for Document Intelligence and OpenAI services
- Open-source community for excellent tools and libraries

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/planproof/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/planproof/discussions)

---

Made with ❤️ for planning officers
