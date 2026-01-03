"""
Shared test fixtures for Azure service mocking.

Provides reusable fixtures for:
- Azure Blob Storage
- Azure Document Intelligence
- Azure OpenAI
- Database mocking
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from pathlib import Path


# ============================================================================
# Azure Storage Fixtures
# ============================================================================

@pytest.fixture
def azure_storage_mock():
    """Comprehensive Azure Blob Storage mock."""
    with patch('planproof.storage.BlobServiceClient') as mock:
        # Create mock hierarchy
        mock_service = Mock()
        mock_container = Mock()
        mock_blob = Mock()
        
        # Blob operations
        mock_blob.upload_blob.return_value = Mock(
            name="test.pdf",
            etag="abc123",
            last_modified=datetime.now()
        )
        mock_blob.download_blob.return_value = Mock(
            readall=lambda: b"fake pdf content"
        )
        mock_blob.delete_blob.return_value = None
        mock_blob.url = "https://teststorage.blob.core.windows.net/inbox/test.pdf"
        mock_blob.exists.return_value = True
        
        # Container operations
        mock_container.get_blob_client.return_value = mock_blob
        mock_container.list_blobs.return_value = [
            Mock(name="file1.pdf", size=1024),
            Mock(name="file2.pdf", size=2048)
        ]
        
        # Service operations
        mock_service.get_container_client.return_value = mock_container
        mock.from_connection_string.return_value = mock_service
        
        yield mock


@pytest.fixture
def azure_storage_error_mock():
    """Azure Storage mock that simulates errors."""
    with patch('planproof.storage.BlobServiceClient') as mock:
        mock_service = Mock()
        mock_container = Mock()
        mock_blob = Mock()
        
        # Simulate various errors
        mock_blob.upload_blob.side_effect = Exception("Upload failed")
        mock_blob.download_blob.side_effect = Exception("Blob not found")
        
        mock_container.get_blob_client.return_value = mock_blob
        mock_service.get_container_client.return_value = mock_container
        mock.from_connection_string.return_value = mock_service
        
        yield mock


# ============================================================================
# Document Intelligence Fixtures
# ============================================================================

@pytest.fixture
def doc_intel_mock_with_text():
    """Document Intelligence mock with text extraction."""
    with patch('planproof.docintel.DocumentAnalysisClient') as mock:
        mock_client = Mock()
        
        # Create realistic page with text
        mock_line1 = Mock()
        mock_line1.content = "Planning Application Form"
        mock_line1.polygon = [100, 100, 500, 100, 500, 120, 100, 120]
        
        mock_line2 = Mock()
        mock_line2.content = "Site Address: 123 High Street, Birmingham, B1 1AA"
        mock_line2.polygon = [100, 150, 600, 150, 600, 170, 100, 170]
        
        mock_line3 = Mock()
        mock_line3.content = "Applicant: John Smith"
        mock_line3.polygon = [100, 200, 400, 200, 400, 220, 100, 220]
        
        mock_page = Mock()
        mock_page.lines = [mock_line1, mock_line2, mock_line3]
        mock_page.page_number = 1
        mock_page.width = 612
        mock_page.height = 792
        mock_page.unit = "pixel"
        
        mock_result = Mock()
        mock_result.pages = [mock_page]
        mock_result.tables = []
        mock_result.key_value_pairs = []
        
        mock_poller = Mock()
        mock_poller.result.return_value = mock_result
        
        mock_client.begin_analyze_document_from_url.return_value = mock_poller
        mock_client.begin_analyze_document.return_value = mock_poller
        
        mock.return_value = mock_client
        yield mock


@pytest.fixture
def doc_intel_mock_with_tables():
    """Document Intelligence mock with table extraction."""
    with patch('planproof.docintel.DocumentAnalysisClient') as mock:
        mock_client = Mock()
        
        # Create mock table
        cells = []
        for row in range(3):
            for col in range(2):
                mock_cell = Mock()
                mock_cell.content = f"Cell {row},{col}"
                mock_cell.row_index = row
                mock_cell.column_index = col
                mock_cell.row_span = 1
                mock_cell.column_span = 1
                cells.append(mock_cell)
        
        mock_table = Mock()
        mock_table.cells = cells
        mock_table.row_count = 3
        mock_table.column_count = 2
        mock_table.bounding_regions = []
        
        mock_result = Mock()
        mock_result.pages = []
        mock_result.tables = [mock_table]
        mock_result.key_value_pairs = []
        
        mock_poller = Mock()
        mock_poller.result.return_value = mock_result
        
        mock_client.begin_analyze_document_from_url.return_value = mock_poller
        mock_client.begin_analyze_document.return_value = mock_poller
        
        mock.return_value = mock_client
        yield mock


@pytest.fixture
def doc_intel_error_mock():
    """Document Intelligence mock that simulates errors."""
    with patch('planproof.docintel.DocumentAnalysisClient') as mock:
        mock_client = Mock()
        mock_client.begin_analyze_document_from_url.side_effect = Exception("Analysis failed")
        mock_client.begin_analyze_document.side_effect = Exception("Analysis failed")
        
        mock.return_value = mock_client
        yield mock


# ============================================================================
# Azure OpenAI Fixtures
# ============================================================================

@pytest.fixture
def openai_mock_field_extraction():
    """Azure OpenAI mock for field extraction."""
    with patch('planproof.aoai.AzureOpenAI') as mock:
        mock_client = Mock()
        
        def create_completion(*args, **kwargs):
            messages = kwargs.get('messages', [])
            last_message = messages[-1]['content'] if messages else ""
            
            # Simulate different responses based on prompt
            if "site_address" in last_message.lower():
                response_text = "123 High Street, Birmingham, B1 1AA"
            elif "applicant" in last_message.lower():
                response_text = "John Smith"
            elif "fee" in last_message.lower():
                response_text = "£206"
            else:
                response_text = "Extracted value"
            
            mock_message = Mock()
            mock_message.content = response_text
            mock_choice = Mock()
            mock_choice.message = mock_message
            mock_response = Mock()
            mock_response.choices = [mock_choice]
            
            return mock_response
        
        mock_client.chat.completions.create = Mock(side_effect=create_completion)
        
        mock.return_value = mock_client
        yield mock


@pytest.fixture
def openai_mock_conflict_resolution():
    """Azure OpenAI mock for conflict resolution."""
    with patch('planproof.aoai.AzureOpenAI') as mock:
        mock_client = Mock()
        
        mock_message = Mock()
        mock_message.content = "The correct value is: 123 High Street, Birmingham, B1 1AA (full format)"
        mock_choice = Mock()
        mock_choice.message = mock_message
        mock_response = Mock()
        mock_response.choices = [mock_choice]
        
        mock_client.chat.completions.create.return_value = mock_response
        
        mock.return_value = mock_client
        yield mock


@pytest.fixture
def openai_error_mock():
    """Azure OpenAI mock that simulates errors."""
    with patch('planproof.aoai.AzureOpenAI') as mock:
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API rate limit exceeded")
        
        mock.return_value = mock_client
        yield mock


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture
def mock_database_with_data():
    """Mock database with sample data."""
    db = Mock()
    
    # Mock runs
    db.get_run.return_value = {
        "run_id": 1,
        "status": "completed",
        "created_at": datetime.now(),
        "total_documents": 5,
        "total_issues": 10,
        "resolved_issues": 7
    }
    
    # Mock documents
    db.get_documents.return_value = [
        {
            "document_id": 1,
            "document_type": "site_plan",
            "blob_url": "https://storage/doc1.pdf",
            "status": "processed"
        },
        {
            "document_id": 2,
            "document_type": "floor_plan",
            "blob_url": "https://storage/doc2.pdf",
            "status": "processed"
        }
    ]
    
    # Mock issues
    db.get_issues.return_value = [
        {
            "issue_id": "DOC-001",
            "severity": "error",
            "status": "open",
            "rule_id": "DOC-01",
            "message": "Missing site plan"
        },
        {
            "issue_id": "CON-001",
            "severity": "warning",
            "status": "resolved",
            "rule_id": "CON-01",
            "message": "Address discrepancy"
        }
    ]
    
    # Mock validation results
    db.get_validation_results.return_value = [
        {
            "validation_id": 1,
            "rule_id": "DOC-01",
            "status": "fail",
            "extracted_value": None,
            "expected_value": "site_plan.pdf"
        }
    ]
    
    return db


@pytest.fixture
def mock_empty_database():
    """Mock database with no data."""
    db = Mock()
    
    db.get_run.return_value = None
    db.get_documents.return_value = []
    db.get_issues.return_value = []
    db.get_validation_results.return_value = []
    
    return db


# ============================================================================
# File System Fixtures
# ============================================================================

@pytest.fixture
def sample_pdf_bytes():
    """Sample PDF file content as bytes."""
    return b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Count 1\n/Kids [3 0 R]\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n190\n%%EOF"


@pytest.fixture
def temp_pdf_file(tmp_path, sample_pdf_bytes):
    """Create temporary PDF file."""
    pdf_path = tmp_path / "test_document.pdf"
    pdf_path.write_bytes(sample_pdf_bytes)
    return pdf_path


@pytest.fixture
def temp_run_directory(tmp_path):
    """Create temporary run directory structure."""
    run_dir = tmp_path / "runs" / "1"
    inputs_dir = run_dir / "inputs"
    outputs_dir = run_dir / "outputs"
    
    inputs_dir.mkdir(parents=True)
    outputs_dir.mkdir(parents=True)
    
    return run_dir


# ============================================================================
# Sample Data Fixtures
# ============================================================================

@pytest.fixture
def sample_extraction_result():
    """Complete sample extraction result."""
    return {
        "document_id": 1,
        "document_type": "planning_application",
        "text_blocks": [
            {
                "content": "Planning Application Form",
                "page_number": 1,
                "index": 0,
                "bounding_box": [100, 100, 500, 120]
            },
            {
                "content": "Site Address: 123 High Street, Birmingham, B1 1AA",
                "page_number": 1,
                "index": 1,
                "bounding_box": [100, 150, 600, 170]
            },
            {
                "content": "Applicant Name: John Smith",
                "page_number": 1,
                "index": 2,
                "bounding_box": [100, 200, 400, 220]
            },
            {
                "content": "Development Proposal: Single storey rear extension",
                "page_number": 2,
                "index": 3,
                "bounding_box": [100, 100, 600, 140]
            }
        ],
        "tables": [
            {
                "cells": [
                    {"content": "Document Type", "row_index": 0, "col_index": 0},
                    {"content": "Status", "row_index": 0, "col_index": 1},
                    {"content": "Site Plan", "row_index": 1, "col_index": 0},
                    {"content": "Provided", "row_index": 1, "col_index": 1},
                    {"content": "Floor Plan", "row_index": 2, "col_index": 0},
                    {"content": "Missing", "row_index": 2, "col_index": 1}
                ]
            }
        ],
        "fields": {
            "site_address": "123 High Street, Birmingham, B1 1AA",
            "site_address_confidence": 0.92,
            "site_address_page": 1,
            "site_address_bbox": [100, 150, 600, 170],
            "applicant_name": "John Smith",
            "applicant_name_confidence": 0.88,
            "applicant_name_page": 1,
            "development_proposal": "Single storey rear extension",
            "development_proposal_confidence": 0.85,
            "development_proposal_page": 2
        }
    }


@pytest.fixture
def sample_validation_rules():
    """Sample validation rules catalog."""
    return {
        "rules": [
            {
                "rule_id": "DOC-01",
                "category": "Document Presence",
                "type": "presence",
                "required": True,
                "field": "site_plan",
                "message": "Site plan is required"
            },
            {
                "rule_id": "DOC-02",
                "category": "Document Presence",
                "type": "presence",
                "required": True,
                "field": "floor_plan",
                "message": "Floor plan is required"
            },
            {
                "rule_id": "CON-01",
                "category": "Consistency",
                "type": "consistency",
                "required": True,
                "fields": ["site_address", "site_address_alt"],
                "message": "Site address must be consistent across documents"
            }
        ]
    }


@pytest.fixture
def sample_issues():
    """Sample enhanced issues."""
    return [
        {
            "issue_id": "DOC-001",
            "run_id": 1,
            "document_id": 1,
            "rule_id": "DOC-01",
            "severity": "error",
            "status": "open",
            "rule_category": "Document Presence",
            "message": "Required document missing: Site Plan",
            "resolution_options": ["upload", "mark_na"],
            "evidence_page": 1,
            "created_at": datetime.now()
        },
        {
            "issue_id": "CON-001",
            "run_id": 1,
            "document_id": 1,
            "rule_id": "CON-01",
            "severity": "warning",
            "status": "open",
            "rule_category": "Consistency",
            "message": "Discrepancy found in site address between form and plans",
            "resolution_options": ["explain", "correct"],
            "evidence_page": 2,
            "evidence_text": "Site address appears as '123 High St' in one place and '123 High Street, Birmingham' in another",
            "created_at": datetime.now()
        }
    ]


# ============================================================================
# Configuration Fixtures
# ============================================================================

@pytest.fixture
def mock_settings():
    """Mock application settings."""
    with patch('planproof.config.get_settings') as mock:
        settings = Mock()
        settings.azure_storage_connection_string = "DefaultEndpointsProtocol=https;AccountName=test"
        settings.azure_doc_intel_endpoint = "https://test.cognitiveservices.azure.com/"
        settings.azure_doc_intel_key = "test_key"
        settings.azure_openai_endpoint = "https://test.openai.azure.com/"
        settings.azure_openai_key = "test_key"
        settings.azure_openai_deployment = "gpt-4"
        settings.database_url = "postgresql://test:test@localhost/test"
        settings.enable_db_writes = True
        settings.llm_temperature = 0.0
        settings.llm_max_tokens = 2000
        
        mock.return_value = settings
        yield mock


if __name__ == "__main__":
    print("Shared test fixtures loaded successfully")
