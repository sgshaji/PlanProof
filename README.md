# PlanProof

> AI-Powered UK Planning Application Validation System

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![React 18](https://img.shields.io/badge/react-18-blue.svg)](https://reactjs.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

PlanProof is an intelligent validation system for UK planning applications that combines Azure AI services with a comprehensive rules engine to automate initial validation, extract key information, and provide clear actionable findings for planning officers.

## 🚀 Key Features

- **Automated Document Analysis**: Extracts planning application data using Azure Document Intelligence
- **30+ Validation Rules**: Comprehensive validation across 11 categories (Field Requirements, Document Requirements, Consistency, Fees, Ownership, Prior Approval, Constraints, BNG, Plan Quality, Modifications, Spatial)
- **Natural Language Findings**: User-friendly validation results categorized by topic, not technical severity
- **Document Intelligence**: Identifies missing documents and suggests alternatives from submission packages
- **Officer-Friendly UX**: Modern React interface designed specifically for planning officers
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

- **[Quick Start Guide](docs/QUICKSTART.md)** - Get up and running in 10 minutes
- **[Local Setup Guide](docs/setup-local.md)** - Detailed local development setup
- **[Architecture Guide](docs/ARCHITECTURE.md)** - System design and components
- **[API Integration Guide](docs/API_INTEGRATION_GUIDE.md)** - Backend API reference
- **[Deployment Guide](docs/DEPLOYMENT.md)** - Production deployment instructions
- **[Testing Guide](docs/TESTING_GUIDE.md)** - Running and writing tests
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues and solutions

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

### Azure Deployment

1. **Provision Azure resources**
   ```bash
   ./infrastructure/scripts/provision-storage.ps1
   ```

2. **Configure environment**
   ```bash
   cp config/production.env.example config/production.env
   # Edit with production credentials
   ```

3. **Deploy with Docker**
   ```bash
   docker-compose -f infrastructure/docker/docker-compose.yml up -d
   ```

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed instructions.

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
