"""
Integration tests for MVP workflow end-to-end.
"""

import pytest
import os
from pathlib import Path

# Skip if missing required environment variables
required_env = [
    "DATABASE_URL",
    "AZURE_STORAGE_CONNECTION_STRING",
    "AZURE_DOCINTEL_ENDPOINT",
    "AZURE_DOCINTEL_KEY",
]
missing_env = [name for name in required_env if not os.getenv(name)]
if missing_env:
    pytest.skip(
        f"Missing required environment variables: {', '.join(missing_env)}",
        allow_module_level=True,
    )


def test_rule_catalog_loads_with_categories():
    """Test that rule catalog loads with all rule categories."""
    from planproof.pipeline.validate import load_rule_catalog
    
    rules = load_rule_catalog("artefacts/rule_catalog.json")
    
    assert len(rules) > 0
    
    # Check that all rules have categories
    for rule in rules:
        assert hasattr(rule, 'rule_category')
        assert rule.rule_category in [
            "FIELD_REQUIRED",
            "DOCUMENT_REQUIRED",
            "CONSISTENCY",
            "MODIFICATION",
            "SPATIAL"
        ]
    
    # Check that we have at least one rule of each critical category
    categories = {rule.rule_category for rule in rules}
    assert "DOCUMENT_REQUIRED" in categories
    assert "CONSISTENCY" in categories
    assert "MODIFICATION" in categories


def test_document_required_rules_exist():
    """Test that DOCUMENT_REQUIRED rules are in catalog."""
    from planproof.pipeline.validate import load_rule_catalog
    
    rules = load_rule_catalog("artefacts/rule_catalog.json")
    
    doc_required_rules = [r for r in rules if r.rule_category == "DOCUMENT_REQUIRED"]
    
    assert len(doc_required_rules) >= 2
    
    # Check for specific rules
    rule_ids = {r.rule_id for r in doc_required_rules}
    assert "R-DOC-001" in rule_ids  # Application Form Required
    assert "R-DOC-002" in rule_ids  # Site Plan Required


def test_consistency_rules_exist():
    """Test that CONSISTENCY rules are in catalog."""
    from planproof.pipeline.validate import load_rule_catalog
    
    rules = load_rule_catalog("artefacts/rule_catalog.json")
    
    consistency_rules = [r for r in rules if r.rule_category == "CONSISTENCY"]
    
    assert len(consistency_rules) >= 2
    
    # Check for specific rules
    rule_ids = {r.rule_id for r in consistency_rules}
    assert "R-CONS-001" in rule_ids  # Postcode Consistency
    assert "R-CONS-002" in rule_ids  # Site Address Consistency


def test_modification_rules_exist():
    """Test that MODIFICATION rules are in catalog."""
    from planproof.pipeline.validate import load_rule_catalog
    
    rules = load_rule_catalog("artefacts/rule_catalog.json")
    
    modification_rules = [r for r in rules if r.rule_category == "MODIFICATION"]
    
    assert len(modification_rules) >= 1
    
    # Check for specific rules
    rule_ids = {r.rule_id for r in modification_rules}
    assert "R-MOD-001" in rule_ids  # Modification Parent Reference


def test_database_models_exist():
    """Test that new database models are properly defined."""
    from planproof.db import OfficerOverride, FieldResolution
    
    # Check OfficerOverride model
    assert hasattr(OfficerOverride, 'override_id')
    assert hasattr(OfficerOverride, 'validation_result_id')
    assert hasattr(OfficerOverride, 'original_status')
    assert hasattr(OfficerOverride, 'override_status')
    assert hasattr(OfficerOverride, 'notes')
    assert hasattr(OfficerOverride, 'officer_id')
    
    # Check FieldResolution model
    assert hasattr(FieldResolution, 'resolution_id')
    assert hasattr(FieldResolution, 'submission_id')
    assert hasattr(FieldResolution, 'field_key')
    assert hasattr(FieldResolution, 'chosen_value')
    assert hasattr(FieldResolution, 'officer_id')


def test_changeset_model_exists():
    """Test that ChangeSet and ChangeItem models exist."""
    from planproof.db import ChangeSet, ChangeItem
    
    # Check ChangeSet model
    assert hasattr(ChangeSet, 'id')
    assert hasattr(ChangeSet, 'submission_id')
    assert hasattr(ChangeSet, 'parent_submission_id')
    assert hasattr(ChangeSet, 'significance_score')
    assert hasattr(ChangeSet, 'requires_validation')
    
    # Check ChangeItem model (check table name to verify it exists)
    assert ChangeItem.__tablename__ == 'change_items'
    # Verify key columns exist
    assert any(col.name == 'change_set_id' for col in ChangeItem.__table__.columns)
    assert any(col.name == 'change_type' for col in ChangeItem.__table__.columns)


def test_ui_pages_exist():
    """Test that all UI pages are properly created."""
    from pathlib import Path
    
    ui_dir = Path("planproof/ui/pages")
    
    # Check that all pages exist
    assert (ui_dir / "upload.py").exists()
    assert (ui_dir / "status.py").exists()
    assert (ui_dir / "results.py").exists()
    assert (ui_dir / "case_overview.py").exists()
    assert (ui_dir / "fields.py").exists()


def test_ui_components_exist():
    """Test that UI components are properly created."""
    from pathlib import Path
    
    components_dir = Path("planproof/ui/components")
    
    assert components_dir.exists()
    assert (components_dir / "document_viewer.py").exists()


def test_services_exist():
    """Test that service layer modules exist."""
    from pathlib import Path
    
    services_dir = Path("planproof/services")
    
    assert services_dir.exists()
    assert (services_dir / "officer_override.py").exists()
    assert (services_dir / "delta_service.py").exists()

