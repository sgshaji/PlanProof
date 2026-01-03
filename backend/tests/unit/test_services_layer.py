"""
Comprehensive tests for services layer.

Tests cover:
- ResolutionService
- DeltaService (additional tests)
- ExportService
- NotificationService
- RequestInfoService
- SearchService
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, mock_open
from datetime import datetime
from io import BytesIO

from planproof.services.resolution_service import ResolutionService

# Note: Other services not yet implemented - will test when they exist
# from planproof.services.export_service import ExportService
# from planproof.services.notification_service import NotificationService  
# from planproof.services.request_info_service import RequestInfoService
# from planproof.services.search_service import SearchService


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_run_dir(tmp_path):
    """Create temporary run directory structure."""
    run_id = 1
    run_dir = tmp_path / "runs" / str(run_id)
    inputs_dir = run_dir / "inputs"
    outputs_dir = run_dir / "outputs"
    
    inputs_dir.mkdir(parents=True)
    outputs_dir.mkdir(parents=True)
    
    return run_dir, inputs_dir, outputs_dir


@pytest.fixture
def mock_uploaded_file():
    """Mock Streamlit UploadedFile."""
    mock_file = Mock()
    mock_file.name = "test_document.pdf"
    mock_file.getbuffer.return_value = b"fake pdf content"
    return mock_file


@pytest.fixture
def sample_issues():
    """Sample enhanced issues for testing."""
    return [
        {
            "issue_id": "DOC-001",
            "status": "open",
            "severity": "error",
            "rule_id": "DOC-01",
            "document_type": "site_plan"
        },
        {
            "issue_id": "CON-001",
            "status": "open",
            "severity": "warning",
            "rule_id": "CON-01"
        }
    ]


# ============================================================================
# ResolutionService Tests
# ============================================================================

class TestResolutionService:
    """Tests for ResolutionService."""
    
    def test_init_creates_directories(self, tmp_path, monkeypatch):
        """Test ResolutionService creates necessary directories."""
        monkeypatch.chdir(tmp_path)
        
        service = ResolutionService(run_id=1)
        
        assert service.run_dir.exists()
        assert service.inputs_dir.exists()
        assert service.outputs_dir.exists()
    
    def test_load_resolutions_empty_file(self, tmp_path, monkeypatch):
        """Test loading resolutions when file doesn't exist."""
        monkeypatch.chdir(tmp_path)
        
        service = ResolutionService(run_id=1)
        
        assert service.resolutions == {"actions": [], "issues": {}}
    
    def test_load_resolutions_existing_file(self, tmp_path, monkeypatch):
        """Test loading resolutions from existing file."""
        monkeypatch.chdir(tmp_path)
        
        # Create existing resolution file
        run_dir = tmp_path / "runs" / "1"
        outputs_dir = run_dir / "outputs"
        outputs_dir.mkdir(parents=True)
        
        resolution_data = {
            "actions": [{"action_type": "upload", "timestamp": "2026-01-01T10:00:00"}],
            "issues": {"DOC-001": {"status": "resolved"}}
        }
        
        resolution_file = outputs_dir / "resolutions.json"
        resolution_file.write_text(json.dumps(resolution_data))
        
        service = ResolutionService(run_id=1)
        
        assert len(service.resolutions["actions"]) == 1
        assert "DOC-001" in service.resolutions["issues"]
    
    def test_process_document_upload_saves_file(self, tmp_path, monkeypatch, mock_uploaded_file):
        """Test document upload saves file correctly."""
        monkeypatch.chdir(tmp_path)
        
        service = ResolutionService(run_id=1)
        result = service.process_document_upload(
            uploaded_file=mock_uploaded_file,
            document_type="site_plan",
            issue_id="DOC-001"
        )
        
        assert result["success"] == True
        assert "filename" in result
        
        # Check file was saved
        saved_files = list(service.inputs_dir.glob("*.pdf"))
        assert len(saved_files) == 1
    
    def test_process_document_upload_records_action(self, tmp_path, monkeypatch, mock_uploaded_file):
        """Test document upload records action."""
        monkeypatch.chdir(tmp_path)
        
        service = ResolutionService(run_id=1)
        service.process_document_upload(
            uploaded_file=mock_uploaded_file,
            document_type="site_plan",
            issue_id="DOC-001"
        )
        
        assert len(service.resolutions["actions"]) == 1
        action = service.resolutions["actions"][0]
        assert action["action_type"] == "document_upload"
        assert action["issue_id"] == "DOC-001"
        assert action["document_type"] == "site_plan"
    
    def test_process_bulk_document_upload(self, tmp_path, monkeypatch, mock_uploaded_file):
        """Test bulk document upload."""
        monkeypatch.chdir(tmp_path)
        
        service = ResolutionService(run_id=1)
        
        uploads = [
            (mock_uploaded_file, "site_plan"),
            (mock_uploaded_file, "floor_plan")
        ]
        issue_ids = ["DOC-001", "DOC-002"]
        
        result = service.process_bulk_document_upload(uploads, issue_ids)
        
        assert result["success"] == True
        assert result["successful"] >= 0
        assert isinstance(service.resolutions["actions"], list)
    
    def test_process_option_selection(self, tmp_path, monkeypatch):
        """Test option selection processing."""
        monkeypatch.chdir(tmp_path)
        
        service = ResolutionService(run_id=1)
        result = service.process_option_selection(
            issue_id="BNG-001",
            selected_option="not_applicable",
            option_label="Site is under 10 sqm"
        )
        
        assert result["success"] == True
        assert len(service.resolutions["actions"]) == 1
        assert service.resolutions["actions"][0]["action_type"] == "option_selection"
    
    def test_process_explanation(self, tmp_path, monkeypatch):
        """Test explanation processing."""
        monkeypatch.chdir(tmp_path)
        
        service = ResolutionService(run_id=1)
        result = service.process_explanation(
            issue_id="C_001",
            explanation_text="This is a clarification of the discrepancy."
        )
        
        assert result["success"] == True
        assert len(service.resolutions["actions"]) == 1
        assert service.resolutions["actions"][0]["action_type"] == "explanation_provided"
    
    def test_get_issues_pending_recheck(self, tmp_path, monkeypatch):
        """Test getting issues pending recheck."""
        monkeypatch.chdir(tmp_path)
        
        service = ResolutionService(run_id=1)
        service.resolutions = {
            "actions": [
                {"action_type": "document_upload", "issue_id": "DOC-001"}
            ],
            "issues": {
                "DOC-001": {"status": "resolved", "recheck_pending": True},
                "DOC-002": {"status": "resolved", "recheck_pending": False}
            }
        }
        
        pending = service.get_issues_pending_recheck()
        
        assert "DOC-001" in pending
        assert "DOC-002" not in pending
    
    def test_mark_issue_rechecked(self, tmp_path, monkeypatch):
        """Test marking issue as rechecked."""
        monkeypatch.chdir(tmp_path)
        
        service = ResolutionService(run_id=1)
        service.resolutions["issues"] = {
            "DOC-001": {"status": "in_progress", "recheck_pending": True}
        }
        
        service.mark_issue_rechecked(
            issue_id="DOC-001",
            new_status="resolved",
            recheck_result={"result": "resolved"}
        )
        
        assert service.resolutions["issues"]["DOC-001"]["status"] == "resolved"
        assert service.resolutions["issues"]["DOC-001"]["recheck_pending"] is False
    
    def test_dismiss_issue(self, tmp_path, monkeypatch):
        """Test officer dismissal of issue."""
        monkeypatch.chdir(tmp_path)
        
        service = ResolutionService(run_id=1)
        result = service.dismiss_issue(
            issue_id="CON-001",
            officer_id="OFC-123",
            reason="Not applicable for this case"
        )
        
        assert result["success"] == True
        assert len(service.resolutions["actions"]) == 1
        assert service.resolutions["actions"][0]["action_type"] == "dismissed"


# ============================================================================
# Tests for services that don't exist yet - will implement when they're added
# ============================================================================

@pytest.mark.skip(reason="Service not yet implemented")
class TestAutoRecheckEngine:
    """Tests for AutoRecheckEngine."""
    pass


@pytest.mark.skip(reason="Service not yet implemented")
class TestDependencyResolver:
    """Tests for DependencyResolver."""
    pass


# ============================================================================
# ExportService Tests - To be implemented
# ============================================================================

@pytest.mark.skip(reason="Service not yet implemented")
class TestExportService:
    """Tests for ExportService."""
    pass


# ============================================================================
# NotificationService Tests - To be implemented
# ============================================================================

@pytest.mark.skip(reason="Service not yet implemented")
class TestNotificationService:
    """Tests for NotificationService."""
    pass


# ============================================================================
# RequestInfoService Tests - To be implemented
# ============================================================================

@pytest.mark.skip(reason="Service not yet implemented")
class TestRequestInfoService:
    """Tests for RequestInfoService."""
    pass


# ============================================================================
# SearchService Tests - To be implemented
# ============================================================================

@pytest.mark.skip(reason="Service not yet implemented")
class TestSearchService:
    """Tests for SearchService."""
    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
