"""
Performance tests for PlanProof.

Tests cover:
- Large document processing
- Concurrent processing load
- Memory usage
- Response time benchmarks
- Database query performance
"""

import pytest
import time
import psutil
import os
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime
import tempfile


class TestLargeDocumentPerformance:
    """Performance tests for large document processing."""

    @pytest.mark.slow
    @patch('planproof.docintel.DocumentIntelligence')
    def test_large_pdf_processing_time(self, mock_docintel_class):
        """Test processing time for large PDFs (50+ pages)."""
        from planproof.pipeline.extract import extract_from_pdf_bytes

        # Mock large document result
        mock_client = Mock()
        large_result = {
            "text_blocks": [
                {"content": f"Page {i} content", "page": i, "bbox": [0, 0, 100, 100]}
                for i in range(1, 51)  # 50 pages
            ],
            "tables": [],
            "metadata": {"page_count": 50}
        }
        mock_client.analyze_document.return_value = large_result
        mock_docintel_class.return_value = mock_client

        # Create large fake PDF (50MB)
        large_pdf_bytes = b"%PDF-1.4\n" + (b"X" * 50 * 1024 * 1024)

        start_time = time.time()

        result = extract_from_pdf_bytes(
            pdf_bytes=large_pdf_bytes,
            document_id=1,
            docintel_client=mock_client
        )

        elapsed_time = time.time() - start_time

        assert result is not None
        # Should complete within reasonable time (mocked, so should be fast)
        assert elapsed_time < 10.0  # 10 seconds max for mocked operation

    @pytest.mark.slow
    def test_large_file_hash_computation_performance(self, tmp_path):
        """Test hash computation performance for large files."""
        from planproof.pipeline.ingest import ingest_pdf

        # Create large PDF file (100MB)
        large_pdf = tmp_path / "large_document.pdf"

        # Write in chunks to avoid memory issues
        with open(large_pdf, "wb") as f:
            f.write(b"%PDF-1.4\n")
            for _ in range(100):
                f.write(b"X" * 1024 * 1024)  # 1MB chunks

        start_time = time.time()

        with patch('planproof.pipeline.ingest.StorageClient'):
            with patch('planproof.pipeline.ingest.Database') as mock_db_class:
                mock_db = Mock()
                mock_app = Mock()
                mock_app.id = 1
                mock_db.get_application_by_ref.return_value = mock_app
                mock_db.create_document.return_value = Mock(id=1)

                mock_session = Mock()
                mock_session.query.return_value.filter.return_value.first.return_value = None
                mock_db.get_session.return_value = mock_session
                mock_db_class.return_value = mock_db

                try:
                    ingest_pdf(
                        pdf_path=str(large_pdf),
                        application_ref="APP/2024/001",
                        db=mock_db
                    )
                except Exception:
                    pass  # May fail on upload, but hash should complete

        elapsed_time = time.time() - start_time

        # Hash computation should be reasonably fast
        assert elapsed_time < 30.0  # 30 seconds max for 100MB file

    @pytest.mark.slow
    @patch('planproof.pipeline.validate.load_rule_catalog')
    def test_validation_performance_many_rules(self, mock_catalog):
        """Test validation performance with many rules."""
        from planproof.pipeline.validate import validate_extraction

        # Create many mock rules
        mock_rules = []
        for i in range(100):
            mock_rule = Mock()
            mock_rule.rule_id = f"R-{i:03d}"
            mock_rule.rule_category = "FIELD_REQUIRED"
            mock_rule.severity = "error"
            mock_rules.append(mock_rule)

        mock_catalog.return_value = mock_rules

        extracted_data = {"site_address": "123 High Street"}
        documents = [{"document_type": "application_form"}]

        start_time = time.time()

        results = validate_extraction(
            extracted_data=extracted_data,
            documents=documents,
            rule_catalog=mock_rules
        )

        elapsed_time = time.time() - start_time

        assert results is not None
        # Should complete within reasonable time
        assert elapsed_time < 5.0  # 5 seconds for 100 rules


class TestConcurrentProcessingLoad:
    """Load tests for concurrent processing."""

    @pytest.mark.slow
    @patch('planproof.ui.run_orchestrator.Database')
    @patch('planproof.ui.run_orchestrator.StorageClient')
    def test_concurrent_runs_performance(self, mock_storage_class, mock_db_class, tmp_path, monkeypatch):
        """Test performance with multiple concurrent runs."""
        from planproof.ui.run_orchestrator import start_run

        monkeypatch.chdir(tmp_path)

        # Setup mocks
        mock_storage = Mock()
        mock_storage.upload_pdf_bytes.return_value = "azure://test.pdf"
        mock_storage_class.return_value = mock_storage

        run_counter = {"count": 0}

        def create_run_side_effect(*args, **kwargs):
            run_counter["count"] += 1
            return {"id": run_counter["count"]}

        mock_db = Mock()
        mock_db.create_run.side_effect = create_run_side_effect
        mock_db_class.return_value = mock_db

        # Create fake files
        fake_files = []
        for i in range(10):
            fake_file = Mock()
            fake_file.name = f"test{i}.pdf"
            fake_file.getbuffer.return_value = b"fake pdf"
            fake_files.append(fake_file)

        start_time = time.time()

        # Start 10 concurrent runs
        run_ids = []
        for i, fake_file in enumerate(fake_files):
            run_id = start_run(
                app_ref=f"APP/2024/{i:03d}",
                files=[fake_file]
            )
            run_ids.append(run_id)

        elapsed_time = time.time() - start_time

        # All runs should start quickly
        assert len(run_ids) == 10
        assert elapsed_time < 5.0  # Should start all within 5 seconds

    @pytest.mark.slow
    def test_memory_usage_multiple_documents(self, tmp_path):
        """Test memory usage doesn't grow excessively with multiple documents."""
        from planproof.pipeline.ingest import ingest_pdf

        # Get initial memory
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Process multiple documents
        with patch('planproof.pipeline.ingest.StorageClient'):
            with patch('planproof.pipeline.ingest.Database') as mock_db_class:
                mock_db = Mock()
                mock_app = Mock()
                mock_app.id = 1
                mock_db.get_application_by_ref.return_value = mock_app
                mock_db.create_document.return_value = Mock(id=1)

                mock_session = Mock()
                mock_session.query.return_value.filter.return_value.first.return_value = None
                mock_db.get_session.return_value = mock_session
                mock_db_class.return_value = mock_db

                for i in range(20):
                    pdf_file = tmp_path / f"test{i}.pdf"
                    pdf_file.write_bytes(b"%PDF-1.4\n" + (b"X" * 1024 * 1024))  # 1MB each

                    try:
                        ingest_pdf(
                            pdf_path=str(pdf_file),
                            application_ref="APP/2024/001",
                            db=mock_db
                        )
                    except Exception:
                        pass

        # Get final memory
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Memory shouldn't increase too much (allow 100MB growth)
        assert memory_increase < 100.0


class TestDatabaseQueryPerformance:
    """Performance tests for database queries."""

    @pytest.mark.slow
    @patch('planproof.db.create_engine')
    @patch('planproof.db.sessionmaker')
    def test_bulk_document_retrieval_performance(self, mock_sessionmaker, mock_create_engine):
        """Test performance of retrieving many documents."""
        from planproof.db import Database

        # Mock many documents
        mock_docs = []
        for i in range(1000):
            mock_doc = Mock()
            mock_doc.id = i
            mock_doc.filename = f"doc{i}.pdf"
            mock_docs.append(mock_doc)

        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.all.return_value = mock_docs
        mock_sessionmaker.return_value = Mock(return_value=mock_session)

        db = Database()

        start_time = time.time()

        # Query many documents
        session = db.get_session()
        from planproof.db import Document
        results = session.query(Document).all()

        elapsed_time = time.time() - start_time

        assert len(results) == 1000
        # Should complete quickly (mocked)
        assert elapsed_time < 1.0

    @pytest.mark.slow
    @patch('planproof.db.create_engine')
    @patch('planproof.db.sessionmaker')
    def test_validation_result_query_performance(self, mock_sessionmaker, mock_create_engine):
        """Test performance of querying validation results."""
        from planproof.db import Database

        # Mock many validation results
        mock_results = []
        for i in range(500):
            mock_result = Mock()
            mock_result.id = i
            mock_result.rule_id = f"R-{i:03d}"
            mock_result.status = "pass"
            mock_results.append(mock_result)

        mock_session = Mock()
        mock_session.query.return_value.filter.return_value.all.return_value = mock_results
        mock_sessionmaker.return_value = Mock(return_value=mock_session)

        db = Database()

        start_time = time.time()

        # Query validation results
        session = db.get_session()
        from planproof.db import ValidationResult
        results = session.query(ValidationResult).all()

        elapsed_time = time.time() - start_time

        assert len(results) == 500
        assert elapsed_time < 1.0


class TestResponseTimeBenchmarks:
    """Benchmark tests for API response times."""

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_api_health_check_response_time(self):
        """Test API health check response time."""
        from fastapi.testclient import TestClient

        try:
            from planproof.api.main import app

            client = TestClient(app)

            start_time = time.time()
            response = client.get("/health")
            elapsed_time = time.time() - start_time

            assert response.status_code == 200
            # Health check should be very fast
            assert elapsed_time < 0.5
        except ImportError:
            pytest.skip("FastAPI app not available")

    @pytest.mark.slow
    def test_file_upload_response_time(self, tmp_path):
        """Test file upload endpoint response time."""
        from fastapi.testclient import TestClient

        try:
            from planproof.api.main import app

            client = TestClient(app)

            # Create test file
            pdf_file = tmp_path / "test.pdf"
            pdf_file.write_bytes(b"%PDF-1.4\nTest content")

            start_time = time.time()

            with open(pdf_file, "rb") as f:
                response = client.post(
                    "/applications/APP-2024-001/documents",
                    files={"file": ("test.pdf", f, "application/pdf")}
                )

            elapsed_time = time.time() - start_time

            # Upload should complete reasonably fast
            assert elapsed_time < 5.0
        except ImportError:
            pytest.skip("FastAPI app not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
