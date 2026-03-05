#!/usr/bin/env python
"""Generate a sample ground truth annotation for submission ID 1.

Usage:
    cd PlanProof
    python -m research.scripts.create_sample_gt

Outputs gt_submission_1.json to research/ground_truth/.
Adapt this script for real submissions by modifying the entities,
relationships, conflicts, and expected verdicts.
"""

import os
import sys

# Ensure PlanProof root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from research.evaluation.ground_truth import (
    GroundTruthAnnotation,
    GroundTruthEntity,
    GroundTruthRelationship,
    GroundTruthConflict,
)


def create_sample_annotation() -> GroundTruthAnnotation:
    """Build a sample ground truth annotation for submission 1."""
    entities = [
        GroundTruthEntity(
            entity_id="room_kitchen",
            entity_type="Room",
            label="Kitchen",
            properties={"area": 15.0, "floor": "ground"},
            match_key="kitchen",
        ),
        GroundTruthEntity(
            entity_id="room_lounge",
            entity_type="Room",
            label="Lounge",
            properties={"area": 22.5, "floor": "ground"},
            match_key="lounge",
        ),
        GroundTruthEntity(
            entity_id="room_bedroom",
            entity_type="Room",
            label="Bedroom 1",
            properties={"area": 18.0, "floor": "first"},
            match_key="bedroom_1",
        ),
        GroundTruthEntity(
            entity_id="building_main",
            entity_type="Building",
            label="Main Dwelling",
            properties={"ridge_height": 8.5, "address": "12 Oak Lane"},
            match_key="main_dwelling",
        ),
        GroundTruthEntity(
            entity_id="boundary_north",
            entity_type="Boundary",
            label="North Boundary",
            properties={"distance_to_building": 2.0},
            match_key="north_boundary",
        ),
    ]

    relationships = [
        GroundTruthRelationship(
            source_id="Main Dwelling",
            target_id="Kitchen",
            relationship_type="CONTAINS",
        ),
        GroundTruthRelationship(
            source_id="Main Dwelling",
            target_id="Lounge",
            relationship_type="CONTAINS",
        ),
        GroundTruthRelationship(
            source_id="Kitchen",
            target_id="Lounge",
            relationship_type="ADJACENT_TO",
        ),
        GroundTruthRelationship(
            source_id="North Boundary",
            target_id="Main Dwelling",
            relationship_type="OPENS_INTO",
        ),
    ]

    conflicts = [
        GroundTruthConflict(
            conflict_id="gt_conflict_1",
            conflict_type="area",
            entity_a_id="room_kitchen",
            entity_b_id="room_kitchen",
            field_name="floor_area",
            value_a="15.0",
            value_b="18.5",
            severity="high",
            description="Kitchen area differs between form (15 sqm) and drawing (18.5 sqm)",
        ),
        GroundTruthConflict(
            conflict_id="gt_conflict_2",
            conflict_type="height",
            entity_a_id="building_main",
            entity_b_id="building_main",
            field_name="ridge_height",
            value_a="8.5",
            value_b="9.2",
            severity="medium",
            description="Ridge height differs between form (8.5m) and drawing (9.2m)",
        ),
    ]

    return GroundTruthAnnotation(
        submission_id=1,
        annotator="sample",
        annotation_date="2026-03-04",
        is_synthetic=True,
        source="manual",
        entities=entities,
        relationships=relationships,
        conflicts=conflicts,
        expected_verdicts={
            "max_height_8m": "fail",
            "boundary_distance_1m": "pass",
            "floor_area_consistency": "fail",
            "address_consistency": "pass",
        },
        notes="Sample ground truth annotation for testing and demonstration purposes.",
    )


def main():
    gt = create_sample_annotation()
    output_dir = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "ground_truth"
    )
    filepath = gt.save(output_dir)
    print(f"Saved sample ground truth to: {filepath}")


if __name__ == "__main__":
    main()
