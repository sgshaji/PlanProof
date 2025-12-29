"""
Deterministic field extraction from extracted layout.
"""
from __future__ import annotations
import re
from typing import Any, Dict, List, Tuple, Optional

POSTCODE_RE = re.compile(r"\b([A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2})\b", re.I)
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE_RE = re.compile(r"\b(\+?\d[\d\s().-]{8,}\d)\b")
APPREF_RE = re.compile(r"\b(20\d{6,}[A-Z]{1,3})\b", re.I)
DATE_LIKE = re.compile(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b")

# Strong heuristics for plan sheets
ADDRESS_LIKE = re.compile(r"^\s*\d+\s+[A-Z0-9'’\- ]{4,}$")
PROPOSAL_HINTS = re.compile(r"\b(PROPOS|DEVELOPMENT|CONVERSION|USE|HMO|EXTENSION|LOFT|DORMER)\b", re.I)

LABEL_PATTERNS = {
    "site_address": [r"site address", r"address of site", r"site location"],
    "proposal_description": [r"proposal", r"description of development", r"proposed development", r"what are you proposing"],
    "applicant_name": [r"applicant name", r"name of applicant"],
    "agent_name": [r"agent name", r"name of agent"],
}

DOC_TYPE_HINTS = {
    "application_form": [r"application form", r"planning application", r"town and country planning"],
    "site_plan": [r"location\s*&\s*block\s*plan", r"location plan", r"block plan", r"\b1:1250\b", r"\b1:500\b", r"\b1:2500\b"],
    "drawing": [r"existing", r"proposed", r"elevation", r"floor plan", r"section"],
    "design_statement": [r"design and access statement", r"design\s*&\s*access"],
    "heritage": [r"heritage statement", r"listed building", r"conservation area"],
}


def _norm(s: str) -> str:
    """Normalize whitespace."""
    return re.sub(r"\s+", " ", (s or "")).strip()


def _add_ev(ev: Dict[str, List[Dict[str, Any]]], field: str, page: int, block_id: str, snippet: str):
    """Add evidence entry for a field."""
    ev.setdefault(field, []).append({"page": page, "block_id": block_id, "snippet": _norm(snippet)[:240]})


def _looks_like_allcaps(s: str) -> bool:
    """Check if string is mostly uppercase."""
    letters = [c for c in s if c.isalpha()]
    if len(letters) < 8:
        return False
    upp = sum(1 for c in letters if c.isupper())
    return upp / max(1, len(letters)) > 0.8


def _is_noise(s: str) -> bool:
    """Check if text block is noise (copyright, notes, etc.)."""
    sl = s.lower()
    return any(k in sl for k in ["copyright", "notes:", "scale", "printed on", "os 1000"])


def looks_like_phone(s: str) -> bool:
    """Check if string looks like a phone number (not a date)."""
    # Reject if it matches date pattern
    if DATE_LIKE.search(s):
        return False
    # Phone should have digits, not just date separators
    digits = sum(1 for c in s if c.isdigit())
    if digits < 8:  # Too short
        return False
    return True


def pick_site_address(blocks: List[Dict[str, Any]]) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """Pick site address from plan sheet (first address-like line)."""
    for b in blocks[:60]:
        t = _norm(b.get("content", b.get("text", "")))
        if not t or _is_noise(t):
            continue
        if ADDRESS_LIKE.match(t):
            return t, b
    return None, None


def pick_proposed_use(blocks: List[Dict[str, Any]]) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """Pick proposed use from plan sheet (all caps sentence with proposal keywords)."""
    for b in blocks[:80]:
        t = _norm(b.get("content", b.get("text", "")))
        if not t or _is_noise(t):
            continue
        if PROPOSAL_HINTS.search(t) and (len(t) >= 20) and (_looks_like_allcaps(t) or t.endswith(".")):
            return t, b
    return None, None


def classify_document(text_blocks: List[Dict[str, Any]]) -> str:
    """Classify document type from text content."""
    text = " ".join(_norm(b.get("content", b.get("text", ""))) for b in text_blocks[:200]).lower()
    best = ("unknown", 0)
    for dtype, hints in DOC_TYPE_HINTS.items():
        score = sum(1 for h in hints if re.search(h, text))
        if score > best[1]:
            best = (dtype, score)
    return best[0]


def extract_by_label(text_blocks: List[Dict[str, Any]], label_patterns: List[str]) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """Extract field value by looking for label patterns."""
    # look for label in a block, then take same block after ":" or next 1–2 blocks
    for i, b in enumerate(text_blocks):
        t = _norm(b.get("content", b.get("text", "")))
        tl = t.lower()
        if any(re.search(p, tl) for p in label_patterns):
            # try "Label: value"
            m = re.split(r":", t, maxsplit=1)
            if len(m) == 2 and _norm(m[1]):
                return _norm(m[1]), b
            # else take next blocks
            nxt = []
            for j in range(1, 4):
                if i + j < len(text_blocks):
                    nxt_txt = _norm(text_blocks[i+j].get("content", text_blocks[i+j].get("text", "")))
                    if nxt_txt:
                        nxt.append(nxt_txt)
                if len(" ".join(nxt)) > 20:
                    break
            if nxt:
                return _norm(" ".join(nxt)), b
    return None, None


def map_fields(extracted_layout: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract structured fields from extracted layout.
    
    Returns:
        {
            "fields": {field_name: value, ...},
            "evidence_index": {field_name: [{"page": int, "block_id": str, "snippet": str}, ...]}
        }
    """
    blocks = extracted_layout.get("text_blocks", []) or []
    fields: Dict[str, Any] = {}
    evidence: Dict[str, List[Dict[str, Any]]] = {}

    # document type
    dtype = classify_document(blocks)
    fields["document_type"] = dtype

    # app ref
    for b in blocks[:400]:
        t = b.get("content", b.get("text", ""))
        m = APPREF_RE.search(t)
        if m:
            fields["application_ref"] = m.group(1).upper()
            page_num = int(b.get("page_number", b.get("page", 0)))
            block_id = f"p{page_num}b{b.get('index', '')}"
            _add_ev(evidence, "application_ref", page_num, block_id, t)
            break

    # site_address - use strong heuristic first
    if "site_address" not in fields:
        addr, src = pick_site_address(blocks)
        if addr:
            fields["site_address"] = addr
            page_num = int(src.get("page_number", src.get("page", 0)))
            block_id = f"p{page_num}b{src.get('index', '')}"
            _add_ev(evidence, "site_address", page_num, block_id, src.get("content", src.get("text", "")))
    
    # proposed_use - use strong heuristic first
    if "proposed_use" not in fields:
        prop, src = pick_proposed_use(blocks)
        if prop:
            fields["proposed_use"] = prop
            page_num = int(src.get("page_number", src.get("page", 0)))
            block_id = f"p{page_num}b{src.get('index', '')}"
            _add_ev(evidence, "proposed_use", page_num, block_id, src.get("content", src.get("text", "")))

    # labeled fields (fallback for other fields)
    for field, pats in LABEL_PATTERNS.items():
        if field not in fields:  # Skip if already found
            val, src = extract_by_label(blocks, pats)
            if val:
                fields[field] = val
                page_num = int(src.get("page_number", src.get("page", 0)))
                block_id = f"p{page_num}b{src.get('index', '')}"
                _add_ev(evidence, field, page_num, block_id, src.get("content", src.get("text", "")))

    # regex fields (email/phone/postcode)
    for b in blocks[:400]:
        t = b.get("content", b.get("text", ""))
        if "applicant_email" not in fields:
            m = EMAIL_RE.search(t)
            if m:
                fields["applicant_email"] = m.group(0)
                page_num = int(b.get("page_number", b.get("page", 0)))
                block_id = f"p{page_num}b{b.get('index', '')}"
                _add_ev(evidence, "applicant_email", page_num, block_id, t)
        if "applicant_phone" not in fields:
            m = PHONE_RE.search(t)
            if m and looks_like_phone(m.group(1)) and len(_norm(m.group(1))) >= 9:
                fields["applicant_phone"] = _norm(m.group(1))
                page_num = int(b.get("page_number", b.get("page", 0)))
                block_id = f"p{page_num}b{b.get('index', '')}"
                _add_ev(evidence, "applicant_phone", page_num, block_id, t)
        if "postcode" not in fields:
            m = POSTCODE_RE.search(t)
            if m:
                fields["postcode"] = m.group(1).upper()
                page_num = int(b.get("page_number", b.get("page", 0)))
                block_id = f"p{page_num}b{b.get('index', '')}"
                _add_ev(evidence, "postcode", page_num, block_id, t)


    return {"fields": fields, "evidence_index": evidence}

