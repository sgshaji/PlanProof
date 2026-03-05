"""End-to-end smoke test for the research pipeline.

Runs the full pipeline in-memory (no DB, no external services):
1. Construct a synthetic NetworkX graph
2. Run Leiden community detection
3. Run conflict detection
4. Create a ground truth annotation
5. Evaluate metrics (P/R/F1)
6. Run perturbation sweep
7. Assert the pipeline produces valid output
"""

import pytest
import networkx as nx

from research.config import ResearchConfig
from research.graph.schema import NodeType, EdgeType
from research.graph.nx_utils import (
    graph_summary,
    add_community_nodes,
    spatial_subgraph,
)
from research.community.leiden import run_leiden
from research.conflict.detector import detect_conflicts
from research.conflict.contradicts import add_contradicts_edges, conflict_summary
from research.evaluation.ground_truth import (
    GroundTruthAnnotation,
    GroundTruthEntity,
    GroundTruthRelationship,
    GroundTruthConflict,
)
from research.evaluation.metrics import evaluate
from research.evaluation.perturbation import (
    drop_entities,
    perturb_attributes,
    drop_relationships,
    sweep_degradation,
)


def _build_synthetic_graph() -> nx.DiGraph:
    """Build a small SN-KG with rooms, building, boundary, claims, and pages."""
    G = nx.DiGraph()

    # Building
    G.add_node("building_1", node_type=NodeType.BUILDING.value,
               label="Main Dwelling", address="12 Oak Lane")

    # Rooms
    G.add_node("room_kitchen", node_type=NodeType.ROOM.value,
               label="Kitchen", area=15.0)
    G.add_node("room_lounge", node_type=NodeType.ROOM.value,
               label="Lounge", area=22.5)
    G.add_node("room_bedroom", node_type=NodeType.ROOM.value,
               label="Bedroom 1", area=18.0)

    # Boundary
    G.add_node("boundary_north", node_type=NodeType.BOUNDARY.value,
               label="North Boundary", distance_to_building=2.0)

    # Page and document
    G.add_node("doc_1", node_type=NodeType.PLANNING_DOCUMENT.value,
               label="Application Form")
    G.add_node("page_1", node_type=NodeType.PAGE.value, label="Page 1")

    # Claims (form values)
    G.add_node("claim_area_form", node_type=NodeType.CLAIM.value,
               label="area: 15 sqm", field_name="floor_area",
               field_value="15", field_unit="sqm", source="form")
    G.add_node("claim_area_drawing", node_type=NodeType.CLAIM.value,
               label="area: 18.5 sqm", field_name="floor_area",
               field_value="18.5", field_unit="sqm", source="geometry")
    G.add_node("claim_height_form", node_type=NodeType.CLAIM.value,
               label="height: 8.5m", field_name="ridge_height",
               field_value="8.5", field_unit="m", source="form")
    G.add_node("claim_height_drawing", node_type=NodeType.CLAIM.value,
               label="height: 9.2m", field_name="ridge_height",
               field_value="9.2", field_unit="m", source="geometry")

    # Spatial edges
    G.add_edge("building_1", "room_kitchen",
               edge_type=EdgeType.CONTAINS.value)
    G.add_edge("building_1", "room_lounge",
               edge_type=EdgeType.CONTAINS.value)
    G.add_edge("building_1", "room_bedroom",
               edge_type=EdgeType.CONTAINS.value)
    G.add_edge("room_kitchen", "room_lounge",
               edge_type=EdgeType.ADJACENT_TO.value)
    G.add_edge("room_lounge", "room_kitchen",
               edge_type=EdgeType.ADJACENT_TO.value)
    G.add_edge("boundary_north", "building_1",
               edge_type=EdgeType.OPENS_INTO.value)

    # Provenance edges
    G.add_edge("doc_1", "page_1", edge_type=EdgeType.EXTRACTED_FROM.value)
    G.add_edge("claim_area_form", "page_1",
               edge_type=EdgeType.EXTRACTED_FROM.value)
    G.add_edge("claim_height_form", "page_1",
               edge_type=EdgeType.EXTRACTED_FROM.value)

    return G


def _build_ground_truth() -> GroundTruthAnnotation:
    """Build a ground truth annotation matching the synthetic graph."""
    return GroundTruthAnnotation(
        submission_id=1,
        annotator="test",
        annotation_date="2026-03-04",
        is_synthetic=True,
        entities=[
            GroundTruthEntity("room_kitchen", "Room", "Kitchen",
                              {"area": 15.0}, "kitchen"),
            GroundTruthEntity("room_lounge", "Room", "Lounge",
                              {"area": 22.5}, "lounge"),
            GroundTruthEntity("room_bedroom", "Room", "Bedroom 1",
                              {"area": 18.0}, "bedroom_1"),
            GroundTruthEntity("building_main", "Building", "Main Dwelling",
                              {"ridge_height": 8.5}, "main_dwelling"),
            GroundTruthEntity("boundary_north", "Boundary", "North Boundary",
                              {"distance_to_building": 2.0}, "north_boundary"),
        ],
        relationships=[
            GroundTruthRelationship("Main Dwelling", "Kitchen", "CONTAINS"),
            GroundTruthRelationship("Main Dwelling", "Lounge", "CONTAINS"),
            GroundTruthRelationship("Kitchen", "Lounge", "ADJACENT_TO"),
            GroundTruthRelationship("North Boundary", "Main Dwelling",
                                   "OPENS_INTO"),
        ],
        conflicts=[
            GroundTruthConflict(
                "gt_conflict_1", "area", "room_kitchen", "room_kitchen",
                "floor_area", "15.0", "18.5", "high",
                "Kitchen area mismatch",
            ),
        ],
        expected_verdicts={
            "max_height_8m": "fail",
            "boundary_distance_1m": "pass",
        },
    )


class TestEndToEndPipeline:
    """Integration test: full research pipeline in-memory."""

    def test_graph_construction(self):
        G = _build_synthetic_graph()
        summary = graph_summary(G)

        assert summary["total_nodes"] == 11
        assert summary["total_edges"] == 9
        assert summary["nodes_by_type"][NodeType.ROOM.value] == 3
        assert summary["nodes_by_type"][NodeType.BUILDING.value] == 1
        assert summary["nodes_by_type"][NodeType.CLAIM.value] == 4

    def test_leiden_community_detection(self):
        G = _build_synthetic_graph()
        result = run_leiden(G, config=ResearchConfig(leiden_seed=42))

        assert result.num_communities >= 1
        assert len(result.community_map) > 0
        # Only spatial nodes should be in the community map
        spatial = spatial_subgraph(G)
        assert set(result.community_map.keys()) == set(spatial.nodes())

    def test_add_community_nodes(self):
        G = _build_synthetic_graph()
        result = run_leiden(G, config=ResearchConfig(leiden_seed=42))
        add_community_nodes(G, result.community_map)

        community_nodes = [
            n for n, d in G.nodes(data=True)
            if d.get("node_type") == NodeType.COMMUNITY.value
        ]
        assert len(community_nodes) == result.num_communities

    def test_conflict_detection(self):
        G = _build_synthetic_graph()
        cfg = ResearchConfig(area_tolerance_pct=0.10)
        conflicts = detect_conflicts(G, cfg)

        # Should detect the floor_area conflict (15 vs 18.5 = 23%)
        area_conflicts = [c for c in conflicts if c.conflict_type == "area"]
        assert len(area_conflicts) >= 1

    def test_contradicts_edges(self):
        G = _build_synthetic_graph()
        conflicts = detect_conflicts(G, ResearchConfig(area_tolerance_pct=0.10))
        add_contradicts_edges(G, conflicts)

        summary = conflict_summary(G)
        assert summary["total_conflicts"] >= 1

    def test_evaluation_metrics(self):
        G = _build_synthetic_graph()
        gt = _build_ground_truth()

        # Add CONTRADICTS edges for conflict evaluation
        conflicts = detect_conflicts(G, ResearchConfig(area_tolerance_pct=0.10))
        add_contradicts_edges(G, conflicts)

        result = evaluate(G, gt)

        # Entity metrics should exist
        assert result.overall_entity is not None
        assert result.overall_entity.precision >= 0.0
        assert result.overall_entity.recall >= 0.0
        assert result.overall_entity.f1 >= 0.0

        # Relationship metrics should exist
        assert result.overall_relationship is not None

        # Should be serializable
        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)

    def test_perturbation_drop_entities(self):
        G = _build_synthetic_graph()
        degraded = drop_entities(G, rate=0.5, seed=42)

        spatial_original = spatial_subgraph(G)
        spatial_degraded = spatial_subgraph(degraded)
        assert spatial_degraded.number_of_nodes() < spatial_original.number_of_nodes()

    def test_perturbation_perturb_attributes(self):
        G = _build_synthetic_graph()
        perturbed = perturb_attributes(G, noise_std=0.1, seed=42)

        # Claim values should have changed
        original_val = G.nodes["claim_area_form"].get("field_value")
        perturbed_val = perturbed.nodes["claim_area_form"].get("field_value")
        assert original_val != perturbed_val

    def test_perturbation_drop_relationships(self):
        G = _build_synthetic_graph()
        degraded = drop_relationships(G, rate=0.5, seed=42)
        assert degraded.number_of_edges() < G.number_of_edges()

    def test_sweep_degradation(self):
        G = _build_synthetic_graph()
        rates = [0.0, 0.2, 0.5]
        results = sweep_degradation(G, rates=rates, config=ResearchConfig())

        assert len(results) == 3
        # Rate 0.0 should preserve the graph
        assert results[0][0] == 0.0
        # Higher rates should degrade more
        nodes_at_0 = results[0][1].number_of_nodes()
        nodes_at_50 = results[2][1].number_of_nodes()
        assert nodes_at_50 <= nodes_at_0

    def test_ground_truth_roundtrip(self, tmp_path):
        gt = _build_ground_truth()
        filepath = gt.save(str(tmp_path))

        loaded = GroundTruthAnnotation.load(filepath)
        assert loaded.submission_id == gt.submission_id
        assert len(loaded.entities) == len(gt.entities)
        assert len(loaded.relationships) == len(gt.relationships)
        assert len(loaded.conflicts) == len(gt.conflicts)

    def test_full_pipeline_wiring(self):
        """Verify all modules wire together end-to-end."""
        G = _build_synthetic_graph()
        gt = _build_ground_truth()
        cfg = ResearchConfig(
            area_tolerance_pct=0.10,
            leiden_seed=42,
            random_seed=42,
        )

        # Phase 1: Graph is already built

        # Phase 2: Community detection
        leiden_result = run_leiden(G, config=cfg)
        add_community_nodes(G, leiden_result.community_map)

        # Phase 3: Conflict detection
        conflicts = detect_conflicts(G, cfg)
        add_contradicts_edges(G, conflicts)

        # Phase 4: Evaluation
        eval_result = evaluate(G, gt)
        assert eval_result.overall_entity is not None

        # Phase 5: Perturbation sweep with evaluation
        degradation_curve = []
        for rate in [0.0, 0.1, 0.3]:
            degraded = drop_entities(G, rate, seed=cfg.random_seed)
            degraded_eval = evaluate(degraded, gt)
            degradation_curve.append({
                "rate": rate,
                "entity_f1": degraded_eval.overall_entity.f1,
            })

        # F1 should generally decrease with more degradation
        assert len(degradation_curve) == 3
        assert degradation_curve[0]["entity_f1"] >= degradation_curve[2]["entity_f1"]
