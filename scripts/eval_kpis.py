from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from planproof.pipeline.llm_gate import should_trigger_llm


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text())


def evaluate_outputs(outputs_dir: Path) -> Dict[str, Any]:
    extraction_files = sorted(outputs_dir.glob("extraction_*.json"))
    if not extraction_files:
        raise FileNotFoundError(f"No extraction_*.json files found in {outputs_dir}")

    total_docs = 0
    app_ref_docs = 0
    app_ref_found = 0
    council_email_hits = 0
    llm_triggers = 0
    validation_by_doc_type: Dict[str, Dict[str, int]] = {}

    for extraction_path in extraction_files:
        total_docs += 1
        extraction = _load_json(extraction_path)
        fields = extraction.get("fields", {})
        doc_type = fields.get("document_type", "unknown")

        if doc_type == "application_form":
            app_ref_docs += 1
            if fields.get("application_ref"):
                app_ref_found += 1

        applicant_email = fields.get("applicant_email", "") or ""
        if applicant_email.lower().endswith("birmingham.gov.uk"):
            council_email_hits += 1

        validation_path = outputs_dir / extraction_path.name.replace("extraction_", "validation_")
        if validation_path.exists():
            validation = _load_json(validation_path)
            if should_trigger_llm(validation, extraction):
                llm_triggers += 1

            summary = validation.get("summary", {})
            doc_stats = validation_by_doc_type.setdefault(doc_type, {"total": 0, "pass": 0})
            doc_stats["total"] += 1
            if summary.get("needs_review", 0) == 0 and summary.get("fail", 0) == 0:
                doc_stats["pass"] += 1

    app_ref_rate = (app_ref_found / app_ref_docs) if app_ref_docs else 0.0
    llm_trigger_rate = llm_triggers / total_docs if total_docs else 0.0

    validation_pass_rate = {
        doc_type: (stats["pass"] / stats["total"] if stats["total"] else 0.0)
        for doc_type, stats in validation_by_doc_type.items()
    }

    return {
        "total_docs": total_docs,
        "application_ref_extracted_rate": app_ref_rate,
        "council_email_false_positive_count": council_email_hits,
        "llm_trigger_rate": llm_trigger_rate,
        "validation_pass_rate_by_doc_type": validation_pass_rate,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate pipeline KPIs from outputs.")
    parser.add_argument("outputs_dir", type=Path, help="Directory containing extraction_*.json outputs")
    args = parser.parse_args()

    kpis = evaluate_outputs(args.outputs_dir)
    print(json.dumps(kpis, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
