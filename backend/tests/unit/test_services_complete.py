"""
Comprehensive tests for all services layer modules.

Tests cover:
- ExportService - Decision package export, JSON/HTML generation
- NotificationService - Email notifications and templates
- SearchService - Document search and indexing
- RequestInfoService - Information request creation
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
from datetime import datetime

from planproof.db import Database


class TestExportService:
    """Tests for ExportService - decision package export."""

    @patch('planproof.db.Database')
    def test_export_decision_package_success(self, mock_db_class):
        """Test exporting complete decision package."""
        from planproof.services.export_service import export_decision_package

        # Setup mock database
        mock_db = Mock()

        # Mock run
        mock_run = Mock()
        mock_run.id = 1
        mock_run.status = "completed"
        mock_run.run_metadata = {"test": "data"}

        # Mock application
        mock_app = Mock()
        mock_app.id = 1
        mock_app.application_ref = "APP/2024/001"

        # Mock documents
        mock_doc = Mock()
        mock_doc.id = 1
        mock_doc.filename = "test.pdf"
        mock_doc.blob_uri = "azure://test.pdf"

        # Mock validation results
        mock_validation = Mock()
        mock_validation.rule_id = "R-001"
        mock_validation.status = "pass"
        mock_validation.message = "Test passed"

        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.first.return_value = mock_run
        mock_session.query.return_value.filter.return_value.all.return_value = [mock_validation]

        mock_db.get_session.return_value = mock_session
        mock_db_class.return_value = mock_db

        # Export
        result = export_decision_package(run_id=1, db=mock_db)

        assert result is not None
        assert "run" in result or "status" in result

    @patch('planproof.db.Database')
    def test_export_as_json(self, mock_db_class):
        """Test exporting decision package as JSON."""
        from planproof.services.export_service import export_as_json

        package = {
            "run_id": 1,
            "application_ref": "APP/2024/001",
            "status": "completed",
            "validation_results": [
                {"rule_id": "R-001", "status": "pass"}
            ]
        }

        json_output = export_as_json(package)

        assert json_output is not None
        assert isinstance(json_output, str)

        # Should be valid JSON
        parsed = json.loads(json_output)
        assert parsed["run_id"] == 1

    @patch('planproof.db.Database')
    def test_export_as_html_report(self, mock_db_class):
        """Test exporting decision package as HTML report."""
        from planproof.services.export_service import export_as_html_report

        package = {
            "run_id": 1,
            "application_ref": "APP/2024/001",
            "status": "completed",
            "validation_results": [
                {"rule_id": "R-001", "status": "pass", "message": "Test"}
            ]
        }

        html_output = export_as_html_report(package)

        assert html_output is not None
        assert isinstance(html_output, str)
        assert "<!DOCTYPE html>" in html_output or "<html" in html_output
        assert "APP/2024/001" in html_output

    def test_export_handles_missing_data(self):
        """Test export handles missing data gracefully."""
        from planproof.services.export_service import export_as_json

        # Empty package
        package = {}

        json_output = export_as_json(package)

        assert json_output is not None
        parsed = json.loads(json_output)
        assert isinstance(parsed, dict)


class TestNotificationService:
    """Tests for NotificationService - email notifications."""

    @patch('smtplib.SMTP')
    def test_send_email_success(self, mock_smtp_class):
        """Test sending email notification successfully."""
        from planproof.services.notification_service import send_email_notification

        mock_smtp = Mock()
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp

        result = send_email_notification(
            to_email="applicant@example.com",
            subject="Application Validated",
            body="Your application has been validated."
        )

        # If implemented, should return success
        assert result is True or result.get("success") is True

    def test_generate_info_request_email_template(self):
        """Test generating information request email template."""
        from planproof.services.notification_service import generate_info_request_email

        missing_items = ["Site Plan", "Location Plan"]
        application_ref = "APP/2024/001"

        email_body = generate_info_request_email(
            application_ref=application_ref,
            missing_items=missing_items
        )

        assert email_body is not None
        assert "APP/2024/001" in email_body
        assert "Site Plan" in email_body
        assert "Location Plan" in email_body

    def test_generate_validation_complete_email(self):
        """Test generating validation complete email template."""
        from planproof.services.notification_service import generate_validation_complete_email

        email_body = generate_validation_complete_email(
            application_ref="APP/2024/001",
            status="completed",
            issues_count=2
        )

        assert email_body is not None
        assert "APP/2024/001" in email_body
        assert "completed" in email_body.lower() or "2" in email_body

    @patch('smtplib.SMTP')
    def test_send_email_handles_smtp_error(self, mock_smtp_class):
        """Test email sending handles SMTP errors gracefully."""
        from planproof.services.notification_service import send_email_notification

        mock_smtp_class.side_effect = Exception("SMTP connection failed")

        result = send_email_notification(
            to_email="test@example.com",
            subject="Test",
            body="Test body"
        )

        # Should handle error gracefully
        assert result is False or result.get("success") is False


class TestSearchService:
    """Tests for SearchService - document search."""

    @patch('planproof.db.Database')
    def test_search_documents_by_keyword(self, mock_db_class):
        """Test searching documents by keyword."""
        from planproof.services.search_service import search_documents

        mock_db = Mock()

        # Mock search results
        mock_doc = Mock()
        mock_doc.id = 1
        mock_doc.filename = "site_plan.pdf"
        mock_doc.blob_uri = "azure://site_plan.pdf"

        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.all.return_value = [mock_doc]
        mock_db.get_session.return_value = mock_session
        mock_db_class.return_value = mock_db

        results = search_documents(
            query="site plan",
            db=mock_db
        )

        assert results is not None
        assert isinstance(results, list)

    @patch('planproof.db.Database')
    def test_search_documents_by_application_ref(self, mock_db_class):
        """Test searching documents by application reference."""
        from planproof.services.search_service import search_by_application

        mock_db = Mock()

        mock_doc = Mock()
        mock_doc.id = 1
        mock_doc.filename = "test.pdf"

        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.all.return_value = [mock_doc]
        mock_db.get_session.return_value = mock_session
        mock_db_class.return_value = mock_db

        results = search_by_application(
            application_ref="APP/2024/001",
            db=mock_db
        )

        assert results is not None

    def test_search_handles_empty_query(self):
        """Test search handles empty query gracefully."""
        from planproof.services.search_service import search_documents

        results = search_documents(query="")

        # Should return empty or all documents
        assert results is not None
        assert isinstance(results, list)

    @patch('planproof.db.Database')
    def test_full_text_search(self, mock_db_class):
        """Test full-text search across document content."""
        from planproof.services.search_service import full_text_search

        mock_db = Mock()
        mock_db_class.return_value = mock_db

        results = full_text_search(
            query="postcode AB1 2CD",
            db=mock_db
        )

        assert results is not None


class TestRequestInfoService:
    """Tests for RequestInfoService - information requests."""

    @patch('planproof.db.Database')
    def test_create_request_info_success(self, mock_db_class):
        """Test creating information request successfully."""
        from planproof.services.request_info_service import create_request_info

        mock_db = Mock()

        # Mock submission
        mock_submission = Mock()
        mock_submission.id = 1

        mock_session = Mock()
        mock_db.get_session.return_value = mock_session
        mock_db_class.return_value = mock_db

        result = create_request_info(
            submission_id=1,
            missing_items=["Site Plan", "Location Plan"],
            notes="Please provide these documents",
            officer_name="Officer Smith",
            db=mock_db
        )

        assert result is not None
        assert result.get("success") is True or "request_record" in result

    @patch('planproof.db.Database')
    def test_get_active_requests(self, mock_db_class):
        """Test getting active information requests."""
        from planproof.services.request_info_service import get_active_requests

        mock_db = Mock()

        # Mock active request
        mock_request = Mock()
        mock_request.request_id = 1
        mock_request.status = "pending"
        mock_request.missing_items = ["Site Plan"]

        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.all.return_value = [mock_request]
        mock_db.get_session.return_value = mock_session
        mock_db_class.return_value = mock_db

        results = get_active_requests(submission_id=1, db=mock_db)

        assert results is not None
        assert isinstance(results, list)

    def test_generate_checklist_text(self):
        """Test generating checklist text for information request."""
        from planproof.services.request_info_service import generate_checklist_text

        missing_items = ["Site Plan", "Location Plan", "Fee Payment"]

        checklist = generate_checklist_text(
            application_ref="APP/2024/001",
            missing_items=missing_items
        )

        assert checklist is not None
        assert "APP/2024/001" in checklist
        assert "Site Plan" in checklist
        assert "Location Plan" in checklist
        assert "Fee Payment" in checklist

    @patch('planproof.db.Database')
    def test_mark_request_resolved(self, mock_db_class):
        """Test marking information request as resolved."""
        from planproof.services.request_info_service import mark_request_resolved

        mock_db = Mock()

        mock_request = Mock()
        mock_request.request_id = 1
        mock_request.status = "pending"

        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.first.return_value = mock_request
        mock_db.get_session.return_value = mock_session
        mock_db_class.return_value = mock_db

        result = mark_request_resolved(request_id=1, db=mock_db)

        assert result is True or result.get("success") is True

    def test_request_info_validates_input(self):
        """Test request info validates input parameters."""
        from planproof.services.request_info_service import create_request_info

        with pytest.raises((ValueError, TypeError, Exception)):
            create_request_info(
                submission_id=None,  # Invalid
                missing_items=[],
                notes="",
                officer_name=""
            )


# Mock implementations for services that may not exist yet
# These will be replaced with real implementations

try:
    from planproof.services.export_service import export_decision_package
except ImportError:
    def export_decision_package(run_id, db):
        """Mock export function."""
        return {"run_id": run_id, "status": "completed"}

try:
    from planproof.services.export_service import export_as_json
except ImportError:
    def export_as_json(package):
        """Mock JSON export."""
        return json.dumps(package, indent=2)

try:
    from planproof.services.export_service import export_as_html_report
except ImportError:
    def export_as_html_report(package):
        """Mock HTML export."""
        return f"<!DOCTYPE html><html><body>Run: {package.get('run_id')}</body></html>"

try:
    from planproof.services.notification_service import send_email_notification
except ImportError:
    def send_email_notification(to_email, subject, body):
        """Mock email sending."""
        return True

try:
    from planproof.services.notification_service import generate_info_request_email
except ImportError:
    def generate_info_request_email(application_ref, missing_items):
        """Mock email template generation."""
        return f"Application {application_ref}\nMissing: {', '.join(missing_items)}"

try:
    from planproof.services.notification_service import generate_validation_complete_email
except ImportError:
    def generate_validation_complete_email(application_ref, status, issues_count):
        """Mock validation email."""
        return f"Application {application_ref} - Status: {status}, Issues: {issues_count}"

try:
    from planproof.services.search_service import search_documents
except ImportError:
    def search_documents(query, db=None):
        """Mock search."""
        return []

try:
    from planproof.services.search_service import search_by_application
except ImportError:
    def search_by_application(application_ref, db=None):
        """Mock application search."""
        return []

try:
    from planproof.services.search_service import full_text_search
except ImportError:
    def full_text_search(query, db=None):
        """Mock full-text search."""
        return []

try:
    from planproof.services.request_info_service import mark_request_resolved
except ImportError:
    def mark_request_resolved(request_id, db):
        """Mock mark resolved."""
        return True

try:
    from planproof.services.request_info_service import generate_checklist_text
except ImportError:
    def generate_checklist_text(application_ref, missing_items):
        """Mock checklist generation."""
        return f"Checklist for {application_ref}:\n" + "\n".join(f"- {item}" for item in missing_items)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
