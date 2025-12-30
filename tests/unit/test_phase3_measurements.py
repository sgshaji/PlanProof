"""Unit tests for Phase 3: Measurement Extraction"""
import pytest
from planproof.pipeline.field_mapper import (
    extract_measurements,
    _normalize_unit,
    _detect_measurement_context,
    _detect_entity,
    _detect_datum,
    _detect_existing_or_proposed,
)


def test_extract_simple_meters():
    """Test extracting simple meter measurement"""
    blocks = [
        {"content": "Height: 8.5m", "page": 1, "index": 0}
    ]
    measurements = extract_measurements(blocks)
    assert len(measurements) == 1
    assert measurements[0]["value"] == 8.5
    assert measurements[0]["unit"] == "m"


def test_extract_area_sqm():
    """Test extracting square meter measurement"""
    blocks = [
        {"content": "Floor area: 100 sqm", "page": 1, "index": 0}
    ]
    measurements = extract_measurements(blocks)
    assert len(measurements) == 1
    assert measurements[0]["value"] == 100
    assert measurements[0]["unit"] == "sqm"
    assert measurements[0]["context"] == "area"


def test_extract_with_comma():
    """Test extracting measurement with comma in number"""
    blocks = [
        {"content": "Total area of 20,512 ft2", "page": 1, "index": 0}
    ]
    measurements = extract_measurements(blocks)
    assert len(measurements) == 1
    assert measurements[0]["value"] == 20512.0
    assert measurements[0]["unit"] == "sqft"


def test_extract_with_superscript():
    """Test extracting measurement with superscript 2"""
    blocks = [
        {"content": "Area: 1,906m²", "page": 1, "index": 0}
    ]
    measurements = extract_measurements(blocks)
    assert len(measurements) == 1
    assert measurements[0]["value"] == 1906.0
    assert measurements[0]["unit"] == "sqm"


def test_normalize_unit_meters():
    """Test unit normalization for meters"""
    assert _normalize_unit("m") == "m"
    assert _normalize_unit("metre") == "m"
    assert _normalize_unit("meters") == "m"


def test_normalize_unit_sqm():
    """Test unit normalization for square meters"""
    assert _normalize_unit("sqm") == "sqm"
    assert _normalize_unit("sq m") == "sqm"
    assert _normalize_unit("m²") == "sqm"
    assert _normalize_unit("m2") == "sqm"


def test_normalize_unit_sqft():
    """Test unit normalization for square feet"""
    assert _normalize_unit("ft2") == "sqft"
    assert _normalize_unit("ft²") == "sqft"


def test_detect_context_ridge_height():
    """Test detecting ridge height context"""
    text = "The proposed ridge height is 8.5m"
    context = _detect_measurement_context(text.lower())
    assert context == "height"


def test_detect_context_floor_area():
    """Test detecting floor area context"""
    text = "Gross internal area (GIA) of 150 sqm"
    context = _detect_measurement_context(text.lower())
    assert context == "area"


def test_detect_context_width():
    """Test detecting width context"""
    text = "Width of extension: 4.2m"
    context = _detect_measurement_context(text.lower())
    assert context == "width"


def test_detect_entity_bedroom():
    """Test detecting bedroom entity"""
    text = "Bedroom 1 measures 12 sqm"
    entity = _detect_entity(text.lower())
    assert entity is not None
    assert "bedroom" in entity.lower()


def test_detect_entity_extension():
    """Test detecting extension entity"""
    text = "The rear extension has a depth of 5m"
    entity = _detect_entity(text.lower())
    assert entity is not None
    assert "extension" in entity.lower()


def test_detect_no_entity():
    """Test no entity detected"""
    text = "Overall dimensions"
    entity = _detect_entity(text.lower())
    assert entity is None


def test_detect_datum_ground_level():
    """Test detecting ground level datum"""
    text = "Height from ground level: 8m"
    datum = _detect_datum(text.lower())
    assert datum is not None
    assert "ground level" in datum.lower()


def test_detect_datum_ridge():
    """Test detecting ridge datum"""
    text = "Measured to ridge: 9.5m"
    datum = _detect_datum(text.lower())
    assert datum is not None
    assert "ridge" in datum.lower()


def test_detect_existing_or_proposed_existing():
    """Test detecting existing structure"""
    text = "Existing building height: 7m"
    status = _detect_existing_or_proposed(text.lower())
    assert status == "existing"


def test_detect_existing_or_proposed_proposed():
    """Test detecting proposed structure"""
    text = "Proposed ridge height: 8.5m"
    status = _detect_existing_or_proposed(text.lower())
    assert status == "proposed"


def test_detect_existing_or_proposed_unknown():
    """Test unknown status"""
    text = "Building height: 8m"
    status = _detect_existing_or_proposed(text.lower())
    assert status == "unknown"


def test_extract_multiple_measurements():
    """Test extracting multiple measurements from one block"""
    blocks = [
        {"content": "Ridge height 8.5m, eaves height 5.2m, footprint 65 sqm", "page": 1, "index": 0}
    ]
    measurements = extract_measurements(blocks)
    assert len(measurements) == 3
    
    # Check values
    values = [m["value"] for m in measurements]
    assert 8.5 in values
    assert 5.2 in values
    assert 65 in values


def test_measurement_confidence():
    """Test measurement confidence scoring"""
    blocks = [
        {
            "content": "Proposed ridge height from ground level: 8.5m for bedroom 1",
            "page": 1,
            "index": 0
        }
    ]
    measurements = extract_measurements(blocks)
    assert len(measurements) == 1
    
    # Should have high confidence (context + entity + datum + existing/proposed)
    assert measurements[0]["confidence"] >= 0.9


def test_measurement_context_window():
    """Test that measurements use context from surrounding blocks"""
    blocks = [
        {"content": "Building Heights", "page": 1, "index": 0},
        {"content": "8.5m", "page": 1, "index": 1},  # Should detect "height" from previous block
        {"content": "to ridge", "page": 1, "index": 2}
    ]
    measurements = extract_measurements(blocks)
    assert len(measurements) == 1
    assert measurements[0]["context"] == "height"


def test_no_false_positives():
    """Test that non-measurements are not extracted"""
    blocks = [
        {"content": "Telephone: 0121 464 3669", "page": 1, "index": 0},  # Phone number
        {"content": "Reference: PP-14469287", "page": 1, "index": 1},  # Application ref
    ]
    measurements = extract_measurements(blocks)
    # Should not extract phone numbers or application refs as measurements
    assert len(measurements) == 0
