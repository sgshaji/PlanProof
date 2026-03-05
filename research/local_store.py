"""JSON-based local storage for research pipeline results.

Provides persistence for SN-KG graphs, experiment results, and
pipeline state without requiring a PostgreSQL database.
All data is stored as JSON/pickle files in the output directory.
"""

import json
import logging
import os
import pickle
from dataclasses import asdict
from pathlib import Path
from typing import Any, Optional

import networkx as nx
from networkx.readwrite import json_graph

from research.config import ResearchConfig

logger = logging.getLogger(__name__)


class LocalStore:
    """File-based storage for research pipeline outputs.

    Directory structure:
        output/
            graphs/
                snkg_{app_id}.json       # SN-KG per application (JSON)
                snkg_{app_id}.gpickle    # SN-KG per application (pickle, fast)
            results/
                leiden_{app_id}.json     # Community detection results
                conflicts_{app_id}.json  # Conflict detection results
                experiment_results.json  # All experiment outputs
            extracted/
                {app_id}/
                    text/                # Extracted text from PDFs
                    vision/              # GPT-4o vision descriptions
    """

    def __init__(self, config: Optional[ResearchConfig] = None):
        self.config = config or ResearchConfig()
        self.base_dir = Path(self.config.output_dir)
        self.graphs_dir = self.base_dir / "graphs"
        self.results_dir = self.base_dir / "results"
        self.extracted_dir = self.base_dir / "extracted"

        # Ensure directories exist
        for d in [self.graphs_dir, self.results_dir, self.extracted_dir]:
            d.mkdir(parents=True, exist_ok=True)

    # --- Graph persistence ---

    def save_graph(self, G: nx.DiGraph, app_id: str) -> Path:
        """Save a NetworkX graph as both JSON and pickle."""
        # JSON (human-readable, portable)
        json_path = self.graphs_dir / f"snkg_{app_id}.json"
        data = json_graph.node_link_data(G)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

        # Pickle (fast loading, preserves all Python types)
        pickle_path = self.graphs_dir / f"snkg_{app_id}.gpickle"
        with open(pickle_path, "wb") as f:
            pickle.dump(G, f, protocol=pickle.HIGHEST_PROTOCOL)

        logger.info("Saved graph for %s (%d nodes, %d edges) to %s",
                     app_id, G.number_of_nodes(), G.number_of_edges(), json_path)
        return json_path

    def load_graph(self, app_id: str) -> Optional[nx.DiGraph]:
        """Load a graph, preferring pickle for speed."""
        pickle_path = self.graphs_dir / f"snkg_{app_id}.gpickle"
        if pickle_path.exists():
            with open(pickle_path, "rb") as f:
                G = pickle.load(f)
            logger.info("Loaded graph for %s from pickle (%d nodes)",
                        app_id, G.number_of_nodes())
            return G

        json_path = self.graphs_dir / f"snkg_{app_id}.json"
        if json_path.exists():
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            G = json_graph.node_link_graph(data, directed=True)
            logger.info("Loaded graph for %s from JSON (%d nodes)",
                        app_id, G.number_of_nodes())
            return G

        logger.warning("No saved graph found for %s", app_id)
        return None

    def list_saved_graphs(self) -> list[str]:
        """List all saved graph application IDs."""
        return sorted(set(
            p.stem.replace("snkg_", "")
            for p in self.graphs_dir.glob("snkg_*.json")
        ))

    def graph_exists(self, app_id: str) -> bool:
        """Check if a graph has been saved for an application."""
        return (self.graphs_dir / f"snkg_{app_id}.json").exists()

    # --- Result persistence ---

    def save_results(self, results: dict, name: str) -> Path:
        """Save experiment/pipeline results as JSON."""
        path = self.results_dir / f"{name}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, default=str)
        logger.info("Saved results to %s", path)
        return path

    def load_results(self, name: str) -> Optional[dict]:
        """Load saved results."""
        path = self.results_dir / f"{name}.json"
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_leiden_results(self, app_id: str, leiden_data: dict) -> Path:
        """Save Leiden community detection results."""
        return self.save_results(leiden_data, f"leiden_{app_id}")

    def save_conflict_results(self, app_id: str, conflict_data: dict) -> Path:
        """Save conflict detection results."""
        return self.save_results(conflict_data, f"conflicts_{app_id}")

    # --- Extracted text persistence ---

    def get_extracted_dir(self, app_id: str) -> Path:
        """Get the extracted text directory for an application."""
        d = self.extracted_dir / app_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def save_extracted_text(self, app_id: str, filename: str, text: str) -> Path:
        """Save extracted text for a document."""
        text_dir = self.get_extracted_dir(app_id) / "text"
        text_dir.mkdir(parents=True, exist_ok=True)
        path = text_dir / f"{filename}.txt"
        path.write_text(text, encoding="utf-8")
        return path

    def save_vision_description(self, app_id: str, filename: str,
                                 description: str, metadata: dict = None) -> Path:
        """Save GPT-4o vision description for a document page."""
        vision_dir = self.get_extracted_dir(app_id) / "vision"
        vision_dir.mkdir(parents=True, exist_ok=True)
        path = vision_dir / f"{filename}.txt"
        path.write_text(description, encoding="utf-8")
        if metadata:
            meta_path = vision_dir / f"{filename}.meta.json"
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2)
        return path

    def list_extracted_apps(self) -> list[str]:
        """List application IDs that have extracted text."""
        return sorted(
            d.name for d in self.extracted_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        )

    # --- Pipeline state ---

    def save_pipeline_state(self, state: dict) -> Path:
        """Save pipeline execution state for resumability."""
        return self.save_results(state, "pipeline_state")

    def load_pipeline_state(self) -> Optional[dict]:
        """Load pipeline execution state."""
        return self.load_results("pipeline_state")

    # --- Summary ---

    def summary(self) -> dict:
        """Return a summary of stored data."""
        return {
            "graphs": self.list_saved_graphs(),
            "extracted_apps": self.list_extracted_apps(),
            "result_files": sorted(p.name for p in self.results_dir.glob("*.json")),
            "output_dir": str(self.base_dir),
        }
