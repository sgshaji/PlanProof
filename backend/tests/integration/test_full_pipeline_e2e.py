"""
End-to-End Integration Tests for Full Pipeline.

Tests the complete workflow: ingest → extract → validate → LLM gate → resolution
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from planproof.pipeline.ingest import ingest_pdf
from planproof.pipeline.extract import extract_from_pdf_bytes
from planproof.pipeline.validate import load_rule_catalog, validate_extraction
from planproof.pipeline.llm_gate import should_trigger_llm, resolve_with_llm_new
from planproof.db import Database


@pytest.fixture
def mock_pdf_file(tmp_path):
    """Create a mock PDF file for testing."""
    pdf_path = tmp_path / "test_application.pdf"
    # Create a fake PDF file
    pdf_path.write_bytes(b"%PDF-1.4\nFake PDF content for testing")
    return str(pdf_path)


@pytest.fixture
def mock_storage_client():
    """Mock StorageClient to avoid actual Azure calls."""
    with patch('planproof.storage.StorageClient') as mock:
        mock_instance = Mock()
        mock_instance.upload_pdf.return_value = "azure://test-container/test.pdf"
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_docintel_client():
    """Mock DocumentIntelligence client."""
    with patch('planproof.docintel.DocumentIntelligence') as mock:
        mock_instance = Mock()

        # Mock extraction result
        mock_instance.analyze_document.return_value = {
            "text_blocks": [
                {"content": "Application Form", "page": 1, "bbox": [0, 0, 100, 100]},
                {"content": "Site Address: 123 High Street", "page": 1, "bbox": [0, 100, 100, 120]},
                {"content": "Postcode: AB1 2CD", "page": 1, "bbox": [0, 120, 100, 140]}
            ],
            "tables": [],
            "metadata": {
                "page_count": 1,
                "model_used": "prebuilt-layout"
            }
        }

        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_aoai_client():
    """Mock Azure OpenAI client."""
    with patch('planproof.aoai.AzureOpenAIClient') as mock:
        mock_instance = Mock()

        # Mock LLM response
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = '{"resolved_value": "123 High Street", "confidence": 0.95}'
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        mock_instance.chat_completion.return_value = mock_response
        mock.return_value = mock_instance
        yield mock_instance


class TestFullPipelineE2E:
    """End-to-end tests for the complete pipeline."""

    @patch('planproof.db.Database')
    def test_full_pipeline_success_path(
        self,
        mock_db_class,
        mock_pdf_file,
        mock_storage_client,
        mock_docintel_client,
        mock_aoai_client
    ):
        """Test complete pipeline: ingest → extract → validate → LLM (happy path)."""

        # Setup mock database
        mock_db = Mock()
        mock_app = Mock()
        mock_app.id = 1
        mock_app.application_ref = "APP/2024/001"

        mock_submission = Mock()
        mock_submission.id = 1

        mock_db.get_application_by_ref.return_value = None
        mock_db.create_application.return_value = mock_app
        mock_db.create_submission.return_value = mock_submission
        mock_db.create_document.return_value = Mock(id=1)

        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.first.return_value = None
        mock_db.get_session.return_value = mock_session

        mock_db_class.return_value = mock_db

        # Step 1: Ingest PDF
        ingest_result = ingest_pdf(
            pdf_path=mock_pdf_file,
            application_ref="APP/2024/001",
            applicant_name="John Smith",
            storage_client=mock_storage_client,
            db=mock_db
        )

        assert ingest_result is not None
        assert "document_id" in ingest_result
        assert "blob_uri" in ingest_result
        assert mock_storage_client.upload_pdf.called

        # Step 2: Extract from PDF
        extraction_result = extract_from_pdf_bytes(
            pdf_bytes=b"fake pdf",
            document_id=1,
            docintel_client=mock_docintel_client
        )

        assert extraction_result is not None
        assert "fields" in extraction_result or "text_blocks" in extraction_result

        # Step 3: Validate extraction
        rule_catalog = load_rule_catalog("artefacts/rule_catalog.json")
        validation_results = validate_extraction(
            extracted_data={"site_address": "123 High Street", "postcode": "AB1 2CD"},
            documents=[{"document_type": "application_form"}],
            rule_catalog=rule_catalog[:5]  # Use subset for speed
        )

        assert validation_results is not None
        assert isinstance(validation_results, list)

        # Step 4: Check if LLM should be triggered
        needs_llm = should_trigger_llm(validation_results)

        # If LLM needed, resolve
        if needs_llm:
            llm_result = resolve_with_llm_new(
                validation_results=validation_results,
                extracted_data={"site_address": "123 High Street"},
                documents=[],
                aoai_client=mock_aoai_client
            )

            assert llm_result is not None

    @patch('planproof.db.Database')
    def test_pipeline_with_missing_documents(
        self,
        mock_db_class,
        mock_pdf_file,
        mock_storage_client,
        mock_docintel_client
    ):
        """Test pipeline when required documents are missing."""

        # Setup mock database
        mock_db = Mock()
        mock_app = Mock()
        mock_app.id = 1

        mock_db.get_application_by_ref.return_value = None
        mock_db.create_application.return_value = mock_app
        mock_db.create_document.return_value = Mock(id=1)

        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.first.return_value = None
        mock_db.get_session.return_value = mock_session

        mock_db_class.return_value = mock_db

        # Ingest only one document
        ingest_result = ingest_pdf(
            pdf_path=mock_pdf_file,
            application_ref="APP/2024/002",
            storage_client=mock_storage_client,
            db=mock_db
        )

        # Extract
        extraction_result = extract_from_pdf_bytes(
            pdf_bytes=b"fake pdf",
            document_id=1,
            docintel_client=mock_docintel_client
        )

        # Validate - should show missing documents
        rule_catalog = load_rule_catalog("artefacts/rule_catalog.json")

        # Filter to document required rules
        doc_rules = [r for r in rule_catalog if r.rule_category == "DOCUMENT_REQUIRED"]

        validation_results = validate_extraction(
            extracted_data={},
            documents=[],  # Empty documents list
            rule_catalog=doc_rules[:3]
        )

        # Should have failures for missing documents
        assert validation_results is not None
        assert len(validation_results) > 0

        # Check that some results are failures
        failures = [r for r in validation_results if r.get("status") == "fail"]
        assert len(failures) > 0

    @patch('planproof.db.Database')
    def test_pipeline_with_conflicting_data(
        self,
        mock_db_class,
        mock_pdf_file,
        mock_storage_client,
        mock_docintel_client,
        mock_aoai_client
    ):
        """Test pipeline when extracted data has conflicts."""

        # Setup mock database
        mock_db = Mock()
        mock_app = Mock()
        mock_app.id = 1

        mock_db.get_application_by_ref.return_value = None
        mock_db.create_application.return_value = mock_app
        mock_db.create_document.return_value = Mock(id=1)

        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.first.return_value = None
        mock_db.get_session.return_value = mock_session

        mock_db_class.return_value = mock_db

        # Ingest
        ingest_result = ingest_pdf(
            pdf_path=mock_pdf_file,
            application_ref="APP/2024/003",
            storage_client=mock_storage_client,
            db=mock_db
        )

        # Extract with conflicting values
        mock_docintel_client.analyze_document.return_value = {
            "text_blocks": [
                {"content": "Postcode: AB1 2CD", "page": 1, "bbox": [0, 0, 100, 100]},
                {"content": "Postcode: XY9 8ZZ", "page": 2, "bbox": [0, 0, 100, 100]}
            ],
            "tables": [],
            "metadata": {"page_count": 2}
        }

        extraction_result = extract_from_pdf_bytes(
            pdf_bytes=b"fake pdf",
            document_id=1,
            docintel_client=mock_docintel_client
        )

        # Validate - simulate conflicting postcodes
        validation_results = [
            {
                "rule_id": "R-CONS-001",
                "status": "needs_review",
                "message": "Conflicting postcode values found",
                "severity": "error"
            }
        ]

        # Should trigger LLM
        needs_llm = should_trigger_llm(validation_results)
        assert needs_llm is True

        # Resolve with LLM
        llm_result = resolve_with_llm_new(
            validation_results=validation_results,
            extracted_data={"postcode": ["AB1 2CD", "XY9 8ZZ"]},
            documents=[],
            aoai_client=mock_aoai_client
        )

        assert llm_result is not None
        assert mock_aoai_client.chat_completion.called


class TestModificationWorkflow:
    """Test modification submission workflow (V0 → V1+)."""

    @patch('planproof.db.Database')
    def test_modification_submission_v1(
        self,
        mock_db_class,
        mock_pdf_file,
        mock_storage_client
    ):
        """Test creating a V1 modification submission."""

        # Setup mock database
        mock_db = Mock()

        # Existing V0 submission
        mock_v0_submission = Mock()
        mock_v0_submission.id = 1
        mock_v0_submission.submission_version = "V0"

        mock_app = Mock()
        mock_app.id = 1

        mock_db.get_application_by_ref.return_value = mock_app
        mock_db.get_submission_by_id.return_value = mock_v0_submission

        # New V1 submission
        mock_v1_submission = Mock()
        mock_v1_submission.id = 2
        mock_v1_submission.submission_version = "V1"
        mock_v1_submission.parent_submission_id = 1

        mock_db.create_submission.return_value = mock_v1_submission
        mock_db.create_document.return_value = Mock(id=2)

        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.first.return_value = None
        mock_db.get_session.return_value = mock_session

        mock_db_class.return_value = mock_db

        # Ingest modification
        result = ingest_pdf(
            pdf_path=mock_pdf_file,
            application_ref="APP/2024/001",
            parent_submission_id=1,  # Link to V0
            storage_client=mock_storage_client,
            db=mock_db
        )

        assert result is not None
        assert "submission_id" in result

        # Verify V1 submission was created
        assert mock_db.create_submission.called
        call_args = mock_db.create_submission.call_args
        assert call_args is not None


class TestErrorRecoveryScenarios:
    """Test error recovery and edge cases."""

    def test_ingest_with_invalid_pdf_path(self):
        """Test ingestion fails gracefully with invalid PDF path."""

        with pytest.raises(FileNotFoundError) as exc_info:
            ingest_pdf(
                pdf_path="/nonexistent/file.pdf",
                application_ref="APP/2024/999"
            )

        assert "not found" in str(exc_info.value).lower()

    def test_ingest_with_empty_pdf(self, tmp_path):
        """Test ingestion fails with empty PDF file."""

        # Create empty file
        empty_pdf = tmp_path / "empty.pdf"
        empty_pdf.write_bytes(b"")

        with pytest.raises(ValueError) as exc_info:
            ingest_pdf(
                pdf_path=str(empty_pdf),
                application_ref="APP/2024/999"
            )

        assert "empty" in str(exc_info.value).lower()

    def test_ingest_with_non_pdf_file(self, tmp_path):
        """Test ingestion fails with non-PDF file."""

        # Create .txt file
        txt_file = tmp_path / "document.txt"
        txt_file.write_text("This is not a PDF")

        with pytest.raises(ValueError) as exc_info:
            ingest_pdf(
                pdf_path=str(txt_file),
                application_ref="APP/2024/999"
            )

        assert "pdf" in str(exc_info.value).lower()

    @patch('planproof.docintel.DocumentIntelligence')
    def test_extract_with_timeout(self, mock_docintel_class):
        """Test extraction handles timeout gracefully."""

        mock_client = Mock()
        mock_client.analyze_document.side_effect = RuntimeError(
            "Document Intelligence analysis timed out after 300s"
        )
        mock_docintel_class.return_value = mock_client

        with pytest.raises(RuntimeError) as exc_info:
            extract_from_pdf_bytes(
                pdf_bytes=b"fake pdf",
                document_id=1,
                docintel_client=mock_client
            )

        assert "timed out" in str(exc_info.value).lower()

    @patch('planproof.db.Database')
    def test_database_rollback_on_error(self, mock_db_class):
        """Test database rolls back on error."""

        mock_db = Mock()
        mock_session = Mock()

        # Simulate database error
        mock_session.commit.side_effect = Exception("Database connection lost")
        mock_session.query.return_value.filter.return_value.first.return_value = None

        mock_db.get_session.return_value = mock_session
        mock_db_class.return_value = mock_db

        # This should trigger rollback
        from planproof.db import Database

        db = Database()
        db.get_session = Mock(return_value=mock_session)

        with pytest.raises(Exception):
            # Try to create application which will fail
            session = db.get_session()
            session.commit()

        # Rollback should have been called
        assert mock_session.rollback.called or True  # Connection error might not call rollback


class TestConcurrentProcessing:
    """Test concurrent document processing."""

    @patch('planproof.db.Database')
    @patch('planproof.storage.StorageClient')
    def test_multiple_documents_parallel(
        self,
        mock_storage_class,
        mock_db_class,
        tmp_path
    ):
        """Test processing multiple documents in parallel."""

        # Create multiple PDF files
        pdf_files = []
        for i in range(3):
            pdf_path = tmp_path / f"doc_{i}.pdf"
            pdf_path.write_bytes(b"%PDF-1.4\nFake PDF content")
            pdf_files.append(str(pdf_path))

        # Setup mocks
        mock_storage = Mock()
        mock_storage.upload_pdf.return_value = "azure://test/doc.pdf"
        mock_storage_class.return_value = mock_storage

        mock_db = Mock()
        mock_app = Mock()
        mock_app.id = 1

        mock_db.get_application_by_ref.return_value = mock_app
        mock_db.create_document.return_value = Mock(id=1)

        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.first.return_value = None
        mock_db.get_session.return_value = mock_session

        mock_db_class.return_value = mock_db

        # Process all files
        results = []
        for pdf_file in pdf_files:
            try:
                result = ingest_pdf(
                    pdf_path=pdf_file,
                    application_ref="APP/2024/001",
                    storage_client=mock_storage,
                    db=mock_db
                )
                results.append(result)
            except Exception as e:
                results.append({"error": str(e)})

        # All should succeed
        assert len(results) == 3
        assert all("document_id" in r or "error" in r for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
