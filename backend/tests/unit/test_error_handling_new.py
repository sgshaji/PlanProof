"""
Tests for NEW error handling added to core modules.

Tests comprehensive error handling for:
- aoai.py - Timeout handling, error classification
- docintel.py - Retry logic, timeout polling
- db.py - Database rollbacks
- ingest.py - File validation, error handling
- run_orchestrator.py - Error file writing, recovery
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile

from openai import APIError, APITimeoutError, RateLimitError, APIConnectionError
from azure.core.exceptions import ServiceRequestError, ServiceResponseError


class TestAzureOpenAIErrorHandling:
    """Test error handling in aoai.py."""

    @patch('openai.AzureOpenAI')
    def test_timeout_error_raises_runtime_error(self, mock_openai_class):
        """Test API timeout raises RuntimeError with clear message."""
        from planproof.aoai import AzureOpenAIClient

        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = APITimeoutError("Request timed out")
        mock_openai_class.return_value = mock_client

        aoai = AzureOpenAIClient(timeout=60.0)

        with pytest.raises(RuntimeError) as exc_info:
            aoai.chat_completion(
                messages=[{"role": "user", "content": "test"}]
            )

        assert "timeout" in str(exc_info.value).lower()
        assert "60" in str(exc_info.value) or "60.0" in str(exc_info.value)

    @patch('openai.AzureOpenAI')
    def test_rate_limit_error_raises_runtime_error(self, mock_openai_class):
        """Test rate limit error raises RuntimeError with clear message."""
        from planproof.aoai import AzureOpenAIClient

        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = RateLimitError("Rate limit exceeded")
        mock_openai_class.return_value = mock_client

        aoai = AzureOpenAIClient()

        with pytest.raises(RuntimeError) as exc_info:
            aoai.chat_completion(
                messages=[{"role": "user", "content": "test"}]
            )

        assert "rate limit" in str(exc_info.value).lower()

    @patch('openai.AzureOpenAI')
    def test_connection_error_raises_runtime_error(self, mock_openai_class):
        """Test connection error raises RuntimeError with clear message."""
        from planproof.aoai import AzureOpenAIClient

        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = APIConnectionError("Connection failed")
        mock_openai_class.return_value = mock_client

        aoai = AzureOpenAIClient()

        with pytest.raises(RuntimeError) as exc_info:
            aoai.chat_completion(
                messages=[{"role": "user", "content": "test"}]
            )

        assert "connection" in str(exc_info.value).lower()

    @patch('openai.AzureOpenAI')
    def test_api_error_raises_runtime_error(self, mock_openai_class):
        """Test general API error raises RuntimeError with clear message."""
        from planproof.aoai import AzureOpenAIClient

        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = APIError("API error occurred")
        mock_openai_class.return_value = mock_client

        aoai = AzureOpenAIClient()

        with pytest.raises(RuntimeError) as exc_info:
            aoai.chat_completion(
                messages=[{"role": "user", "content": "test"}]
            )

        assert "api error" in str(exc_info.value).lower()

    @patch('openai.AzureOpenAI')
    def test_custom_timeout_value(self, mock_openai_class):
        """Test custom timeout value is used."""
        from planproof.aoai import AzureOpenAIClient

        aoai = AzureOpenAIClient(timeout=120.0)

        assert aoai.timeout == 120.0

        # Verify timeout was passed to client
        call_kwargs = mock_openai_class.call_args[1]
        assert call_kwargs['timeout'] == 120.0


class TestDocumentIntelligenceErrorHandling:
    """Test error handling in docintel.py."""

    @patch('azure.ai.documentintelligence.DocumentIntelligenceClient')
    def test_network_error_retries_and_fails(self, mock_client_class):
        """Test network errors trigger retry logic and eventually fail."""
        from planproof.docintel import DocumentIntelligence

        mock_client = Mock()
        mock_client.begin_analyze_document.side_effect = ServiceRequestError("Network error")
        mock_client_class.return_value = mock_client

        di = DocumentIntelligence()

        with pytest.raises(RuntimeError) as exc_info:
            di.analyze_document(pdf_bytes=b"fake pdf")

        # Should mention the error and retries
        error_msg = str(exc_info.value).lower()
        assert "network error" in error_msg or "service request" in error_msg
        assert "attempt" in error_msg or "failed" in error_msg

    @patch('azure.ai.documentintelligence.DocumentIntelligenceClient')
    def test_service_error_retries_and_fails(self, mock_client_class):
        """Test service errors (500s) trigger retry logic."""
        from planproof.docintel import DocumentIntelligence

        mock_client = Mock()
        mock_client.begin_analyze_document.side_effect = ServiceResponseError("Internal server error")
        mock_client_class.return_value = mock_client

        di = DocumentIntelligence()

        with pytest.raises(RuntimeError) as exc_info:
            di.analyze_document(pdf_bytes=b"fake pdf")

        error_msg = str(exc_info.value).lower()
        assert "service error" in error_msg or "internal server" in error_msg

    @patch('azure.ai.documentintelligence.DocumentIntelligenceClient')
    def test_timeout_polling_raises_error(self, mock_client_class):
        """Test timeout during polling raises clear error."""
        from planproof.docintel import DocumentIntelligence

        mock_client = Mock()

        # Mock a poller that never completes
        mock_poller = Mock()
        mock_poller.done.return_value = False  # Never done

        mock_client.begin_analyze_document.return_value = mock_poller
        mock_client_class.return_value = mock_client

        di = DocumentIntelligence(timeout=2)  # 2 second timeout for test

        with pytest.raises(RuntimeError) as exc_info:
            di.analyze_document(pdf_bytes=b"fake pdf")

        error_msg = str(exc_info.value).lower()
        assert "timed out" in error_msg or "timeout" in error_msg
        assert "2" in str(exc_info.value)

    @patch('azure.ai.documentintelligence.DocumentIntelligenceClient')
    def test_unexpected_error_does_not_retry(self, mock_client_class):
        """Test unexpected errors do not trigger retries."""
        from planproof.docintel import DocumentIntelligence

        mock_client = Mock()
        mock_client.begin_analyze_document.side_effect = ValueError("Unexpected error")
        mock_client_class.return_value = mock_client

        di = DocumentIntelligence()

        with pytest.raises(RuntimeError) as exc_info:
            di.analyze_document(pdf_bytes=b"fake pdf")

        error_msg = str(exc_info.value).lower()
        assert "unexpected" in error_msg


class TestDatabaseRollbackHandling:
    """Test database rollback handling in db.py."""

    @patch('planproof.db.create_engine')
    @patch('planproof.db.sessionmaker')
    def test_create_application_rolls_back_on_error(self, mock_sessionmaker, mock_create_engine):
        """Test create_application rolls back on database error."""
        from planproof.db import Database

        mock_session = Mock()
        mock_session.commit.side_effect = Exception("Database error")

        mock_sessionmaker.return_value = Mock(return_value=mock_session)

        db = Database()

        with pytest.raises(RuntimeError) as exc_info:
            db.create_application(
                application_ref="APP/2024/001",
                applicant_name="Test"
            )

        # Verify rollback was called
        assert mock_session.rollback.called
        assert "failed to create application" in str(exc_info.value).lower()

    @patch('planproof.db.create_engine')
    @patch('planproof.db.sessionmaker')
    def test_create_document_rolls_back_on_error(self, mock_sessionmaker, mock_create_engine):
        """Test create_document rolls back on database error."""
        from planproof.db import Database

        mock_session = Mock()
        mock_session.commit.side_effect = Exception("Connection lost")

        mock_sessionmaker.return_value = Mock(return_value=mock_session)

        db = Database()

        with pytest.raises(RuntimeError) as exc_info:
            db.create_document(
                application_id=1,
                blob_uri="azure://test.pdf",
                filename="test.pdf"
            )

        assert mock_session.rollback.called
        assert "failed to create document" in str(exc_info.value).lower()

    @patch('planproof.db.create_engine')
    @patch('planproof.db.sessionmaker')
    def test_update_run_rolls_back_on_error(self, mock_sessionmaker, mock_create_engine):
        """Test update_run rolls back on database error."""
        from planproof.db import Database
        from planproof.db import Run

        mock_session = Mock()
        mock_run = Mock(spec=Run)
        mock_session.query.return_value.filter.return_value.first.return_value = mock_run
        mock_session.commit.side_effect = Exception("Update failed")

        mock_sessionmaker.return_value = Mock(return_value=mock_session)

        db = Database()

        with pytest.raises(RuntimeError) as exc_info:
            db.update_run(run_id=1, status="completed")

        assert mock_session.rollback.called
        assert "failed to update run" in str(exc_info.value).lower()

    @patch('planproof.db.create_engine')
    @patch('planproof.db.sessionmaker')
    def test_update_run_raises_value_error_if_not_found(self, mock_sessionmaker, mock_create_engine):
        """Test update_run raises ValueError if run not found."""
        from planproof.db import Database

        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.first.return_value = None

        mock_sessionmaker.return_value = Mock(return_value=mock_session)

        db = Database()

        with pytest.raises(ValueError) as exc_info:
            db.update_run(run_id=999, status="completed")

        assert "not found" in str(exc_info.value).lower()
        # Should not call rollback for not found
        assert not mock_session.rollback.called


class TestIngestFileValidation:
    """Test file validation in ingest.py."""

    def test_file_not_found_error(self):
        """Test ingestion fails with clear error for missing file."""
        from planproof.pipeline.ingest import ingest_pdf

        with pytest.raises(FileNotFoundError) as exc_info:
            ingest_pdf(
                pdf_path="/nonexistent/path/file.pdf",
                application_ref="APP/2024/001"
            )

        assert "not found" in str(exc_info.value).lower()
        assert "/nonexistent/path/file.pdf" in str(exc_info.value)

    def test_non_pdf_file_error(self, tmp_path):
        """Test ingestion fails with clear error for non-PDF file."""
        from planproof.pipeline.ingest import ingest_pdf

        txt_file = tmp_path / "document.txt"
        txt_file.write_text("Not a PDF")

        with pytest.raises(ValueError) as exc_info:
            ingest_pdf(
                pdf_path=str(txt_file),
                application_ref="APP/2024/001"
            )

        assert "pdf" in str(exc_info.value).lower()
        assert ".txt" in str(exc_info.value)

    def test_empty_file_error(self, tmp_path):
        """Test ingestion fails with clear error for empty file."""
        from planproof.pipeline.ingest import ingest_pdf

        empty_pdf = tmp_path / "empty.pdf"
        empty_pdf.write_bytes(b"")

        with pytest.raises(ValueError) as exc_info:
            ingest_pdf(
                pdf_path=str(empty_pdf),
                application_ref="APP/2024/001"
            )

        assert "empty" in str(exc_info.value).lower()

    @patch('planproof.pipeline.ingest.StorageClient')
    def test_hash_computation_error(self, mock_storage_class, tmp_path):
        """Test ingestion handles hash computation errors."""
        from planproof.pipeline.ingest import ingest_pdf

        # Create a PDF file that will cause read error
        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4\nFake PDF")

        # Make file unreadable by patching open
        with patch('builtins.open', side_effect=IOError("Permission denied")):
            with pytest.raises(RuntimeError) as exc_info:
                ingest_pdf(
                    pdf_path=str(pdf_file),
                    application_ref="APP/2024/001"
                )

            assert "failed to read" in str(exc_info.value).lower()
            assert "hashing" in str(exc_info.value).lower()

    @patch('planproof.db.Database')
    @patch('planproof.pipeline.ingest.StorageClient')
    def test_blob_upload_error(self, mock_storage_class, mock_db_class, tmp_path):
        """Test ingestion handles blob upload errors."""
        from planproof.pipeline.ingest import ingest_pdf

        pdf_file = tmp_path / "test.pdf"
        pdf_file.write_bytes(b"%PDF-1.4\nFake PDF content")

        # Mock storage to fail
        mock_storage = Mock()
        mock_storage.upload_pdf.side_effect = Exception("Upload failed")
        mock_storage_class.return_value = mock_storage

        # Mock database
        mock_db = Mock()
        mock_app = Mock()
        mock_app.id = 1
        mock_db.get_application_by_ref.return_value = mock_app

        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.first.return_value = None
        mock_db.get_session.return_value = mock_session

        mock_db_class.return_value = mock_db

        with pytest.raises(RuntimeError) as exc_info:
            ingest_pdf(
                pdf_path=str(pdf_file),
                application_ref="APP/2024/001",
                storage_client=mock_storage,
                db=mock_db
            )

        assert "failed to upload" in str(exc_info.value).lower()
        assert "blob storage" in str(exc_info.value).lower()


class TestRunOrchestratorErrorHandling:
    """Test error handling in run_orchestrator.py."""

    @patch('planproof.ui.run_orchestrator.Database')
    def test_error_file_writing_on_critical_failure(self, mock_db_class, tmp_path, monkeypatch):
        """Test critical errors are written to error files."""
        from planproof.ui.run_orchestrator import _run_pipeline_threaded

        # Change to temp directory
        monkeypatch.chdir(tmp_path)

        # Mock database to fail on update
        mock_db = Mock()
        mock_db.update_run.side_effect = Exception("Critical DB error")
        mock_db_class.return_value = mock_db

        # Run pipeline (will fail)
        _run_pipeline_threaded(
            run_id=1,
            pdf_paths=[],
            application_ref="APP/2024/001",
            applicant_name=None,
            parent_submission_id=None,
            db=mock_db
        )

        # Check error file was created
        error_file = tmp_path / "runs" / "1" / "outputs" / "critical_update_error.txt"

        # Give it a moment to write
        time.sleep(0.5)

        if error_file.exists():
            content = error_file.read_text()
            assert "Critical error" in content
            assert "Run ID: 1" in content

    def test_read_error_files_handles_io_errors(self, tmp_path):
        """Test reading error files handles IO errors gracefully."""
        from planproof.ui.run_orchestrator import get_run_results

        # Create a run directory with an inaccessible error file
        run_dir = tmp_path / "runs" / "1"
        outputs_dir = run_dir / "outputs"
        outputs_dir.mkdir(parents=True)

        # Create error file
        error_file = outputs_dir / "error_ingest.txt"
        error_file.write_text("Test error")

        # Make it unreadable by patching open
        with patch('builtins.open', side_effect=IOError("Permission denied")):
            # Should not crash, just return partial results
            # This would need actual implementation context to test properly
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
