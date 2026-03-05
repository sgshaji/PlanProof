"""Precision, Recall, and F1 computation for SN-KG evaluation.

Computes metrics per entity type and relationship type by matching
predicted graph elements against ground truth annotations.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

import networkx as nx

from research.graph.schema import NodeType, EdgeType
from research.evaluation.ground_truth import (
    GroundTruthAnnotation,
    GroundTruthEntity,
    GroundTruthRelationship,
)

logger = logging.getLogger(__name__)

# Tolerance for numeric matching
AREA_MATCH_TOLERANCE = 0.10  # 10%
HEIGHT_MATCH_TOLERANCE = 0.15  # metres


@dataclass
class MetricResult:
    """Precision/Recall/F1 for a single category."""

    category: str
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0

    @property
    def precision(self) -> float:
        denom = self.true_positives + self.false_positives
        return self.true_positives / denom if denom > 0 else 0.0

    @property
    def recall(self) -> float:
        denom = self.true_positives + self.false_negatives
        return self.true_positives / denom if denom > 0 else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) > 0 else 0.0


@dataclass
class EvaluationResult:
    """Full evaluation result across all categories."""

    entity_metrics: dict[str, MetricResult] = field(default_factory=dict)
    relationship_metrics: dict[str, MetricResult] = field(default_factory=dict)
    conflict_metrics: Optional[MetricResult] = None
    overall_entity: Optional[MetricResult] = None
    overall_relationship: Optional[MetricResult] = None

    def to_dict(self) -> dict:
        """Convert to a serializable dict."""
        result = {}
        for category, mr in self.entity_metrics.items():
            result[f"entity/{category}"] = {
                "precision": mr.precision,
                "recall": mr.recall,
                "f1": mr.f1,
                "tp": mr.true_positives,
                "fp": mr.false_positives,
                "fn": mr.false_negatives,
            }
        for category, mr in self.relationship_metrics.items():
            result[f"relationship/{category}"] = {
                "precision": mr.precision,
                "recall": mr.recall,
                "f1": mr.f1,
                "tp": mr.true_positives,
                "fp": mr.false_positives,
                "fn": mr.false_negatives,
            }
        if self.conflict_metrics:
            result["conflicts"] = {
                "precision": self.conflict_metrics.precision,
                "recall": self.conflict_metrics.recall,
                "f1": self.conflict_metrics.f1,
            }
        if self.overall_entity:
            result["overall_entity"] = {
                "precision": self.overall_entity.precision,
                "recall": self.overall_entity.recall,
                "f1": self.overall_entity.f1,
            }
        if self.overall_relationship:
            result["overall_relationship"] = {
                "precision": self.overall_relationship.precision,
                "recall": self.overall_relationship.recall,
                "f1": self.overall_relationship.f1,
            }
        return result


def evaluate(
    G: nx.DiGraph,
    ground_truth: GroundTruthAnnotation,
) -> EvaluationResult:
    """Evaluate the SN-KG against ground truth.

    Args:
        G: The predicted SN-KG.
        ground_truth: The ground truth annotation.

    Returns:
        EvaluationResult with per-type and overall metrics.
    """
    result = EvaluationResult()

    # Evaluate entities by type
    predicted_entities = _extract_predicted_entities(G)
    gt_entities_by_type = _group_by_type(ground_truth.entities)
    pred_entities_by_type = _group_predicted_by_type(predicted_entities)

    all_entity_types = set(gt_entities_by_type.keys()) | set(pred_entities_by_type.keys())
    total_tp, total_fp, total_fn = 0, 0, 0

    for entity_type in all_entity_types:
        gt_list = gt_entities_by_type.get(entity_type, [])
        pred_list = pred_entities_by_type.get(entity_type, [])
        mr = _match_entities(entity_type, gt_list, pred_list)
        result.entity_metrics[entity_type] = mr
        total_tp += mr.true_positives
        total_fp += mr.false_positives
        total_fn += mr.false_negatives

    result.overall_entity = MetricResult(
        category="overall_entity",
        true_positives=total_tp,
        false_positives=total_fp,
        false_negatives=total_fn,
    )

    # Evaluate relationships by type
    predicted_rels = _extract_predicted_relationships(G)
    gt_rels_by_type = _group_rels_by_type(ground_truth.relationships)
    pred_rels_by_type = _group_pred_rels_by_type(predicted_rels)

    all_rel_types = set(gt_rels_by_type.keys()) | set(pred_rels_by_type.keys())
    total_tp, total_fp, total_fn = 0, 0, 0

    for rel_type in all_rel_types:
        gt_list = gt_rels_by_type.get(rel_type, [])
        pred_list = pred_rels_by_type.get(rel_type, [])
        mr = _match_relationships(rel_type, gt_list, pred_list)
        result.relationship_metrics[rel_type] = mr
        total_tp += mr.true_positives
        total_fp += mr.false_positives
        total_fn += mr.false_negatives

    result.overall_relationship = MetricResult(
        category="overall_relationship",
        true_positives=total_tp,
        false_positives=total_fp,
        false_negatives=total_fn,
    )

    # Evaluate conflicts
    if ground_truth.conflicts:
        result.conflict_metrics = _evaluate_conflicts(G, ground_truth)

    logger.info(
        "Evaluation: entity P=%.3f R=%.3f F1=%.3f | "
        "relationship P=%.3f R=%.3f F1=%.3f",
        result.overall_entity.precision, result.overall_entity.recall,
        result.overall_entity.f1,
        result.overall_relationship.precision, result.overall_relationship.recall,
        result.overall_relationship.f1,
    )

    return result


def _extract_predicted_entities(G: nx.DiGraph) -> list[dict]:
    """Extract entity-like nodes from the predicted graph."""
    entity_types = {
        NodeType.ROOM.value, NodeType.BUILDING.value,
        NodeType.BOUNDARY.value, NodeType.OPENING.value,
    }
    entities = []
    for nid, attrs in G.nodes(data=True):
        if attrs.get("node_type") in entity_types:
            entities.append({
                "node_id": nid,
                "entity_type": attrs["node_type"],
                "label": attrs.get("label", ""),
                "properties": {k: v for k, v in attrs.items()
                               if k not in ("node_type", "label")},
            })
    return entities


def _extract_predicted_relationships(G: nx.DiGraph) -> list[dict]:
    """Extract spatial relationship edges from the predicted graph."""
    spatial_edge_types = {
        EdgeType.CONTAINS.value, EdgeType.ADJACENT_TO.value,
        EdgeType.OPENS_INTO.value,
    }
    rels = []
    for u, v, attrs in G.edges(data=True):
        if attrs.get("edge_type") in spatial_edge_types:
            rels.append({
                "source": u,
                "target": v,
                "type": attrs["edge_type"],
                "source_label": G.nodes[u].get("label", ""),
                "target_label": G.nodes[v].get("label", ""),
            })
    return rels


def _group_by_type(entities: list[GroundTruthEntity]) -> dict[str, list]:
    groups: dict[str, list] = {}
    for e in entities:
        groups.setdefault(e.entity_type, []).append(e)
    return groups


def _group_predicted_by_type(entities: list[dict]) -> dict[str, list]:
    groups: dict[str, list] = {}
    for e in entities:
        groups.setdefault(e["entity_type"], []).append(e)
    return groups


def _group_rels_by_type(rels: list[GroundTruthRelationship]) -> dict[str, list]:
    groups: dict[str, list] = {}
    for r in rels:
        groups.setdefault(r.relationship_type, []).append(r)
    return groups


def _group_pred_rels_by_type(rels: list[dict]) -> dict[str, list]:
    groups: dict[str, list] = {}
    for r in rels:
        groups.setdefault(r["type"], []).append(r)
    return groups


def _match_entities(
    entity_type: str,
    gt_list: list[GroundTruthEntity],
    pred_list: list[dict],
) -> MetricResult:
    """Match predicted entities against ground truth for a given type."""
    mr = MetricResult(category=entity_type)
    matched_gt = set()
    matched_pred = set()

    for i, pred in enumerate(pred_list):
        for j, gt in enumerate(gt_list):
            if j in matched_gt:
                continue
            if _entity_matches(gt, pred):
                matched_gt.add(j)
                matched_pred.add(i)
                mr.true_positives += 1
                break

    mr.false_positives = len(pred_list) - len(matched_pred)
    mr.false_negatives = len(gt_list) - len(matched_gt)
    return mr


def _entity_matches(gt: GroundTruthEntity, pred: dict) -> bool:
    """Check if a predicted entity matches a ground truth entity."""
    # Label similarity
    gt_label = (gt.label or "").lower().strip()
    pred_label = (pred.get("label", "") or "").lower().strip()

    if gt_label and pred_label and gt_label == pred_label:
        return True

    # Match key comparison
    if gt.match_key:
        pred_key = pred.get("properties", {}).get("entity_key", "")
        if pred_key and gt.match_key.lower() in pred_key.lower():
            return True

    # Area-based matching for rooms
    gt_area = gt.properties.get("area")
    pred_area = pred.get("properties", {}).get("area")
    if gt_area is not None and pred_area is not None:
        try:
            diff = abs(float(gt_area) - float(pred_area))
            if diff / max(float(gt_area), 1e-9) <= AREA_MATCH_TOLERANCE:
                return True
        except (ValueError, TypeError):
            pass

    return False


def _match_relationships(
    rel_type: str,
    gt_list: list[GroundTruthRelationship],
    pred_list: list[dict],
) -> MetricResult:
    """Match predicted relationships against ground truth."""
    mr = MetricResult(category=rel_type)
    matched_gt = set()

    for pred in pred_list:
        for j, gt in enumerate(gt_list):
            if j in matched_gt:
                continue
            if _relationship_matches(gt, pred):
                matched_gt.add(j)
                mr.true_positives += 1
                break
        else:
            mr.false_positives += 1

    mr.false_negatives = len(gt_list) - len(matched_gt)
    return mr


def _relationship_matches(gt: GroundTruthRelationship, pred: dict) -> bool:
    """Check if a predicted relationship matches a ground truth one.

    Matches by endpoint labels since IDs differ between systems.
    """
    pred_src = pred.get("source_label", "").lower()
    pred_tgt = pred.get("target_label", "").lower()
    gt_src = gt.source_id.lower()
    gt_tgt = gt.target_id.lower()

    # Direct match
    if gt_src in pred_src and gt_tgt in pred_tgt:
        return True

    # Reverse match (for undirected relationships like ADJACENT_TO)
    if gt.relationship_type == "ADJACENT_TO":
        if gt_src in pred_tgt and gt_tgt in pred_src:
            return True

    return False


def _evaluate_conflicts(
    G: nx.DiGraph,
    ground_truth: GroundTruthAnnotation,
) -> MetricResult:
    """Evaluate conflict detection against ground truth conflicts."""
    mr = MetricResult(category="conflicts")

    # Get predicted conflicts (CONTRADICTS edges)
    pred_conflicts = []
    seen = set()
    for u, v, attrs in G.edges(data=True):
        if attrs.get("edge_type") == EdgeType.CONTRADICTS.value:
            cid = attrs.get("conflict_id", f"{u}_{v}")
            if cid not in seen:
                seen.add(cid)
                pred_conflicts.append({
                    "source": u,
                    "target": v,
                    "field_name": attrs.get("field_name", ""),
                    "conflict_type": attrs.get("conflict_type", ""),
                })

    matched_gt = set()
    for pred in pred_conflicts:
        matched = False
        for j, gt_conflict in enumerate(ground_truth.conflicts):
            if j in matched_gt:
                continue
            if _conflict_matches(gt_conflict, pred):
                matched_gt.add(j)
                mr.true_positives += 1
                matched = True
                break
        if not matched:
            mr.false_positives += 1

    mr.false_negatives = len(ground_truth.conflicts) - len(matched_gt)
    return mr


def _conflict_matches(gt, pred: dict) -> bool:
    """Check if a predicted conflict matches a ground truth conflict."""
    # Match by conflict type
    if gt.conflict_type != pred.get("conflict_type", ""):
        return False
    # Match by field name: either substring match or same domain
    gt_fn = gt.field_name.lower()
    pred_fn = pred.get("field_name", "").lower()
    if gt_fn in pred_fn or pred_fn in gt_fn:
        return True
    # Same measurement domain (e.g. floor_area ↔ living_room_area are both "area")
    area_kw = {"area", "sqm", "floor_area"}
    height_kw = {"height", "ridge", "eaves"}
    dist_kw = {"distance", "setback", "boundary"}
    for domain in (area_kw, height_kw, dist_kw):
        if any(k in gt_fn for k in domain) and any(k in pred_fn for k in domain):
            return True
    return False
