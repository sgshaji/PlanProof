"""Inter-rater reliability using Cohen's kappa.

Compares system conflict predictions against human annotations
to measure agreement beyond chance.
"""

import logging
from dataclasses import dataclass

import networkx as nx
from sklearn.metrics import cohen_kappa_score

from research.evaluation.ground_truth import GroundTruthAnnotation
from research.graph.schema import EdgeType

logger = logging.getLogger(__name__)


@dataclass
class InterRaterResult:
    """Result of inter-rater reliability analysis."""

    kappa: float
    n_items: int
    system_positive: int
    human_positive: int
    agreement_count: int
    interpretation: str


def compute_cohen_kappa(
    G: nx.DiGraph,
    ground_truth: GroundTruthAnnotation,
) -> InterRaterResult:
    """Compute Cohen's kappa between system conflict predictions and human annotations.

    For each ground truth conflict, checks whether the system also predicted
    a conflict (binary classification). Kappa measures agreement beyond chance.

    Args:
        G: The SN-KG with CONTRADICTS edges.
        ground_truth: Ground truth with conflict annotations.

    Returns:
        InterRaterResult with kappa score and interpretation.
    """
    # Build sets of conflict identifiers
    # System conflicts: use (conflict_type, field_name) as key
    system_conflicts = set()
    for u, v, attrs in G.edges(data=True):
        if attrs.get("edge_type") == EdgeType.CONTRADICTS.value:
            key = (
                attrs.get("conflict_type", ""),
                attrs.get("field_name", ""),
            )
            system_conflicts.add(key)

    # Human conflicts from ground truth
    human_conflicts = set()
    for c in ground_truth.conflicts:
        key = (c.conflict_type, c.field_name)
        human_conflicts.add(key)

    # Build the universe of all possible conflict items
    all_items = system_conflicts | human_conflicts

    if not all_items:
        logger.warning("No conflicts to compare — kappa undefined")
        return InterRaterResult(
            kappa=1.0, n_items=0, system_positive=0,
            human_positive=0, agreement_count=0,
            interpretation="perfect (vacuous)",
        )

    # Convert to binary labels
    system_labels = []
    human_labels = []
    for item in sorted(all_items):
        system_labels.append(1 if item in system_conflicts else 0)
        human_labels.append(1 if item in human_conflicts else 0)

    kappa = cohen_kappa_score(human_labels, system_labels)
    agreements = sum(s == h for s, h in zip(system_labels, human_labels))

    interpretation = _interpret_kappa(kappa)

    result = InterRaterResult(
        kappa=kappa,
        n_items=len(all_items),
        system_positive=len(system_conflicts),
        human_positive=len(human_conflicts),
        agreement_count=agreements,
        interpretation=interpretation,
    )

    logger.info(
        "Cohen's kappa: %.3f (%s), %d items, %d agreements",
        kappa, interpretation, len(all_items), agreements,
    )
    return result


def _interpret_kappa(kappa: float) -> str:
    """Interpret kappa value using Landis & Koch (1977) scale."""
    if kappa < 0:
        return "poor"
    if kappa < 0.20:
        return "slight"
    if kappa < 0.40:
        return "fair"
    if kappa < 0.60:
        return "moderate"
    if kappa < 0.80:
        return "substantial"
    return "almost perfect"
