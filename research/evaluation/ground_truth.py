"""Ground truth annotation data structures and I/O.

Defines the GroundTruthAnnotation schema for manually annotated
submissions, with JSON serialization for storage in research/ground_truth/.
"""

import json
import os
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional, Union

logger = logging.getLogger(__name__)


@dataclass
class GroundTruthEntity:
    """A ground truth spatial entity."""

    entity_id: str
    entity_type: str  # "Room", "Building", "Boundary", "Opening"
    label: str
    properties: dict = field(default_factory=dict)
    # For matching: name + area tolerance (Room), address (Building)
    match_key: str = ""


@dataclass
class GroundTruthRelationship:
    """A ground truth relationship between entities."""

    source_id: str
    target_id: str
    relationship_type: str  # "CONTAINS", "ADJACENT_TO", "OPENS_INTO"
    properties: dict = field(default_factory=dict)


@dataclass
class GroundTruthConflict:
    """A ground truth conflict annotation."""

    conflict_id: str
    conflict_type: str  # "area", "height", "distance", "address"
    entity_a_id: str
    entity_b_id: str
    field_name: str
    value_a: str
    value_b: str
    severity: str  # "high", "medium", "low"
    description: str = ""


@dataclass
class GroundTruthAnnotation:
    """Complete ground truth annotation for a submission."""

    submission_id: Union[int, str]
    annotator: str
    annotation_date: str
    is_synthetic: bool = False
    source: str = "manual"  # "manual", "ifc", "synthetic"

    entities: list[GroundTruthEntity] = field(default_factory=list)
    relationships: list[GroundTruthRelationship] = field(default_factory=list)
    conflicts: list[GroundTruthConflict] = field(default_factory=list)

    # Expected compliance verdicts per rule
    expected_verdicts: dict[str, str] = field(default_factory=dict)

    notes: str = ""

    def save(self, output_dir: str):
        """Save annotation to a JSON file."""
        os.makedirs(output_dir, exist_ok=True)
        filename = f"gt_submission_{self.submission_id}.json"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2, ensure_ascii=False)

        logger.info("Saved ground truth to %s", filepath)
        return filepath

    @classmethod
    def load(cls, filepath: str) -> "GroundTruthAnnotation":
        """Load annotation from a JSON file."""
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        entities = [GroundTruthEntity(**e) for e in data.pop("entities", [])]
        relationships = [
            GroundTruthRelationship(**r) for r in data.pop("relationships", [])
        ]
        conflicts = [GroundTruthConflict(**c) for c in data.pop("conflicts", [])]

        return cls(
            entities=entities,
            relationships=relationships,
            conflicts=conflicts,
            **data,
        )

    @classmethod
    def load_all(cls, ground_truth_dir: str) -> list["GroundTruthAnnotation"]:
        """Load all annotations from a directory."""
        annotations = []
        if not os.path.isdir(ground_truth_dir):
            logger.warning("Ground truth directory not found: %s", ground_truth_dir)
            return annotations

        for filename in sorted(os.listdir(ground_truth_dir)):
            if filename.startswith("gt_") and filename.endswith(".json"):
                filepath = os.path.join(ground_truth_dir, filename)
                try:
                    annotations.append(cls.load(filepath))
                except Exception as e:
                    logger.error("Failed to load %s: %s", filepath, e)

        logger.info("Loaded %d ground truth annotations", len(annotations))
        return annotations
