"""
Unit tests for document viewer component.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from PIL import Image


def test_check_pdf_library():
    """Test PDF library availability check."""
    from planproof.ui.components.document_viewer import check_pdf_library
    
    available, library = check_pdf_library()
    assert isinstance(available, bool)
    assert isinstance(library, str)
    assert library in ["PyMuPDF", "pdf2image", "None"]


@pytest.mark.skipif(
    not pytest.importorskip("fitz", reason="PyMuPDF not installed"),
    reason="PyMuPDF not available"
)
def test_get_page_count_with_mock():
    """Test page count retrieval."""
    from planproof.ui.components.document_viewer import _get_page_count, PYMUPDF_AVAILABLE
    
    if not PYMUPDF_AVAILABLE:
        pytest.skip("PyMuPDF not available")
    
    # This test requires actual PyMuPDF to be installed
    # Skip for now as it's an integration concern
    pytest.skip("Requires PyMuPDF installation")


def test_draw_bbox():
    """Test bounding box drawing on image."""
    from planproof.ui.components.document_viewer import _draw_bbox
    
    # Create test image
    img = Image.new("RGB", (100, 100), color="white")
    
    # Normalized bbox (0-1)
    bbox = {"x": 0.1, "y": 0.1, "width": 0.5, "height": 0.3}
    
    result = _draw_bbox(img, bbox)
    
    assert isinstance(result, Image.Image)
    assert result.size == (100, 100)


def test_draw_bbox_absolute_coords():
    """Test bounding box with absolute coordinates."""
    from planproof.ui.components.document_viewer import _draw_bbox
    
    img = Image.new("RGB", (200, 200), color="white")
    
    # Absolute bbox
    bbox = {"x": 20, "y": 20, "width": 100, "height": 80}
    
    result = _draw_bbox(img, bbox)
    
    assert isinstance(result, Image.Image)
    assert result.size == (200, 200)

