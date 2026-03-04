"""Tests for evaluation metrics computation."""

import pytest
import networkx as nx

from research.graph.schema import NodeType, EdgeType
from research.evaluation.ground_truth import (
    GroundTruthAnnotation,
    GroundTruthEntity,
    GroundTruthRelationship,
)
from research.evaluation.metrics import evaluate, MetricResult


def _make_predicted_graph():
    """Create a predicted graph for testing."""
    G = nx.DiGraph()
    G.add_node("room_1", node_type=NodeType.ROOM.value, label="Kitchen",
               entity_key="kitchen", area=15.0)
    G.add_node("room_2", node_type=NodeType.ROOM.value, label="Bedroom",
               entity_key="bedroom", area=12.0)
    G.add_node("room_3", node_type=NodeType.ROOM.value, label="Hallway",
               entity_key="hallway")  # False positive
    G.add_node("door_1", node_type=NodeType.OPENING.value, label="Front Door")

    G.add_edge("room_1", "room_2", edge_type=EdgeType.ADJACENT_TO.value)
    G.add_edge("door_1", "room_1", edge_type=EdgeType.OPENS_INTO.value)
    return G


def _make_ground_truth():
    """Create ground truth matching the predicted graph."""
    return GroundTruthAnnotation(
        submission_id=1,
        annotator="test",
        annotation_date="2026-03-04",
        entities=[
            GroundTruthEntity("gt_1", "Room", "Kitchen",
                              properties={"area": 15.0}, match_key="kitchen"),
            GroundTruthEntity("gt_2", "Room", "Bedroom",
                              properties={"area": 12.0}, match_key="bedroom"),
            GroundTruthEntity("gt_3", "Room", "Bathroom",
                              properties={"area": 5.0}, match_key="bathroom"),  # False negative
        ],
        relationships=[
            GroundTruthRelationship("gt_1", "gt_2", "ADJACENT_TO"),
        ],
    )


class TestMetricResult:
    def test_precision(self):
        mr = MetricResult("test", true_positives=3, false_positives=1, false_negatives=0)
        assert mr.precision == 0.75

    def test_recall(self):
        mr = MetricResult("test", true_positives=3, false_positives=0, false_negatives=1)
        assert mr.recall == 0.75

    def test_f1(self):
        mr = MetricResult("test", true_positives=2, false_positives=1, false_negatives=1)
        assert mr.precision == pytest.approx(2 / 3)
        assert mr.recall == pytest.approx(2 / 3)
        assert mr.f1 == pytest.approx(2 / 3)

    def test_zero_division(self):
        mr = MetricResult("test", true_positives=0, false_positives=0, false_negatives=0)
        assert mr.precision == 0.0
        assert mr.recall == 0.0
        assert mr.f1 == 0.0


class TestEvaluate:
    def test_basic_evaluation(self):
        G = _make_predicted_graph()
        gt = _make_ground_truth()
        result = evaluate(G, gt)

        # Check entity metrics exist
        assert "Room" in result.entity_metrics

        # Overall entity: 2 TP (Kitchen, Bedroom), 1 FP (Hallway), 1 FN (Bathroom)
        assert result.overall_entity is not None
        assert result.overall_entity.true_positives == 2
        assert result.overall_entity.false_negatives == 1

    def test_result_to_dict(self):
        G = _make_predicted_graph()
        gt = _make_ground_truth()
        result = evaluate(G, gt)
        d = result.to_dict()
        assert "entity/Room" in d
        assert "overall_entity" in d
        assert "precision" in d["overall_entity"]
