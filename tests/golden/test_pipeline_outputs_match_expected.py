import json
from pathlib import Path

import pytest

from planproof.pipeline.field_mapper import map_fields
from planproof.pipeline.validate import load_rule_catalog, validate_extraction

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"
LAYOUTS_DIR = FIXTURES_DIR / "layouts"
EXPECTED_CURRENT = FIXTURES_DIR / "expected_current"
EXPECTED_TARGET = FIXTURES_DIR / "expected_target"

DROP_KEYS = {"created_at", "updated_at", "run_id", "timestamp"}


def _load_json(path: Path):
    return json.loads(path.read_text())


def _normalize(obj):
    if isinstance(obj, dict):
        return {k: _normalize(v) for k, v in obj.items() if k not in DROP_KEYS}
    if isinstance(obj, list):
        normalized_items = [_normalize(item) for item in obj]
        return sorted(normalized_items, key=lambda item: json.dumps(item, sort_keys=True))
    return obj


def _build_extraction(doc_id: int):
    layout = _load_json(LAYOUTS_DIR / f"layout_{doc_id}.json")
    mapped = map_fields(layout)
    return {
        "fields": mapped["fields"],
        "evidence_index": mapped["evidence_index"],
        "metadata": layout.get("metadata", {}),
        "text_blocks": layout.get("text_blocks", []),
        "tables": layout.get("tables", []),
        "page_anchors": layout.get("page_anchors", {}),
    }


def _build_validation(extraction, doc_id: int):
    rules = load_rule_catalog(Path("artefacts/rule_catalog.json"))
    return validate_extraction(
        extraction,
        rules,
        context={"document_id": doc_id, "submission_id": doc_id},
        write_to_tables=False,
    )


def _assert_match(actual, expected):
    assert _normalize(actual) == _normalize(expected)


@pytest.mark.parametrize("doc_id", [81, 82, 83])
def test_golden_current_extraction_matches_expected(doc_id):
    extraction = _build_extraction(doc_id)
    expected = _load_json(EXPECTED_CURRENT / f"extraction_{doc_id}.json")
    _assert_match(extraction, expected)


@pytest.mark.parametrize("doc_id", [81, 82, 83])
def test_golden_current_validation_matches_expected(doc_id):
    extraction = _build_extraction(doc_id)
    validation = _build_validation(extraction, doc_id)
    expected = _load_json(EXPECTED_CURRENT / f"validation_{doc_id}.json")
    _assert_match(validation, expected)


@pytest.mark.parametrize("doc_id", [81, 82, 83])
def test_golden_target_extraction_matches_expected(doc_id):
    if doc_id == 82:
        pytest.xfail("Target outputs are pending rule fixes.")
    extraction = _build_extraction(doc_id)
    expected = _load_json(EXPECTED_TARGET / f"extraction_{doc_id}.json")
    _assert_match(extraction, expected)


@pytest.mark.parametrize("doc_id", [81, 82, 83])
def test_golden_target_validation_matches_expected(doc_id):
    if doc_id == 82:
        pytest.xfail("Target outputs are pending rule fixes.")
    extraction = _build_extraction(doc_id)
    validation = _build_validation(extraction, doc_id)
    expected = _load_json(EXPECTED_TARGET / f"validation_{doc_id}.json")
    _assert_match(validation, expected)
