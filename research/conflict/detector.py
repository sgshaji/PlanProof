"""Cross-document conflict detection.

Traverses the SN-KG comparing Claim nodes (form values) against spatial
entity nodes (drawing values) to detect area, height, distance, and
address conflicts with configurable tolerance thresholds.
"""

import logging
import re
from dataclasses import dataclass
from typing import Optional

import networkx as nx

from research.config import ResearchConfig
from research.graph.schema import NodeType, EdgeType

logger = logging.getLogger(__name__)


@dataclass
class Conflict:
    """A detected conflict between two claims in the graph."""

    conflict_id: str
    conflict_type: str  # "area", "height", "distance", "address", "value"
    claim_a_id: str  # Node ID of first claim
    claim_b_id: str  # Node ID of second claim
    field_name: str
    value_a: str
    value_b: str
    unit: Optional[str]
    discrepancy: Optional[float]  # Absolute difference (for numeric)
    discrepancy_pct: Optional[float]  # Percentage difference
    severity: str  # "high", "medium", "low"
    description: str


def detect_conflicts(
    G: nx.DiGraph,
    config: Optional[ResearchConfig] = None,
) -> list[Conflict]:
    """Detect conflicts in the SN-KG.

    Compares claim nodes that share the same entity or field name
    but report different values. Applies tolerance thresholds from config.

    Args:
        G: The SN-KG DiGraph.
        config: Research configuration with tolerance thresholds.

    Returns:
        List of detected Conflict objects.
    """
    cfg = config or ResearchConfig()
    conflicts = []
    conflict_counter = 0

    # Collect all claim nodes
    claims = [
        (nid, attrs) for nid, attrs in G.nodes(data=True)
        if attrs.get("node_type") == NodeType.CLAIM.value
    ]

    # Group claims by field_name
    claims_by_field: dict[str, list[tuple[str, dict]]] = {}
    for nid, attrs in claims:
        field_name = attrs.get("field_name", "")
        if field_name:
            claims_by_field.setdefault(field_name, []).append((nid, attrs))

    # Compare claims with the same field name
    for field_name, field_claims in claims_by_field.items():
        if len(field_claims) < 2:
            continue

        for i, (id_a, attrs_a) in enumerate(field_claims):
            for id_b, attrs_b in field_claims[i + 1:]:
                val_a = attrs_a.get("field_value", "")
                val_b = attrs_b.get("field_value", "")

                if val_a == val_b:
                    continue  # No conflict

                conflict = _compare_values(
                    id_a, id_b, field_name, val_a, val_b,
                    attrs_a.get("field_unit"), cfg,
                )
                if conflict:
                    conflict_counter += 1
                    conflict.conflict_id = f"conflict_{conflict_counter}"
                    conflicts.append(conflict)

    # Also compare form claims vs geometry claims
    form_claims = [
        (nid, attrs) for nid, attrs in claims
        if attrs.get("source") != "geometry"
    ]
    geom_claims = [
        (nid, attrs) for nid, attrs in claims
        if attrs.get("source") == "geometry"
    ]
    for id_a, attrs_a in form_claims:
        for id_b, attrs_b in geom_claims:
            fn_a = attrs_a.get("field_name", "")
            fn_b = attrs_b.get("field_name", "")
            if not _fields_are_comparable(fn_a, fn_b):
                continue

            val_a = attrs_a.get("field_value", "")
            val_b = attrs_b.get("field_value", "")
            if val_a == val_b:
                continue

            conflict = _compare_values(
                id_a, id_b, fn_a, val_a, val_b,
                attrs_a.get("field_unit") or attrs_b.get("field_unit"), cfg,
            )
            if conflict:
                conflict_counter += 1
                conflict.conflict_id = f"conflict_{conflict_counter}"
                conflict.conflict_type = _classify_conflict_type(fn_a)
                conflicts.append(conflict)

    # Deduplicate: keep only the highest-discrepancy conflict per field_name
    conflicts = deduplicate_conflicts(conflicts)

    logger.info("Detected %d conflicts in graph (after dedup)", len(conflicts))
    return conflicts


def deduplicate_conflicts(conflicts: list[Conflict]) -> list[Conflict]:
    """Keep only the most significant conflict per field_name.

    When a measurement entity has N distinct values, the pairwise
    comparison produces C(N,2) conflicts.  Only the pair with
    the largest percentage discrepancy is meaningful — it represents
    the worst-case inconsistency for that field.

    Also groups semantically equivalent field names (e.g.
    bathroom_area vs bathroom_dimensions) by their base entity
    and conflict type, keeping one winner per group.
    """
    if not conflicts:
        return []

    # Group by (base_entity, conflict_type) to collapse related fields
    groups: dict[tuple[str, str], list[Conflict]] = {}
    for c in conflicts:
        key = (_base_entity_name(c.field_name), c.conflict_type)
        groups.setdefault(key, []).append(c)

    deduped: list[Conflict] = []
    counter = 0
    for _key, group in groups.items():
        # Pick the conflict with the highest percentage discrepancy
        best = max(
            group,
            key=lambda c: c.discrepancy_pct if c.discrepancy_pct is not None else 0.0,
        )
        counter += 1
        best.conflict_id = f"conflict_{counter}"
        deduped.append(best)

    return deduped


def _base_entity_name(field_name: str) -> str:
    """Extract the base entity name, stripping measurement suffixes.

    E.g. "bathroom_area" → "bathroom", "bedroom_1_height" → "bedroom_1",
    "ridge_height" → "ridge", "living_room_area" → "living_room".
    """
    suffixes = (
        "_area", "_height", "_width", "_depth", "_length",
        "_distance", "_dimensions", "_setback", "_separation",
        "_sqm", "_value",
    )
    fn = field_name.lower()
    for suffix in suffixes:
        if fn.endswith(suffix):
            fn = fn[: -len(suffix)]
            break
    return fn


def _compare_values(
    id_a: str, id_b: str, field_name: str,
    val_a: str, val_b: str, unit: Optional[str],
    cfg: ResearchConfig,
) -> Optional[Conflict]:
    """Compare two claim values and return a Conflict if they disagree."""
    num_a = _parse_numeric(val_a)
    num_b = _parse_numeric(val_b)

    if num_a is not None and num_b is not None:
        return _compare_numeric(
            id_a, id_b, field_name, val_a, val_b,
            num_a, num_b, unit, cfg,
        )

    # String comparison (e.g., addresses)
    if val_a.strip().lower() != val_b.strip().lower():
        return Conflict(
            conflict_id="",
            conflict_type=_classify_conflict_type(field_name),
            claim_a_id=id_a,
            claim_b_id=id_b,
            field_name=field_name,
            value_a=val_a,
            value_b=val_b,
            unit=unit,
            discrepancy=None,
            discrepancy_pct=None,
            severity="medium",
            description=f"Value mismatch for '{field_name}': '{val_a}' vs '{val_b}'",
        )
    return None


def _compare_numeric(
    id_a: str, id_b: str, field_name: str,
    val_a: str, val_b: str,
    num_a: float, num_b: float, unit: Optional[str],
    cfg: ResearchConfig,
) -> Optional[Conflict]:
    """Compare numeric values with tolerance thresholds."""
    abs_diff = abs(num_a - num_b)
    pct_diff = abs_diff / max(abs(num_a), abs(num_b), 1e-9)

    # Determine tolerance based on field type
    conflict_type = _classify_conflict_type(field_name)
    if conflict_type == "area":
        threshold = cfg.area_tolerance_pct
    elif conflict_type == "height":
        threshold = cfg.height_tolerance_m / max(abs(num_a), abs(num_b), 1e-9)
    elif conflict_type == "distance":
        threshold = cfg.distance_tolerance_m / max(abs(num_a), abs(num_b), 1e-9)
    else:
        threshold = cfg.area_tolerance_pct  # Default

    if pct_diff <= threshold:
        return None  # Within tolerance

    severity = _severity_from_pct(pct_diff)

    return Conflict(
        conflict_id="",
        conflict_type=conflict_type,
        claim_a_id=id_a,
        claim_b_id=id_b,
        field_name=field_name,
        value_a=val_a,
        value_b=val_b,
        unit=unit,
        discrepancy=abs_diff,
        discrepancy_pct=pct_diff,
        severity=severity,
        description=(
            f"{conflict_type.title()} conflict for '{field_name}': "
            f"{num_a} vs {num_b} ({pct_diff:.1%} discrepancy)"
        ),
    )


def _parse_numeric(value: str) -> Optional[float]:
    """Try to parse a numeric value from a string."""
    if not value:
        return None
    # Remove common units and whitespace
    cleaned = re.sub(r"[^\d.\-]", "", value.strip())
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def _classify_conflict_type(field_name: str) -> str:
    """Classify the conflict type from the field name."""
    fn = field_name.lower()
    if "area" in fn or "sqm" in fn:
        return "area"
    if "height" in fn or "ridge" in fn or "eaves" in fn:
        return "height"
    if "distance" in fn or "boundary" in fn or "setback" in fn:
        return "distance"
    if "address" in fn:
        return "address"
    return "value"


def _fields_are_comparable(field_a: str, field_b: str) -> bool:
    """Check if two fields with different names are semantically comparable."""
    a = field_a.lower()
    b = field_b.lower()

    # Same field name
    if a == b:
        return True

    # Area fields
    area_keywords = {"area", "sqm", "floor_area", "site_area"}
    if any(k in a for k in area_keywords) and any(k in b for k in area_keywords):
        return True

    # Height fields
    height_keywords = {"height", "ridge", "eaves"}
    if any(k in a for k in height_keywords) and any(k in b for k in height_keywords):
        return True

    # Distance fields
    dist_keywords = {"distance", "boundary", "setback", "separation"}
    if any(k in a for k in dist_keywords) and any(k in b for k in dist_keywords):
        return True

    return False


def _severity_from_pct(pct_diff: float) -> str:
    """Determine conflict severity from percentage discrepancy."""
    if pct_diff > 0.25:
        return "high"
    if pct_diff > 0.10:
        return "medium"
    return "low"
