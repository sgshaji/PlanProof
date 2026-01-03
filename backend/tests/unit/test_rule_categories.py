"""
Unit tests for rule category framework and validators.
"""

import pytest
from unittest.mock import Mock, patch


def test_dispatch_by_category_document_required():
    """Test dispatcher routes DOCUMENT_REQUIRED rules correctly."""
    from planproof.pipeline.validate import _dispatch_by_category
    from planproof.rules.catalog import Rule, EvidenceExpectation
    
    rule = Rule(
        rule_id="R-DOC-001",
        title="Test Doc Required",
        description="Test",
        required_fields=["application_form"],
        evidence=EvidenceExpectation(source_types=["all"], keywords=[], min_confidence=0.6),
        rule_category="DOCUMENT_REQUIRED"
    )
    
    context = {
        "submission_id": 1,
        "db": Mock()
    }
    
    # Mock the validator to return a result
    with patch('planproof.pipeline.validate._validate_document_required') as mock_validator:
        mock_validator.return_value = {"status": "pass"}
        
        result = _dispatch_by_category(rule, context)
        
        mock_validator.assert_called_once_with(rule, context)


def test_dispatch_by_category_consistency():
    """Test dispatcher routes CONSISTENCY rules correctly."""
    from planproof.pipeline.validate import _dispatch_by_category
    from planproof.rules.catalog import Rule, EvidenceExpectation
    
    rule = Rule(
        rule_id="R-CONS-001",
        title="Test Consistency",
        description="Test",
        required_fields=["postcode"],
        evidence=EvidenceExpectation(source_types=["all"], keywords=[], min_confidence=0.6),
        rule_category="CONSISTENCY"
    )
    
    context = {
        "submission_id": 1,
        "db": Mock()
    }
    
    with patch('planproof.pipeline.validate._validate_consistency') as mock_validator:
        mock_validator.return_value = {"status": "pass"}
        
        result = _dispatch_by_category(rule, context)
        
        mock_validator.assert_called_once_with(rule, context)


def test_dispatch_by_category_modification():
    """Test dispatcher routes MODIFICATION rules correctly."""
    from planproof.pipeline.validate import _dispatch_by_category
    from planproof.rules.catalog import Rule, EvidenceExpectation
    
    rule = Rule(
        rule_id="R-MOD-001",
        title="Test Modification",
        description="Test",
        required_fields=[],
        evidence=EvidenceExpectation(source_types=["all"], keywords=[], min_confidence=0.6),
        rule_category="MODIFICATION"
    )
    
    context = {
        "submission_id": 1,
        "db": Mock()
    }
    
    with patch('planproof.pipeline.validate._validate_modification') as mock_validator:
        mock_validator.return_value = {"status": "pass"}
        
        result = _dispatch_by_category(rule, context)
        
        mock_validator.assert_called_once_with(rule, context)


def test_dispatch_by_category_field_required():
    """Test dispatcher returns None for FIELD_REQUIRED (handled by default logic)."""
    from planproof.pipeline.validate import _dispatch_by_category
    from planproof.rules.catalog import Rule, EvidenceExpectation
    
    rule = Rule(
        rule_id="R1",
        title="Test Field Required",
        description="Test",
        required_fields=["site_address"],
        evidence=EvidenceExpectation(source_types=["all"], keywords=[], min_confidence=0.6),
        rule_category="FIELD_REQUIRED"
    )
    
    context = {}
    
    result = _dispatch_by_category(rule, context)
    
    assert result is None  # Handled by default logic


def test_validate_document_required_missing_context():
    """Test DOCUMENT_REQUIRED validator handles missing context."""
    from planproof.pipeline.validate import _validate_document_required
    from planproof.rules.catalog import Rule, EvidenceExpectation
    
    rule = Rule(
        rule_id="R-DOC-001",
        title="Test",
        description="Test",
        required_fields=["application_form"],
        evidence=EvidenceExpectation(source_types=["all"], keywords=[], min_confidence=0.6),
        rule_category="DOCUMENT_REQUIRED"
    )
    
    context = {}  # Missing submission_id and db
    
    result = _validate_document_required(rule, context)
    
    assert result["status"] == "needs_review"
    assert "missing submission context" in result["message"]


def test_validate_consistency_missing_context():
    """Test CONSISTENCY validator handles missing context."""
    from planproof.pipeline.validate import _validate_consistency
    from planproof.rules.catalog import Rule, EvidenceExpectation
    
    rule = Rule(
        rule_id="R-CONS-001",
        title="Test",
        description="Test",
        required_fields=["postcode"],
        evidence=EvidenceExpectation(source_types=["all"], keywords=[], min_confidence=0.6),
        rule_category="CONSISTENCY"
    )
    
    context = {}
    
    result = _validate_consistency(rule, context)
    
    assert result["status"] == "needs_review"
    assert "missing submission context" in result["message"]


def test_validate_modification_missing_context():
    """Test MODIFICATION validator handles missing context."""
    from planproof.pipeline.validate import _validate_modification
    from planproof.rules.catalog import Rule, EvidenceExpectation
    
    rule = Rule(
        rule_id="R-MOD-001",
        title="Test",
        description="Test",
        required_fields=[],
        evidence=EvidenceExpectation(source_types=["all"], keywords=[], min_confidence=0.6),
        rule_category="MODIFICATION"
    )
    
    context = {}
    
    result = _validate_modification(rule, context)
    
    assert result["status"] == "needs_review"
    assert "missing submission context" in result["message"]


def test_rule_catalog_parser_extracts_category():
    """Test that rule catalog parser extracts rule_category from markdown."""
    from planproof.rules.catalog import _CATEGORY_LINE
    
    # Test category line regex
    line = "Category: DOCUMENT_REQUIRED"
    match = _CATEGORY_LINE.match(line)
    
    assert match is not None
    assert match.group(1) == "DOCUMENT_REQUIRED"


def test_rule_catalog_parser_category_case_insensitive():
    """Test that category parser is case-insensitive."""
    from planproof.rules.catalog import _CATEGORY_LINE
    
    line = "Rule category: consistency"
    match = _CATEGORY_LINE.match(line)
    
    assert match is not None
    assert match.group(1).upper() == "CONSISTENCY"

