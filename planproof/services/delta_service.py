"""
Delta computation service - compute changes between V0 and V1+ submissions.
"""

from typing import Dict, Any, List, Optional, Tuple
import logging

from planproof.db import Database, ChangeSet, ChangeItem, ExtractedField, Document, SpatialMetric

LOGGER = logging.getLogger(__name__)


# High-impact fields for significance scoring
HIGH_IMPACT_FIELDS = {
    "site_address", "proposed_use", "building_height", "floor_area",
    "num_storeys", "application_type"
}

MEDIUM_IMPACT_FIELDS = {
    "postcode", "applicant_name", "agent_name", "description"
}


def compute_changeset(
    v0_submission_id: int,
    v1_submission_id: int,
    db: Optional[Database] = None
) -> int:
    """
    Compare V0 and V1+ submissions and generate ChangeSet with ChangeItems.
    
    Args:
        v0_submission_id: Parent submission ID (V0)
        v1_submission_id: Current submission ID (V1+)
        db: Optional Database instance
    
    Returns:
        changeset_id: ID of created ChangeSet
    
    Raises:
        ValueError: If submissions don't exist or are invalid
    """
    if db is None:
        db = Database()
    
    session = db.get_session()
    
    try:
        # Verify submissions exist
        from planproof.db import Submission
        v0_sub = session.query(Submission).filter(Submission.id == v0_submission_id).first()
        v1_sub = session.query(Submission).filter(Submission.id == v1_submission_id).first()
        
        if not v0_sub or not v1_sub:
            raise ValueError(f"Submissions not found: V0={v0_submission_id}, V1={v1_submission_id}")
        
        change_items = []
        
        # 1. Compute field deltas
        field_changes = _compute_field_deltas(v0_submission_id, v1_submission_id, session)
        change_items.extend(field_changes)
        
        # 2. Compute document deltas
        doc_changes = _compute_document_deltas(v0_submission_id, v1_submission_id, session)
        change_items.extend(doc_changes)
        
        # 3. Compute spatial metric deltas (if present)
        spatial_changes = _compute_spatial_metric_deltas(v0_submission_id, v1_submission_id, session)
        change_items.extend(spatial_changes)
        
        # 4. Calculate significance score
        significance = calculate_significance(change_items)
        
        # 5. Determine requires_validation flag
        requires_validation = "yes" if significance > 0.3 else ("partial" if significance > 0.1 else "no")
        
        # 6. Create ChangeSet
        changeset = ChangeSet(
            submission_id=v1_submission_id,
            parent_submission_id=v0_submission_id,
            significance_score=significance,
            requires_validation=requires_validation
        )
        
        session.add(changeset)
        session.flush()  # Get changeset ID
        
        # 7. Create ChangeItems
        for item_data in change_items:
            change_item = ChangeItem(
                change_set_id=changeset.id,
                change_type=item_data["change_type"],
                field_key=item_data.get("field_key"),
                document_type=item_data.get("document_type"),
                old_value=item_data.get("old_value"),
                new_value=item_data.get("new_value"),
                change_metadata=item_data.get("metadata", {})
            )
            session.add(change_item)
        
        session.commit()
        session.refresh(changeset)
        
        LOGGER.info(
            f"ChangeSet created: ID={changeset.id}, V0={v0_submission_id}, V1={v1_submission_id}, "
            f"significance={significance:.2f}, items={len(change_items)}"
        )
        
        return changeset.id
    
    except Exception as e:
        session.rollback()
        LOGGER.error(f"Error computing changeset: {str(e)}")
        raise
    
    finally:
        session.close()


def _compute_field_deltas(
    v0_submission_id: int,
    v1_submission_id: int,
    session: Any
) -> List[Dict[str, Any]]:
    """Compute field-level changes between submissions."""
    changes = []
    
    # Get all fields from both submissions
    v0_fields = session.query(ExtractedField).filter(
        ExtractedField.submission_id == v0_submission_id
    ).all()
    
    v1_fields = session.query(ExtractedField).filter(
        ExtractedField.submission_id == v1_submission_id
    ).all()
    
    # Build field maps
    v0_map = {f.field_name: f.field_value for f in v0_fields}
    v1_map = {f.field_name: f.field_value for f in v1_fields}
    
    # Find all unique field keys
    all_keys = set(v0_map.keys()) | set(v1_map.keys())
    
    for key in all_keys:
        v0_val = v0_map.get(key)
        v1_val = v1_map.get(key)
        
        if v0_val != v1_val:
            changes.append({
                "change_type": "field_delta",
                "field_key": key,
                "old_value": str(v0_val) if v0_val is not None else None,
                "new_value": str(v1_val) if v1_val is not None else None,
                "metadata": {
                    "action": "added" if v0_val is None else ("removed" if v1_val is None else "modified")
                }
            })
    
    return changes


def _compute_document_deltas(
    v0_submission_id: int,
    v1_submission_id: int,
    session: Any
) -> List[Dict[str, Any]]:
    """Compute document-level changes between submissions."""
    changes = []
    
    # Get all documents from both submissions
    v0_docs = session.query(Document).filter(
        Document.submission_id == v0_submission_id
    ).all()
    
    v1_docs = session.query(Document).filter(
        Document.submission_id == v1_submission_id
    ).all()
    
    # Build document maps by content_hash
    v0_hashes = {doc.content_hash: doc for doc in v0_docs if doc.content_hash}
    v1_hashes = {doc.content_hash: doc for doc in v1_docs if doc.content_hash}
    
    # Find added documents
    added_hashes = set(v1_hashes.keys()) - set(v0_hashes.keys())
    for hash_val in added_hashes:
        doc = v1_hashes[hash_val]
        changes.append({
            "change_type": "document_delta",
            "document_type": doc.document_type,
            "old_value": None,
            "new_value": doc.filename,
            "metadata": {
                "action": "added",
                "content_hash": hash_val
            }
        })
    
    # Find removed documents
    removed_hashes = set(v0_hashes.keys()) - set(v1_hashes.keys())
    for hash_val in removed_hashes:
        doc = v0_hashes[hash_val]
        changes.append({
            "change_type": "document_delta",
            "document_type": doc.document_type,
            "old_value": doc.filename,
            "new_value": None,
            "metadata": {
                "action": "removed",
                "content_hash": hash_val
            }
        })
    
    # Check for replaced documents (same type, different hash)
    v0_by_type = {}
    for doc in v0_docs:
        if doc.document_type:
            v0_by_type.setdefault(doc.document_type, []).append(doc)
    
    v1_by_type = {}
    for doc in v1_docs:
        if doc.document_type:
            v1_by_type.setdefault(doc.document_type, []).append(doc)
    
    for doc_type in set(v0_by_type.keys()) & set(v1_by_type.keys()):
        v0_type_hashes = {doc.content_hash for doc in v0_by_type[doc_type] if doc.content_hash}
        v1_type_hashes = {doc.content_hash for doc in v1_by_type[doc_type] if doc.content_hash}
        
        if v0_type_hashes != v1_type_hashes:
            changes.append({
                "change_type": "document_delta",
                "document_type": doc_type,
                "old_value": f"{len(v0_type_hashes)} document(s)",
                "new_value": f"{len(v1_type_hashes)} document(s)",
                "metadata": {
                    "action": "replaced"
                }
            })
    
    return changes


def _compute_spatial_metric_deltas(
    v0_submission_id: int,
    v1_submission_id: int,
    session: Any
) -> List[Dict[str, Any]]:
    """Compute spatial metric changes between submissions."""
    changes = []
    
    # Get spatial metrics from both submissions (via geometry features)
    from planproof.db import GeometryFeature
    
    v0_features = session.query(GeometryFeature).filter(
        GeometryFeature.submission_id == v0_submission_id
    ).all()
    
    v1_features = session.query(GeometryFeature).filter(
        GeometryFeature.submission_id == v1_submission_id
    ).all()
    
    if not v0_features and not v1_features:
        return changes  # No spatial data
    
    # Build metric maps
    v0_metrics = {}
    for feature in v0_features:
        for metric in feature.spatial_metrics:
            key = f"{feature.feature_type}_{metric.metric_name}"
            v0_metrics[key] = metric.metric_value
    
    v1_metrics = {}
    for feature in v1_features:
        for metric in feature.spatial_metrics:
            key = f"{feature.feature_type}_{metric.metric_name}"
            v1_metrics[key] = metric.metric_value
    
    # Find changes
    all_keys = set(v0_metrics.keys()) | set(v1_metrics.keys())
    
    for key in all_keys:
        v0_val = v0_metrics.get(key)
        v1_val = v1_metrics.get(key)
        
        if v0_val != v1_val:
            changes.append({
                "change_type": "spatial_metric_delta",
                "field_key": key,
                "old_value": str(v0_val) if v0_val is not None else None,
                "new_value": str(v1_val) if v1_val is not None else None,
                "metadata": {
                    "action": "added" if v0_val is None else ("removed" if v1_val is None else "modified")
                }
            })
    
    return changes


def calculate_significance(change_items: List[Dict[str, Any]]) -> float:
    """
    Calculate significance score (0.0-1.0) based on change types and impacted fields.
    
    High-impact changes: site_address, proposed_use, building_height (0.8-1.0)
    Medium-impact changes: document replacements (0.4-0.6)
    Low-impact changes: minor field updates (0.1-0.3)
    """
    if not change_items:
        return 0.0
    
    scores = []
    
    for item in change_items:
        change_type = item.get("change_type")
        field_key = item.get("field_key", "")
        action = item.get("metadata", {}).get("action", "")
        
        if change_type == "field_delta":
            if field_key in HIGH_IMPACT_FIELDS:
                scores.append(0.9)
            elif field_key in MEDIUM_IMPACT_FIELDS:
                scores.append(0.5)
            else:
                scores.append(0.2)
        
        elif change_type == "document_delta":
            if action == "replaced":
                scores.append(0.6)
            elif action in ["added", "removed"]:
                scores.append(0.4)
        
        elif change_type == "spatial_metric_delta":
            scores.append(0.7)  # Spatial changes are generally significant
    
    # Return max score (most significant change)
    return max(scores) if scores else 0.0


def get_impacted_rules(changeset_id: int, db: Optional[Database] = None) -> List[str]:
    """
    Get list of rule_ids that need revalidation based on the changeset.
    
    This maps changed fields/documents to rules that depend on them.
    """
    if db is None:
        db = Database()
    
    session = db.get_session()
    
    try:
        # Get change items
        change_items = session.query(ChangeItem).filter(
            ChangeItem.change_set_id == changeset_id
        ).all()
        
        changed_fields = {item.field_key for item in change_items if item.change_type == "field_delta" and item.field_key}
        changed_docs = {item.document_type for item in change_items if item.change_type == "document_delta" and item.document_type}
        
        # Rule dependency mapping (should be loaded from rule catalog)
        # For now, use a simple heuristic: all rules need revalidation if any change
        # In production, this would query the rule catalog for dependencies
        
        impacted_rules = []
        
        # Load all active rules and check dependencies
        from planproof.db import Rule
        rules = session.query(Rule).filter(Rule.is_active == "yes").all()
        
        for rule in rules:
            required_fields = rule.required_fields or []
            
            # Check if any required field changed
            if any(field in changed_fields for field in required_fields):
                impacted_rules.append(rule.rule_id)
        
        return impacted_rules
    
    finally:
        session.close()

