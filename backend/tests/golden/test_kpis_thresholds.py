import json
from pathlib import Path

from scripts.eval_kpis import evaluate_outputs

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"
EXPECTED_CURRENT = FIXTURES_DIR / "expected_current"


def test_kpis_thresholds():
    kpis = evaluate_outputs(EXPECTED_CURRENT)
    baseline = json.loads((EXPECTED_CURRENT / "kpis.json").read_text())

    assert kpis["council_email_false_positive_count"] == 0
    assert kpis["llm_trigger_rate"] <= baseline["llm_trigger_rate"]
