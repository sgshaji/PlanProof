"""
Spatial validation module.

Handles spatial metrics validation including setback distances, heights, areas,
and other geometric constraints.
"""

from typing import Dict, Any, Optional, List, TYPE_CHECKING

from planproof.rules.catalog import Rule
from planproof.pipeline.validators.constants import (
    ValidationStatus,
    ValidationSeverity,
)

if TYPE_CHECKING:
    from planproof.db import Database


def validate_spatial(rule: Rule, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Validate SPATIAL rules.

    Checks spatial metrics (setback distances, heights, areas) against
    policy thresholds.

    Args:
        rule: Spatial validation rule
        context: Context dictionary with submission_id, db, fields, etc.

    Returns:
        Validation finding dictionary or None if rule doesn't apply
    """
    submission_id = context.get("submission_id")
    db: Optional["Database"] = context.get("db")
    rule_config = rule.to_dict().get("config", {})

    if not submission_id or not db:
        return {
            "rule_id": rule.rule_id,
            "status": ValidationStatus.NEEDS_REVIEW.value,
            "severity": rule.severity,
            "message": "Cannot validate spatial rules: missing submission context",
            "missing_fields": [],
            "evidence": {}
        }

    from planproof.db import GeometryFeature, SpatialMetric
    session = db.get_session()

    try:
        # Get geometry features for this submission
        features = session.query(GeometryFeature).filter(
            GeometryFeature.submission_id == submission_id
        ).all()

        if not features:
            return {
                "rule_id": rule.rule_id,
                "status": ValidationStatus.NEEDS_REVIEW.value,
                "severity": ValidationSeverity.WARNING.value,
                "message": "No geometry features available for spatial validation",
                "missing_fields": ["geometry_features"],
                "evidence": {
                    "evidence_snippets": [{
                        "page": 1,
                        "snippet": "Spatial validation requires geometry features to be defined"
                    }]
                }
            }

        # Get spatial metrics
        all_metrics = []
        for feature in features:
            metrics = session.query(SpatialMetric).filter(
                SpatialMetric.geometry_feature_id == feature.id
            ).all()
            all_metrics.extend(metrics)

        if not all_metrics:
            return {
                "rule_id": rule.rule_id,
                "status": ValidationStatus.NEEDS_REVIEW.value,
                "severity": ValidationSeverity.WARNING.value,
                "message": "No spatial metrics computed for validation",
                "missing_fields": ["spatial_metrics"],
                "evidence": {
                    "evidence_snippets": [{
                        "page": 1,
                        "snippet": f"Found {len(features)} geometry features but no computed metrics"
                    }]
                }
            }

        # Check spatial constraints from rule config
        thresholds = rule_config.get("thresholds", {})

        if not thresholds:
            return {
                "rule_id": rule.rule_id,
                "status": ValidationStatus.NEEDS_REVIEW.value,
                "severity": ValidationSeverity.WARNING.value,
                "message": f"Spatial metrics present ({len(all_metrics)} metrics) but no policy thresholds configured",
                "missing_fields": [],
                "evidence": {
                    "evidence_snippets": [{
                        "page": 1,
                        "snippet": f"{m.metric_name}: {m.metric_value} {m.metric_unit}"
                    } for m in all_metrics[:5]],
                    "metrics_count": len(all_metrics),
                    "features_count": len(features)
                }
            }

        violations: List[str] = []
        evidence_snippets = []
        passed_checks: List[str] = []

        # Check setback distances
        if "min_setback" in thresholds:
            _check_setback_distances(
                all_metrics, thresholds["min_setback"],
                violations, evidence_snippets, passed_checks
            )

        # Check height limits
        if "max_height" in thresholds:
            _check_height_limits(
                all_metrics, thresholds["max_height"],
                violations, evidence_snippets, passed_checks
            )

        # Check area limits
        if "max_area" in thresholds or "min_area" in thresholds:
            _check_area_limits(
                all_metrics, thresholds,
                violations, evidence_snippets, passed_checks
            )

        # Determine status based on violations
        if violations:
            return {
                "rule_id": rule.rule_id,
                "status": ValidationStatus.FAIL.value,
                "severity": rule.severity,
                "message": f"Spatial violations found: {', '.join(violations[:3])}",
                "missing_fields": [],
                "evidence": {
                    "evidence_snippets": evidence_snippets,
                    "violations": violations,
                    "passed_checks": passed_checks,
                    "metrics_count": len(all_metrics),
                    "features_count": len(features)
                }
            }
        else:
            return {
                "rule_id": rule.rule_id,
                "status": ValidationStatus.PASS.value,
                "severity": rule.severity,
                "message": f"All spatial checks passed ({len(passed_checks)} checks)",
                "missing_fields": [],
                "evidence": {
                    "evidence_snippets": evidence_snippets[:10],
                    "passed_checks": passed_checks,
                    "metrics_count": len(all_metrics),
                    "features_count": len(features)
                }
            }

    finally:
        session.close()


def _check_setback_distances(
    all_metrics: List,
    min_setback: float,
    violations: List[str],
    evidence_snippets: List[Dict[str, Any]],
    passed_checks: List[str]
) -> None:
    """Check setback distance constraints."""
    setback_metrics = [
        m for m in all_metrics
        if "setback" in m.metric_name.lower() or "distance_to_boundary" in m.metric_name.lower()
    ]

    for metric in setback_metrics:
        try:
            value = float(metric.metric_value)
            if value < min_setback:
                violations.append(
                    f"{metric.metric_name}: {value}{metric.metric_unit} < {min_setback}{metric.metric_unit} (minimum)"
                )
                evidence_snippets.append({
                    "page": 1,
                    "snippet": f"VIOLATION: {metric.metric_name}: {value}{metric.metric_unit} < {min_setback}{metric.metric_unit}",
                    "metric_name": metric.metric_name,
                    "metric_value": value,
                    "metric_unit": metric.metric_unit,
                    "threshold": min_setback
                })
            else:
                passed_checks.append(
                    f"{metric.metric_name}: {value}{metric.metric_unit} >= {min_setback}{metric.metric_unit}"
                )
                evidence_snippets.append({
                    "page": 1,
                    "snippet": f"OK: {metric.metric_name}: {value}{metric.metric_unit}",
                    "metric_name": metric.metric_name,
                    "metric_value": value,
                    "metric_unit": metric.metric_unit
                })
        except (ValueError, TypeError):
            pass


def _check_height_limits(
    all_metrics: List,
    max_height: float,
    violations: List[str],
    evidence_snippets: List[Dict[str, Any]],
    passed_checks: List[str]
) -> None:
    """Check height limit constraints."""
    height_metrics = [m for m in all_metrics if "height" in m.metric_name.lower()]

    for metric in height_metrics:
        try:
            value = float(metric.metric_value)
            if value > max_height:
                violations.append(
                    f"{metric.metric_name}: {value}{metric.metric_unit} > {max_height}{metric.metric_unit} (maximum)"
                )
                evidence_snippets.append({
                    "page": 1,
                    "snippet": f"VIOLATION: {metric.metric_name}: {value}{metric.metric_unit} > {max_height}{metric.metric_unit}",
                    "metric_name": metric.metric_name,
                    "metric_value": value,
                    "metric_unit": metric.metric_unit,
                    "threshold": max_height
                })
            else:
                passed_checks.append(
                    f"{metric.metric_name}: {value}{metric.metric_unit} <= {max_height}{metric.metric_unit}"
                )
                evidence_snippets.append({
                    "page": 1,
                    "snippet": f"OK: {metric.metric_name}: {value}{metric.metric_unit}",
                    "metric_name": metric.metric_name,
                    "metric_value": value,
                    "metric_unit": metric.metric_unit
                })
        except (ValueError, TypeError):
            pass


def _check_area_limits(
    all_metrics: List,
    thresholds: Dict[str, Any],
    violations: List[str],
    evidence_snippets: List[Dict[str, Any]],
    passed_checks: List[str]
) -> None:
    """Check area limit constraints."""
    area_metrics = [
        m for m in all_metrics
        if "area" in m.metric_name.lower() or "footprint" in m.metric_name.lower()
    ]

    for metric in area_metrics:
        try:
            value = float(metric.metric_value)

            if "max_area" in thresholds:
                max_area = thresholds["max_area"]
                if value > max_area:
                    violations.append(
                        f"{metric.metric_name}: {value}{metric.metric_unit} > {max_area}{metric.metric_unit} (maximum)"
                    )
                    evidence_snippets.append({
                        "page": 1,
                        "snippet": f"VIOLATION: {metric.metric_name}: {value}{metric.metric_unit} > {max_area}{metric.metric_unit}",
                        "metric_name": metric.metric_name,
                        "metric_value": value,
                        "metric_unit": metric.metric_unit,
                        "threshold": max_area
                    })
                else:
                    passed_checks.append(
                        f"{metric.metric_name}: {value}{metric.metric_unit} <= {max_area}{metric.metric_unit}"
                    )

            if "min_area" in thresholds:
                min_area = thresholds["min_area"]
                if value < min_area:
                    violations.append(
                        f"{metric.metric_name}: {value}{metric.metric_unit} < {min_area}{metric.metric_unit} (minimum)"
                    )
                    evidence_snippets.append({
                        "page": 1,
                        "snippet": f"VIOLATION: {metric.metric_name}: {value}{metric.metric_unit} < {min_area}{metric.metric_unit}",
                        "metric_name": metric.metric_name,
                        "metric_value": value,
                        "metric_unit": metric.metric_unit,
                        "threshold": min_area
                    })
                else:
                    passed_checks.append(
                        f"{metric.metric_name}: {value}{metric.metric_unit} >= {min_area}{metric.metric_unit}"
                    )
        except (ValueError, TypeError):
            pass
