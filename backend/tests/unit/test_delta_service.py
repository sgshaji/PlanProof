"""
Unit tests for delta computation service.
"""

import pytest
from unittest.mock import Mock, patch


def test_calculate_significance_no_changes():
    """Test significance calculation with no changes."""
    from planproof.services.delta_service import calculate_significance
    
    result = calculate_significance([])
    assert result == 0.0


def test_calculate_significance_high_impact_field():
    """Test significance calculation with high-impact field change."""
    from planproof.services.delta_service import calculate_significance
    
    changes = [
        {
            "change_type": "field_delta",
            "field_key": "site_address",
            "old_value": "123 Old St",
            "new_value": "456 New St",
            "metadata": {"action": "modified"}
        }
    ]
    
    result = calculate_significance(changes)
    assert result == 0.9  # High-impact field


def test_calculate_significance_medium_impact_field():
    """Test significance calculation with medium-impact field change."""
    from planproof.services.delta_service import calculate_significance
    
    changes = [
        {
            "change_type": "field_delta",
            "field_key": "postcode",
            "old_value": "B8 1AA",
            "new_value": "B8 1BB",
            "metadata": {"action": "modified"}
        }
    ]
    
    result = calculate_significance(changes)
    assert result == 0.5  # Medium-impact field


def test_calculate_significance_low_impact_field():
    """Test significance calculation with low-impact field change."""
    from planproof.services.delta_service import calculate_significance
    
    changes = [
        {
            "change_type": "field_delta",
            "field_key": "some_minor_field",
            "old_value": "old",
            "new_value": "new",
            "metadata": {"action": "modified"}
        }
    ]
    
    result = calculate_significance(changes)
    assert result == 0.2  # Low-impact field


def test_calculate_significance_document_replaced():
    """Test significance calculation with document replacement."""
    from planproof.services.delta_service import calculate_significance
    
    changes = [
        {
            "change_type": "document_delta",
            "document_type": "site_plan",
            "old_value": "old_plan.pdf",
            "new_value": "new_plan.pdf",
            "metadata": {"action": "replaced"}
        }
    ]
    
    result = calculate_significance(changes)
    assert result == 0.6  # Document replacement


def test_calculate_significance_document_added():
    """Test significance calculation with document addition."""
    from planproof.services.delta_service import calculate_significance
    
    changes = [
        {
            "change_type": "document_delta",
            "document_type": "elevation",
            "old_value": None,
            "new_value": "new_elevation.pdf",
            "metadata": {"action": "added"}
        }
    ]
    
    result = calculate_significance(changes)
    assert result == 0.4  # Document addition


def test_calculate_significance_spatial_metric():
    """Test significance calculation with spatial metric change."""
    from planproof.services.delta_service import calculate_significance
    
    changes = [
        {
            "change_type": "spatial_metric_delta",
            "field_key": "site_boundary_area",
            "old_value": "100.5",
            "new_value": "105.2",
            "metadata": {"action": "modified"}
        }
    ]
    
    result = calculate_significance(changes)
    assert result == 0.7  # Spatial change


def test_calculate_significance_multiple_changes():
    """Test significance calculation with multiple changes (returns max)."""
    from planproof.services.delta_service import calculate_significance
    
    changes = [
        {
            "change_type": "field_delta",
            "field_key": "some_minor_field",
            "old_value": "old",
            "new_value": "new",
            "metadata": {"action": "modified"}
        },
        {
            "change_type": "field_delta",
            "field_key": "proposed_use",
            "old_value": "Residential",
            "new_value": "Commercial",
            "metadata": {"action": "modified"}
        }
    ]
    
    result = calculate_significance(changes)
    assert result == 0.9  # Max of 0.2 and 0.9


@patch('planproof.services.delta_service.Database')
def test_compute_changeset_validates_submissions(mock_db_class):
    """Test that compute_changeset validates submission existence."""
    from planproof.services.delta_service import compute_changeset
    
    # Mock database
    mock_db = Mock()
    mock_session = Mock()
    mock_session.query.return_value.filter.return_value.first.return_value = None
    mock_db.get_session.return_value = mock_session
    mock_db_class.return_value = mock_db
    
    with pytest.raises(ValueError, match="Submissions not found"):
        compute_changeset(1, 2, db=mock_db)

