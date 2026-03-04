"""Real vs synthetic document tracking.

Maintains a JSON label file mapping document IDs to their source
(BCC real data vs synthetic generation) for experimental tracking.
"""

import json
import logging
import os
from dataclasses import dataclass, asdict
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class DocumentLabel:
    """Label for a document's provenance."""

    doc_id: str
    source: str  # "bcc_real" or "synthetic"
    variation: Optional[str] = None  # "standard", "incomplete", "conflicting"
    submission_id: Optional[int] = None
    notes: str = ""


class DocumentLabeller:
    """Manages real/synthetic document labels."""

    def __init__(self, label_file: str):
        self.label_file = label_file
        self.labels: dict[str, DocumentLabel] = {}
        self._load()

    def _load(self):
        """Load labels from file."""
        if os.path.exists(self.label_file):
            with open(self.label_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for doc_id, entry in data.items():
                self.labels[doc_id] = DocumentLabel(**entry)
            logger.info("Loaded %d document labels", len(self.labels))

    def save(self):
        """Save labels to file."""
        os.makedirs(os.path.dirname(self.label_file) or ".", exist_ok=True)
        data = {doc_id: asdict(label) for doc_id, label in self.labels.items()}
        with open(self.label_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info("Saved %d document labels to %s", len(self.labels), self.label_file)

    def add_real(self, doc_id: str, submission_id: int, notes: str = ""):
        """Register a real BCC document."""
        self.labels[doc_id] = DocumentLabel(
            doc_id=doc_id,
            source="bcc_real",
            submission_id=submission_id,
            notes=notes,
        )

    def add_synthetic(
        self, doc_id: str, variation: str,
        submission_id: int, notes: str = "",
    ):
        """Register a synthetic document."""
        self.labels[doc_id] = DocumentLabel(
            doc_id=doc_id,
            source="synthetic",
            variation=variation,
            submission_id=submission_id,
            notes=notes,
        )

    def is_synthetic(self, doc_id: str) -> bool:
        """Check if a document is synthetic."""
        label = self.labels.get(doc_id)
        return label is not None and label.source == "synthetic"

    def get_real_ids(self) -> list[str]:
        """Get all real document IDs."""
        return [did for did, l in self.labels.items() if l.source == "bcc_real"]

    def get_synthetic_ids(self) -> list[str]:
        """Get all synthetic document IDs."""
        return [did for did, l in self.labels.items() if l.source == "synthetic"]

    def summary(self) -> dict:
        """Return summary counts."""
        real = sum(1 for l in self.labels.values() if l.source == "bcc_real")
        synthetic = sum(1 for l in self.labels.values() if l.source == "synthetic")
        by_variation: dict[str, int] = {}
        for l in self.labels.values():
            if l.variation:
                by_variation[l.variation] = by_variation.get(l.variation, 0) + 1
        return {
            "total": len(self.labels),
            "real": real,
            "synthetic": synthetic,
            "by_variation": by_variation,
        }
