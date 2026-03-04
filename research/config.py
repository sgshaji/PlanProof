"""Research module configuration.

Provides settings for graph construction, community detection,
conflict detection thresholds, and database connectivity.
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ResearchConfig:
    """Configuration for the research pipeline."""

    # Database — read-only access to Stage 3 outputs
    database_url: str = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://planproof:planproof@localhost:5432/planproof",
    )

    # Leiden community detection
    leiden_resolution: float = 1.0
    leiden_n_iterations: int = -1  # -1 = iterate until stable
    leiden_seed: Optional[int] = 42

    # Conflict detection thresholds
    area_tolerance_pct: float = 0.10  # 10% tolerance for area conflicts
    height_tolerance_m: float = 0.15  # 15cm tolerance for height conflicts
    distance_tolerance_m: float = 0.10  # 10cm tolerance for distance conflicts
    address_similarity_threshold: float = 0.85  # fuzzy match threshold

    # Perturbation experiments
    random_seed: int = 42
    perturbation_rates: list[float] = field(
        default_factory=lambda: [0.0, 0.05, 0.10, 0.20, 0.30, 0.50]
    )

    # Output paths
    output_dir: str = os.path.join(os.path.dirname(__file__), "output")
    ground_truth_dir: str = os.path.join(os.path.dirname(__file__), "ground_truth")

    # Azure OpenAI (for synthetic data generation and GraphRAG)
    azure_openai_endpoint: str = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
    azure_openai_api_key: str = os.environ.get("AZURE_OPENAI_API_KEY", "")
    azure_openai_api_version: str = os.environ.get(
        "AZURE_OPENAI_API_VERSION", "2024-02-15-preview"
    )
    azure_openai_chat_deployment: str = os.environ.get(
        "AZURE_OPENAI_CHAT_DEPLOYMENT", ""
    )
    azure_openai_embedding_deployment: str = os.environ.get(
        "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", ""
    )

    # GraphRAG workspace
    graphrag_workspace_path: str = os.path.join(
        os.path.dirname(__file__), "graphrag_workspace"
    )

    # BCC sample data
    bcc_data_path: str = os.path.join(
        os.path.dirname(__file__), os.pardir,
        "data", "BCC Sample applications", "BCC Sample applications",
    )

    def __post_init__(self):
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.ground_truth_dir, exist_ok=True)
