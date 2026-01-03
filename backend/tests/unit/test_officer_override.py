"""
Unit tests for officer override service.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch


def test_create_override_validates_notes():
    """Test that empty notes are rejected."""
    from planproof.services.officer_override import create_override
    
    with pytest.raises(ValueError, match="Notes are mandatory"):
        create_override(
            validation_result_id=1,
            validation_check_id=None,
            original_status="fail",
            override_status="pass",
            notes="",
            officer_id="officer123"
        )


def test_create_override_validates_status():
    """Test that invalid status values are rejected."""
    from planproof.services.officer_override import create_override
    
    with pytest.raises(ValueError, match="Invalid override_status"):
        create_override(
            validation_result_id=1,
            validation_check_id=None,
            original_status="fail",
            override_status="invalid_status",
            notes="Test notes",
            officer_id="officer123"
        )


def test_create_override_requires_validation_id():
    """Test that at least one validation ID is required."""
    from planproof.services.officer_override import create_override
    
    with pytest.raises(ValueError, match="Either validation_result_id or validation_check_id"):
        create_override(
            validation_result_id=None,
            validation_check_id=None,
            original_status="fail",
            override_status="pass",
            notes="Test notes",
            officer_id="officer123"
        )


def test_get_override_history_empty():
    """Test getting override history with no IDs returns empty list."""
    from planproof.services.officer_override import get_override_history
    
    result = get_override_history()
    assert result == []


@patch('planproof.services.officer_override.Database')
def test_create_override_success(mock_db_class):
    """Test successful override creation."""
    from planproof.services.officer_override import create_override
    
    # Mock database
    mock_db = Mock()
    mock_session = Mock()
    mock_override = Mock()
    mock_override.override_id = 123
    
    mock_session.add = Mock()
    mock_session.commit = Mock()
    mock_session.refresh = Mock()
    mock_session.close = Mock()
    
    mock_db.get_session.return_value = mock_session
    mock_db_class.return_value = mock_db
    
    # Mock OfficerOverride constructor
    with patch('planproof.services.officer_override.OfficerOverride', return_value=mock_override):
        override_id = create_override(
            validation_result_id=1,
            validation_check_id=None,
            original_status="fail",
            override_status="pass",
            notes="Test override notes",
            officer_id="officer123",
            db=mock_db
        )
        
        assert override_id == 123
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

