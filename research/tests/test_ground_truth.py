"""Tests for ground truth annotation I/O."""

import json
import os
import tempfile
import pytest

from research.evaluation.ground_truth import (
    GroundTruthAnnotation,
    GroundTruthEntity,
    GroundTruthRelationship,
    GroundTruthConflict,
)


def _make_annotation():
    """Create a test annotation."""
    return GroundTruthAnnotation(
        submission_id=1,
        annotator="test",
        annotation_date="2026-03-04",
        entities=[
            GroundTruthEntity(
                entity_id="room_1", entity_type="Room",
                label="Kitchen", properties={"area": 15.0},
                match_key="kitchen_15",
            ),
            GroundTruthEntity(
                entity_id="room_2", entity_type="Room",
                label="Bedroom", properties={"area": 12.0},
                match_key="bedroom_12",
            ),
        ],
        relationships=[
            GroundTruthRelationship(
                source_id="room_1", target_id="room_2",
                relationship_type="ADJACENT_TO",
            ),
        ],
        conflicts=[
            GroundTruthConflict(
                conflict_id="c1", conflict_type="area",
                entity_a_id="room_1", entity_b_id="room_1",
                field_name="floor_area", value_a="15", value_b="13",
                severity="medium",
            ),
        ],
        expected_verdicts={"RULE-1": "pass", "RULE-2": "fail"},
    )


class TestGroundTruthAnnotation:
    def test_save_and_load(self, tmp_path):
        annotation = _make_annotation()
        filepath = annotation.save(str(tmp_path))

        loaded = GroundTruthAnnotation.load(filepath)
        assert loaded.submission_id == 1
        assert loaded.annotator == "test"
        assert len(loaded.entities) == 2
        assert len(loaded.relationships) == 1
        assert len(loaded.conflicts) == 1
        assert loaded.expected_verdicts["RULE-1"] == "pass"

    def test_load_all(self, tmp_path):
        for sid in [1, 2, 3]:
            ann = _make_annotation()
            ann.submission_id = sid
            ann.save(str(tmp_path))

        loaded = GroundTruthAnnotation.load_all(str(tmp_path))
        assert len(loaded) == 3

    def test_entity_properties_preserved(self, tmp_path):
        annotation = _make_annotation()
        filepath = annotation.save(str(tmp_path))
        loaded = GroundTruthAnnotation.load(filepath)

        assert loaded.entities[0].label == "Kitchen"
        assert loaded.entities[0].properties["area"] == 15.0
        assert loaded.entities[0].match_key == "kitchen_15"

    def test_empty_dir(self, tmp_path):
        loaded = GroundTruthAnnotation.load_all(str(tmp_path))
        assert loaded == []

    def test_nonexistent_dir(self):
        loaded = GroundTruthAnnotation.load_all("/nonexistent/path")
        assert loaded == []
