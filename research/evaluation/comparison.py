"""Flat vs community-structured compliance comparison.

Runs Stage 3 flat validation and community-structured graph validation,
then compares both approaches against ground truth to determine
whether the graph approach improves compliance accuracy.
"""

import logging
from dataclasses import dataclass
from typing import Optional

import networkx as nx

from research.config import ResearchConfig
from research.evaluation.ground_truth import GroundTruthAnnotation
from research.evaluation.metrics import MetricResult
from research.graph.schema import NodeType, EdgeType
from research.community.leiden import LeidenResult
from research.conflict.contradicts import get_contradicts_edges

logger = logging.getLogger(__name__)


@dataclass
class ComplianceVerdict:
    """A single compliance verdict."""

    rule_id: str
    status: str  # "pass", "fail", "warning", "needs_review"
    source: str  # "flat" or "graph"
    confidence: float = 1.0
    details: str = ""


@dataclass
class ComparisonResult:
    """Result of comparing flat vs graph compliance."""

    flat_verdicts: list[ComplianceVerdict]
    graph_verdicts: list[ComplianceVerdict]
    flat_metrics: MetricResult
    graph_metrics: MetricResult
    agreements: int
    disagreements: int
    graph_only_correct: int  # Cases where graph was right but flat was wrong
    flat_only_correct: int  # Cases where flat was right but graph was wrong

    def improvement(self) -> float:
        """Compute F1 improvement of graph over flat."""
        return self.graph_metrics.f1 - self.flat_metrics.f1


def compare_flat_vs_graph(
    flat_validation_results: list[dict],
    G: nx.DiGraph,
    leiden_result: LeidenResult,
    ground_truth: GroundTruthAnnotation,
    config: Optional[ResearchConfig] = None,
) -> ComparisonResult:
    """Compare flat validation against graph-structured validation.

    Args:
        flat_validation_results: Results from Stage 3 validate_extraction().
        G: The SN-KG with communities and conflicts.
        leiden_result: Leiden partition result.
        ground_truth: Ground truth annotation.
        config: Research configuration.

    Returns:
        ComparisonResult with verdicts and metrics from both approaches.
    """
    # Convert flat results to verdicts
    flat_verdicts = _flat_to_verdicts(flat_validation_results)

    # Generate graph-based verdicts
    graph_verdicts = _graph_to_verdicts(G, leiden_result)

    # Evaluate both against ground truth
    flat_metrics = _evaluate_verdicts(flat_verdicts, ground_truth)
    graph_metrics = _evaluate_verdicts(graph_verdicts, ground_truth)

    # Compute agreement/disagreement
    agreements, disagreements = 0, 0
    graph_only_correct, flat_only_correct = 0, 0

    flat_by_rule = {v.rule_id: v for v in flat_verdicts}
    graph_by_rule = {v.rule_id: v for v in graph_verdicts}

    for rule_id in set(flat_by_rule.keys()) | set(graph_by_rule.keys()):
        flat_v = flat_by_rule.get(rule_id)
        graph_v = graph_by_rule.get(rule_id)
        expected = ground_truth.expected_verdicts.get(rule_id)

        if flat_v and graph_v:
            if flat_v.status == graph_v.status:
                agreements += 1
            else:
                disagreements += 1
                if expected:
                    if graph_v.status == expected and flat_v.status != expected:
                        graph_only_correct += 1
                    elif flat_v.status == expected and graph_v.status != expected:
                        flat_only_correct += 1

    result = ComparisonResult(
        flat_verdicts=flat_verdicts,
        graph_verdicts=graph_verdicts,
        flat_metrics=flat_metrics,
        graph_metrics=graph_metrics,
        agreements=agreements,
        disagreements=disagreements,
        graph_only_correct=graph_only_correct,
        flat_only_correct=flat_only_correct,
    )

    logger.info(
        "Comparison: flat F1=%.3f, graph F1=%.3f, improvement=%.3f, "
        "agreements=%d, disagreements=%d",
        flat_metrics.f1, graph_metrics.f1, result.improvement(),
        agreements, disagreements,
    )
    return result


def _flat_to_verdicts(flat_results: list[dict]) -> list[ComplianceVerdict]:
    """Convert flat validation results to ComplianceVerdict objects."""
    verdicts = []
    for r in flat_results:
        verdicts.append(ComplianceVerdict(
            rule_id=r.get("rule_id", ""),
            status=r.get("status", "pending"),
            source="flat",
            details=r.get("message", ""),
        ))
    return verdicts


def _graph_to_verdicts(
    G: nx.DiGraph,
    leiden_result: LeidenResult,
) -> list[ComplianceVerdict]:
    """Generate compliance verdicts from the graph structure.

    Uses community structure and conflict edges to produce verdicts.
    """
    verdicts = []

    # Conflict-based verdicts: any CONTRADICTS edge triggers a fail
    contradicts = get_contradicts_edges(G)
    conflict_fields = set()
    for edge in contradicts:
        field_name = edge.get("field_name", "")
        conflict_type = edge.get("conflict_type", "")
        severity = edge.get("severity", "medium")
        conflict_fields.add(field_name)
        verdicts.append(ComplianceVerdict(
            rule_id=f"CONFLICT-{conflict_type}-{field_name}",
            status="fail" if severity == "high" else "warning",
            source="graph",
            confidence=0.9,
            details=edge.get("description", ""),
        ))

    # Community-based verdicts: check spatial coherence
    community_map = leiden_result.community_map
    communities: dict[int, list[str]] = {}
    for nid, cid in community_map.items():
        communities.setdefault(cid, []).append(nid)

    for cid, members in communities.items():
        # Check if community has required spatial elements
        member_types = {G.nodes[m].get("node_type") for m in members if m in G.nodes}
        has_rooms = NodeType.ROOM.value in member_types
        has_boundary = NodeType.BOUNDARY.value in member_types

        if has_rooms and not has_boundary:
            verdicts.append(ComplianceVerdict(
                rule_id=f"SPATIAL-COMMUNITY-{cid}-boundary",
                status="warning",
                source="graph",
                confidence=0.7,
                details=f"Community {cid} has rooms but no boundary information",
            ))

    return verdicts


def _evaluate_verdicts(
    verdicts: list[ComplianceVerdict],
    ground_truth: GroundTruthAnnotation,
) -> MetricResult:
    """Evaluate verdicts against ground truth expected verdicts."""
    mr = MetricResult(category="compliance")
    expected = ground_truth.expected_verdicts

    verdict_by_rule = {v.rule_id: v.status for v in verdicts}

    for rule_id, expected_status in expected.items():
        predicted_status = verdict_by_rule.get(rule_id)
        if predicted_status is None:
            mr.false_negatives += 1
        elif predicted_status == expected_status:
            mr.true_positives += 1
        else:
            mr.false_positives += 1

    # Count predictions not in ground truth
    for rule_id in verdict_by_rule:
        if rule_id not in expected:
            mr.false_positives += 1

    return mr
