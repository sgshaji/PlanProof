from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class EvidenceExpectation:
    # e.g. "application_form", "site_plan", "heritage_statement"
    source_types: List[str]
    # optional hints: keywords to search in extracted text
    keywords: List[str]
    # how strong evidence must be
    min_confidence: float = 0.6

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Rule:
    rule_id: str
    title: str
    description: str
    required_fields: List[str]
    evidence: EvidenceExpectation
    severity: str = "error"  # error|warning
    applies_to: List[str] = None  # e.g. ["new_build", "amendment"]
    tags: List[str] = None
    required_fields_any: bool = False  # If True, any field satisfies (OR logic), else all required (AND logic)
    rule_category: str = "FIELD_REQUIRED"  # DOCUMENT_REQUIRED, CONSISTENCY, MODIFICATION, SPATIAL, FIELD_REQUIRED

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # normalize None lists
        d["applies_to"] = d["applies_to"] or []
        d["tags"] = d["tags"] or []
        d["evidence"] = self.evidence.to_dict()
        return d


_RULE_ID_PATTERNS = [
    re.compile(r"^\s*(?:RULE|R|REQ)\s*[-:]?\s*(\d+(?:\.\d+)*)\s*[:\-]\s*(.+?)\s*$", re.I),
    re.compile(r"^\s*(\d+(?:\.\d+)*)\s*[\)\.\-:]\s*(.+?)\s*$", re.I),
]

_FIELD_LINE = re.compile(r"^\s*(?:Required fields?|Fields?)\s*[:\-]\s*(.+)\s*$", re.I)
_EVID_LINE = re.compile(r"^\s*(?:Evidence|Documents?|Doc types?)\s*[:\-]\s*(.+)\s*$", re.I)
_SEV_LINE = re.compile(r"^\s*(?:Severity|Level)\s*[:\-]\s*(error|warning)\s*$", re.I)
_APPLIES_LINE = re.compile(r"^\s*(?:Applies to)\s*[:\-]\s*(.+)\s*$", re.I)
_TAGS_LINE = re.compile(r"^\s*(?:Tags?)\s*[:\-]\s*(.+)\s*$", re.I)
_KEYWORDS_LINE = re.compile(r"^\s*(?:Keywords?)\s*[:\-]\s*(.+)\s*$", re.I)
_CATEGORY_LINE = re.compile(r"^\s*(?:Category|Rule category)\s*[:\-]\s*(DOCUMENT_REQUIRED|CONSISTENCY|MODIFICATION|SPATIAL|FIELD_REQUIRED)\s*$", re.I)


def _split_csvish(s: str) -> List[str]:
    parts = re.split(r"[,\;\|]+", s)
    return [p.strip() for p in parts if p.strip()]


def _match_rule_header(line: str) -> Optional[Tuple[str, str]]:
    for pat in _RULE_ID_PATTERNS:
        m = pat.match(line)
        if m:
            rid = m.group(1).strip()
            title = m.group(2).strip()
            return rid, title
    return None


def parse_validation_requirements(md_path: str | Path) -> List[Rule]:
    """
    Robust-ish Markdown parser:
    - detects rule blocks by lines that look like "RULE-1: Title" or "1.2 - Title"
    - consumes following lines until next rule header
    - extracts metadata from labelled lines (Required fields:, Evidence:, Severity:, etc.)
    - everything else becomes description text
    """
    md_path = Path(md_path)
    text = md_path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()

    rules: List[Rule] = []
    cur_id: Optional[str] = None
    cur_title: str = ""
    desc_lines: List[str] = []
    req_fields: List[str] = []
    evidence_sources: List[str] = []
    evidence_keywords: List[str] = []
    severity: str = "error"
    applies_to: List[str] = []
    tags: List[str] = []
    rule_category: str = "FIELD_REQUIRED"

    def flush():
        nonlocal cur_id, cur_title, desc_lines, req_fields, evidence_sources, evidence_keywords, severity, applies_to, tags, rule_category
        if not cur_id:
            return
        description = "\n".join([l.strip() for l in desc_lines if l.strip()]).strip()

        # if author forgot to specify sources, keep generic "unknown"
        sources = evidence_sources or ["unknown"]
        ev = EvidenceExpectation(source_types=sources, keywords=evidence_keywords or [], min_confidence=0.6)

        rules.append(
            Rule(
                rule_id=f"R{cur_id}",
                title=cur_title or f"Rule {cur_id}",
                description=description,
                required_fields=req_fields,
                evidence=ev,
                severity=severity,
                applies_to=applies_to,
                tags=tags,
                rule_category=rule_category,
            )
        )

        # reset
        cur_id = None
        cur_title = ""
        desc_lines = []
        req_fields = []
        evidence_sources = []
        evidence_keywords = []
        severity = "error"
        applies_to = []
        tags = []
        rule_category = "FIELD_REQUIRED"

    for line in lines:
        hdr = _match_rule_header(line)
        if hdr:
            flush()
            cur_id, cur_title = hdr
            continue

        if not cur_id:
            continue  # ignore preamble

        # metadata lines
        m = _FIELD_LINE.match(line)
        if m:
            req_fields = _split_csvish(m.group(1))
            continue
        m = _EVID_LINE.match(line)
        if m:
            evidence_sources = _split_csvish(m.group(1))
            continue
        m = _SEV_LINE.match(line)
        if m:
            severity = m.group(1).lower()
            continue
        m = _APPLIES_LINE.match(line)
        if m:
            applies_to = _split_csvish(m.group(1))
            continue
        m = _TAGS_LINE.match(line)
        if m:
            tags = _split_csvish(m.group(1))
            continue
        m = _KEYWORDS_LINE.match(line)
        if m:
            evidence_keywords = _split_csvish(m.group(1))
            continue
        m = _CATEGORY_LINE.match(line)
        if m:
            rule_category = m.group(1).upper()
            continue

        desc_lines.append(line)

    flush()
    return rules


def write_rule_catalog_json(md_path: str | Path, out_path: str | Path) -> Dict[str, Any]:
    rules = parse_validation_requirements(md_path)
    payload = {
        "version": "1.0",
        "source": str(md_path),
        "rule_count": len(rules),
        "rules": [r.to_dict() for r in rules],
    }
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload

