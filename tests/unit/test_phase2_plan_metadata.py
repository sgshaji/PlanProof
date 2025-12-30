"""Unit tests for Phase 2: Plan Metadata Extraction"""
import pytest
from planproof.pipeline.field_mapper import (
    classify_plan_type,
    extract_scale_ratio,
    detect_north_arrow,
    detect_scale_bar,
    extract_drawing_number,
    extract_revision,
)


def test_classify_location_plan():
    """Test location plan classification with 1:1250 scale"""
    blocks = [
        {"content": "LOCATION PLAN", "page": 1},
        {"content": "Scale 1:1250", "page": 1},
    ]
    result = classify_plan_type(blocks)
    assert result == "location_plan"


def test_classify_block_plan():
    """Test block plan classification"""
    blocks = [
        {"content": "BLOCK PLAN", "page": 1},
        {"content": "1:500", "page": 1},
    ]
    result = classify_plan_type(blocks)
    assert result == "block_plan"


def test_classify_floor_plan():
    """Test floor plan classification"""
    blocks = [
        {"content": "Ground Floor Plan", "page": 1},
    ]
    result = classify_plan_type(blocks)
    assert result == "floor_plan"


def test_extract_scale_1_1250():
    """Test scale extraction: 1:1250"""
    blocks = [
        {"content": "Scale 1:1250", "page": 1, "index": 0},
    ]
    scale, source, confidence = extract_scale_ratio(blocks)
    assert scale == "1:1250"
    assert confidence == 0.9  # Common architectural scale


def test_extract_scale_at_format():
    """Test scale extraction: @ 1:500 @ A3"""
    blocks = [
        {"content": "@ 1:500 @ A3", "page": 1, "index": 0},
    ]
    scale, source, confidence = extract_scale_ratio(blocks)
    assert scale == "1:500"
    assert confidence == 0.9


def test_extract_uncommon_scale():
    """Test uncommon scale has lower confidence"""
    blocks = [
        {"content": "Scale 1:750", "page": 1, "index": 0},
    ]
    scale, source, confidence = extract_scale_ratio(blocks)
    assert scale == "1:750"
    assert confidence == 0.7  # Not in common scales list


def test_detect_north_arrow_grid_north():
    """Test north arrow detection: GRID NORTH"""
    blocks = [
        {"content": "GRID NORTH", "page": 1, "index": 0},
    ]
    has_north, source, confidence = detect_north_arrow(blocks)
    assert has_north is True
    assert confidence == 0.8


def test_detect_north_arrow_standalone_n():
    """Test north arrow detection: standalone N"""
    blocks = [
        {"content": "N", "page": 1, "index": 0},
    ]
    has_north, source, confidence = detect_north_arrow(blocks)
    assert has_north is True
    assert confidence == 0.9  # Higher confidence for short form


def test_no_north_arrow():
    """Test no north arrow present"""
    blocks = [
        {"content": "Northern elevation", "page": 1, "index": 0},  # Should not match
        {"content": "Some other text", "page": 1, "index": 1},
    ]
    has_north, source, confidence = detect_north_arrow(blocks)
    assert has_north is False


def test_detect_scale_bar():
    """Test scale bar detection"""
    blocks = [
        {"content": "Scale Bar", "page": 1, "index": 0},
    ]
    has_bar, source, confidence = detect_scale_bar(blocks)
    assert has_bar is True
    assert confidence == 0.8


def test_detect_scale_bar_numeric():
    """Test scale bar with numeric indicators"""
    blocks = [
        {"content": "0 5 10 15 20m", "page": 1, "index": 0},
    ]
    has_bar, source, confidence = detect_scale_bar(blocks)
    assert has_bar is True


def test_extract_drawing_number_standard():
    """Test drawing number extraction: standard format"""
    blocks = [
        {"content": "Drawing No: 2024/001", "page": 1, "index": 0},
    ]
    drawing_num, source, confidence = extract_drawing_number(blocks)
    assert drawing_num == "2024/001"
    assert confidence == 0.8


def test_extract_drawing_number_dwg_format():
    """Test drawing number extraction: Dwg No format"""
    blocks = [
        {"content": "Dwg No: P01", "page": 1, "index": 0},
    ]
    drawing_num, source, confidence = extract_drawing_number(blocks)
    assert drawing_num == "P01"


def test_extract_drawing_number_no_digits():
    """Test drawing number requires at least one digit"""
    blocks = [
        {"content": "Drawing No: ABC", "page": 1, "index": 0},  # No digits - should fail
    ]
    drawing_num, source, confidence = extract_drawing_number(blocks)
    assert drawing_num is None


def test_extract_revision_letter():
    """Test revision extraction: single letter"""
    blocks = [
        {"content": "Rev: A", "page": 1, "index": 0},
    ]
    revision, source, confidence = extract_revision(blocks)
    assert revision == "A"
    assert confidence == 0.8


def test_extract_revision_p_format():
    """Test revision extraction: P01 format"""
    blocks = [
        {"content": "Revision: P01", "page": 1, "index": 0},
    ]
    revision, source, confidence = extract_revision(blocks)
    assert revision == "P01"


def test_extract_revision_normalized_uppercase():
    """Test revision is normalized to uppercase"""
    blocks = [
        {"content": "Rev. b", "page": 1, "index": 0},
    ]
    revision, source, confidence = extract_revision(blocks)
    assert revision == "B"  # Should be uppercase


def test_no_plan_metadata_in_application_form():
    """Test plan metadata not extracted from application forms"""
    from planproof.pipeline.field_mapper import map_fields
    
    extraction = {
        "text_blocks": [
            {"content": "Application Form", "page": 1, "index": 0},
            {"content": "Planning Portal Reference", "page": 1, "index": 1},
        ]
    }
    
    result = map_fields(extraction)
    fields = result["fields"]
    
    # Should classify as application_form
    assert fields["document_type"] == "application_form"
    
    # Should NOT have plan metadata
    assert "plan_type" not in fields
    assert "scale_ratio" not in fields
