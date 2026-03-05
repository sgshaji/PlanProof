# PlanProof Research Module

Experimental graph-based analysis pipeline for UK planning applications. Compares SN-KG (Spatial-Normative Knowledge Graph) + Leiden community detection against flat rule-based validation.

## Quick Start

### 1. Prerequisites

- **Python 3.11+ (x64/AMD64)** — required for GraphRAG and its native dependencies
  - On Windows ARM64 machines, install the x64 version from [python.org](https://www.python.org/downloads/) — Windows will run it via emulation
  - Verify architecture: `python -c "import platform; print(platform.machine())"`  → should print `AMD64`
- **Azure OpenAI** resource with:
  - `gpt-4o` deployment (GPT-4o with Vision support, needed for PDF image extraction)
  - `text-embedding-3-small` deployment (for GraphRAG embeddings)

### 2. Environment Setup

```bash
# From the project root (PlanProof/)

# Create virtual environment with x64 Python
python -m venv .venv

# Activate
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r research/requirements.txt
```

### 3. Configuration

Copy `.env.example` to `.env` (or edit the existing `.env`) in the project root and set:

```dotenv
# Azure OpenAI (required)
AZURE_OPENAI_ENDPOINT=https://<region>.api.cognitive.microsoft.com/
AZURE_OPENAI_API_KEY=<your-key>
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4o
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-small

# GraphRAG (same Azure OpenAI resource, different var names)
GRAPHRAG_API_KEY=<same-key>
GRAPHRAG_API_BASE=https://<region>.api.cognitive.microsoft.com/
GRAPHRAG_API_VERSION=2024-02-15-preview
GRAPHRAG_CHAT_DEPLOYMENT=gpt-4o
GRAPHRAG_EMBEDDING_DEPLOYMENT=text-embedding-3-small

# Cost controls
RESEARCH_BUDGET_USD=10.00
```

### 4. Run the Pipeline

The pipeline runs in three stages:

#### Stage 1: Extract text from PDFs

```bash
# Extract text + GPT-4o Vision descriptions from BCC sample PDFs
python -m research.scripts.extract_pdf_text
python -m research.scripts.extract_pdf_vision
```

Extracted text is saved to `research/graphrag_workspace/input/` as `.txt` files.

#### Stage 2: Build Knowledge Graph (GraphRAG)

```bash
# Run GraphRAG indexing to build entity-relationship graph
python -m research.scripts.run_graphrag_index
```

This produces Parquet files in `research/graphrag_workspace/output/` containing entities, relationships, communities, and embeddings.

#### Stage 3: Run Experiments

```bash
# Run all experiments
python -m research.experiments.run_all
```

Results are saved to:
- `research/output/experiment_results.json`
- `research/output/cost_summary.json` (Azure OpenAI spend tracking)
- `research/output/graphs/` (per-application SN-KG graphs)
- `research/output/leiden/` (community detection results)
- `research/output/conflicts/` (conflict detection results)

## Architecture

```
research/
├── config.py              # Central configuration (loads .env)
├── local_store.py          # JSON/pickle storage (no database required)
├── cost_tracker.py         # Azure OpenAI cost tracking + budget enforcement
├── graph/
│   ├── schema.py           # Node/edge type enums (Room, Building, etc.)
│   ├── builder.py          # SN-KG construction from GraphRAG output
│   └── nx_utils.py         # NetworkX graph utilities
├── community/
│   ├── leiden.py           # Leiden algorithm + resolution sweep
│   └── analysis.py         # Community profiling
├── conflict/
│   ├── detector.py         # Cross-document conflict detection
│   └── contradicts.py      # CONTRADICTS edge creation
├── evaluation/
│   ├── metrics.py          # Precision/Recall/F1
│   ├── ground_truth.py     # Ground truth annotations
│   ├── comparison.py       # Flat vs graph comparison
│   ├── perturbation.py     # Robustness testing
│   └── inter_rater.py      # Cohen's kappa
├── experiments/
│   ├── run_all.py          # Master orchestrator
│   ├── exp_community_quality.py
│   ├── exp_conflict_detection.py
│   ├── exp_perturbation.py
│   └── exp_flat_vs_graph.py
├── scripts/
│   ├── extract_pdf_text.py     # PDFPlumber text extraction
│   ├── extract_pdf_vision.py   # GPT-4o Vision extraction
│   └── run_graphrag_index.py   # GraphRAG CLI wrapper
├── graphrag_workspace/
│   ├── settings.yaml       # GraphRAG v3 configuration
│   └── prompts/            # Custom entity extraction prompts
└── tests/                  # Unit tests
```

## Cost Controls

The pipeline tracks all Azure OpenAI API calls and enforces a budget limit:

- Default budget: **$10.00 USD** (set via `RESEARCH_BUDGET_USD` in `.env`)
- Estimated cost for 15 BCC PDFs: **$1–3 USD**
- If the budget is exceeded, the pipeline raises `BudgetExceededError` and stops
- Cost state persists to `research/output/cost_tracker.json` for resumability
- Run `CostTracker.reset()` to start fresh

### Cost Breakdown (estimated)

| Stage | Estimated Cost |
|-------|---------------|
| PDF Vision extraction (15 PDFs, ~30 pages) | $0.50–1.00 |
| GraphRAG indexing (entity extraction + summarization) | $0.50–1.50 |
| GraphRAG embeddings | < $0.01 |
| **Total** | **$1–3** |

## Data

BCC sample applications are in `data/BCC Sample applications/`:
- 5 planning applications, 15 PDFs total
- Application types: planning permission (PA suffix)

## No Database Required

The research pipeline runs entirely locally using JSON/pickle files for storage. No PostgreSQL or other database is needed. Set `use_database=False` in config (this is the default).

## Experiments

1. **Community Quality** — Measures Leiden community modularity and coherence across resolution parameters
2. **Conflict Detection** — Evaluates cross-document contradiction detection (requires ground truth)
3. **Perturbation** — Tests robustness by injecting noise into graph data (requires ground truth)
4. **Flat vs Graph** — Compares graph-based validation against flat rule checks (requires database)
