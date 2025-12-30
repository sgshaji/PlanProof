"""
Deterministic field extraction from extracted layout.
"""
from __future__ import annotations
import re
from typing import Any, Dict, List, Tuple, Optional

POSTCODE_RE = re.compile(r"\b([A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2})\b", re.I)
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE_RE = re.compile(r"\b(\+?\d[\d\s().-]{8,}\d)\b")
# Application ref patterns: PP-\d{6,} or 20\d{6,}[A-Z]{1,3}
APPREF_RE = re.compile(r"\b(PP-\d{6,}|20\d{6,}[A-Z]{1,3})\b", re.I)
DATE_LIKE = re.compile(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b")

# Strong heuristics for plan sheets
ADDRESS_LIKE = re.compile(r"^\s*\d+\s+[A-Z0-9'’\- ]{4,}$")
PROPOSAL_HINTS = re.compile(r"\b(PROPOS|DEVELOPMENT|CONVERSION|USE|HMO|EXTENSION|LOFT|DORMER)\b", re.I)

LABEL_PATTERNS = {
    "site_address": [r"site address", r"address of site", r"site location"],
    "proposal_description": [
        r"please describe the building\(s\) to be demolished",
        r"please describe.*proposal",
        r"please describe.*development",
        r"please describe.*works",
        r"brief description.*development",
        r"description of.*proposal",
        r"what are you proposing"
    ],
    "applicant_name": [r"applicant name", r"name of applicant", r"first name", r"surname"],
    "agent_name": [r"agent name", r"name of agent"],
    "proposed_use": [r"i/we hereby apply for prior approval", r"prior approval for", r"declaration"],
}

DOC_TYPE_HINTS = {
    "application_form": [
        r"application form", 
        r"planning application", 
        r"town and country planning",
        r"planning portal reference",  # Doc 82: "Planning Portal Reference:"
        r"application to determine if prior approval",  # Prior Approval forms
        r"i/we hereby apply for prior approval",  # Prior Approval declaration
        r"prior approval"
    ],
    "site_notice": [
        r"statement of display of a site notice",
        r"site notice of application",
        r"site notice",
        r"notice of application"
    ],
    "site_plan": [
        r"location\s*&\s*block\s*plan", 
        r"location plan", 
        r"block plan", 
        r"\b1:1250\b", 
        r"\b1:500\b", 
        r"\b1:2500\b"
    ],
    "drawing": [r"existing", r"proposed", r"elevation", r"floor plan", r"section"],
    "design_statement": [r"design and access statement", r"design\s*&\s*access"],
    "heritage": [r"heritage statement", r"listed building", r"conservation area"],
}


def _norm(s: str) -> str:
    """Normalize whitespace."""
    return re.sub(r"\s+", " ", (s or "")).strip()


def _add_ev(ev: Dict[str, List[Dict[str, Any]]], field: str, page: int, block_id: str, snippet: str, 
            confidence: float = 0.5, source_doc_type: Optional[str] = None, extraction_method: str = "heuristic",
            bbox: Optional[Dict[str, float]] = None):
    """Add evidence entry for a field with confidence, source, method, and bbox."""
    evidence_entry = {
        "page": page, 
        "block_id": block_id, 
        "snippet": _norm(snippet)[:240],
        "confidence": confidence,
        "source_doc_type": source_doc_type,
        "extraction_method": extraction_method  # regex, layout, label, llm, manual
    }
    if bbox:
        evidence_entry["bbox"] = bbox
    ev.setdefault(field, []).append(evidence_entry)


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
    return any(k in sl for k in ["copyright", "notes:", "scale", "printed on", "os 1000", 
                                  "disclaimer", "this drawing", "for information only"])

def _is_council_contact(s: str) -> bool:
    """Check if text contains council contact information (not applicant)."""
    sl = s.lower()
    council_indicators = [
        "birmingham.gov.uk", "planning.registration", "council", "local authority",
        "planning department", "planning@", "0121 464", "po box"
    ]
    return any(indicator in sl for indicator in council_indicators)

def _is_in_site_location_section(blocks: List[Dict[str, Any]], block_index: int) -> bool:
    """Check if block is in a 'Site Location' section (higher confidence)."""
    # Look backwards for section headers
    for i in range(max(0, block_index - 10), block_index):
        t = _norm(blocks[i].get("content", blocks[i].get("text", ""))).lower()
        if any(header in t for header in ["site location", "site address", "address of site", 
                                           "location of site", "property address"]):
            return True
    return False


def looks_like_phone(s: str) -> bool:
    """Check if string looks like a phone number (not a date)."""
    return not DATE_LIKE.search(s)


def extract_site_address_from_section(blocks: List[Dict[str, Any]]) -> Tuple[Optional[str], Optional[Dict[str, Any]], float]:
    """
    Extract site address from structured "Site location" section.
    Looks for Property Name, Address Line 1, Address Line 2, Town/City, Postcode fields.
    """
    address_parts = []
    start_idx = None
    
    # Find "Site location" or "Site address" section header
    for i, b in enumerate(blocks[:200]):
        t = _norm(b.get("content", b.get("text", ""))).lower()
        if any(header in t for header in ["site location", "site address", "address of site", "property address"]):
            start_idx = i
            break
    
    if start_idx is None:
        return None, None, 0.0
    
    # Collect address components from next 10-15 blocks after header
    property_name = None
    address_line1 = None
    address_line2 = None
    town_city = None
    postcode = None
    
    for i in range(start_idx + 1, min(start_idx + 20, len(blocks))):
        b = blocks[i]
        t = _norm(b.get("content", b.get("text", "")))
        tl = t.lower()
        
        # Skip empty or noise
        if not t or _is_noise(t) or len(t) < 2:
            continue
        
        # Property Name
        if "property name" in tl and not property_name:
            parts = re.split(r":", t, maxsplit=1)
            if len(parts) == 2:
                property_name = _norm(parts[1])
        
        # Address Line 1
        if "address line 1" in tl or ("address" in tl and "line" in tl and "1" in tl):
            parts = re.split(r":", t, maxsplit=1)
            if len(parts) == 2:
                address_line1 = _norm(parts[1])
        
        # Address Line 2
        if "address line 2" in tl or ("address" in tl and "line" in tl and "2" in tl):
            parts = re.split(r":", t, maxsplit=1)
            if len(parts) == 2:
                address_line2 = _norm(parts[1])
        
        # Town/City
        if "town" in tl or "city" in tl:
            parts = re.split(r":", t, maxsplit=1)
            if len(parts) == 2:
                town_city = _norm(parts[1])
        
        # Postcode
        if "postcode" in tl:
            parts = re.split(r":", t, maxsplit=1)
            if len(parts) == 2:
                postcode_match = POSTCODE_RE.search(parts[1])
                if postcode_match:
                    postcode = postcode_match.group(1).upper()
        
        # Also try to extract values without labels (next block after label)
        if i > start_idx + 1:
            prev_t = _norm(blocks[i-1].get("content", blocks[i-1].get("text", ""))).lower()
            if "property name" in prev_t and not property_name:
                property_name = t
            elif ("address line 1" in prev_t or "address" in prev_t) and not address_line1:
                address_line1 = t
            elif "address line 2" in prev_t and not address_line2:
                address_line2 = t
            elif ("town" in prev_t or "city" in prev_t) and not town_city:
                town_city = t
            elif "postcode" in prev_t and not postcode:
                postcode_match = POSTCODE_RE.search(t)
                if postcode_match:
                    postcode = postcode_match.group(1).upper()
    
    # Build full address string
    address_parts = []
    if property_name:
        address_parts.append(property_name)
    if address_line1:
        address_parts.append(address_line1)
    if address_line2:
        address_parts.append(address_line2)
    if town_city:
        address_parts.append(town_city)
    if postcode:
        address_parts.append(postcode)
    
    if address_parts:
        full_address = ", ".join(address_parts)
        # Use the block containing the section header as source
        source_block = blocks[start_idx] if start_idx < len(blocks) else blocks[0]
        return full_address, source_block, 0.95  # High confidence for structured extraction
    
    return None, None, 0.0


def extract_address_from_demolition_pattern(blocks: List[Dict[str, Any]]) -> Tuple[Optional[str], Optional[Dict[str, Any]], float]:
    """
    Extract site address from "demolition of ..." pattern (for site notices).
    Pattern: "demolition of Unit M, Dorset Road, Saltley Business Park, Saltley, Birmingham, B8 1BG"
    """
    for i, b in enumerate(blocks[:100]):
        t = _norm(b.get("content", b.get("text", "")))
        tl = t.lower()
        
        if "demolition of" in tl or "demolition" in tl:
            # Try to extract from "demolition of" to first postcode
            match = re.search(r"demolition\s+of\s+(.+?)(?:\s+([A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}))", t, re.I)
            if match:
                address_part = match.group(1).strip()
                postcode_part = match.group(2).upper() if match.lastindex >= 2 else None
                
                # Clean up address (remove trailing commas, normalize)
                address_part = re.sub(r",\s*$", "", address_part)
                if postcode_part:
                    full_address = f"{address_part}, {postcode_part}"
                else:
                    full_address = address_part
                
                if len(full_address) > 10:  # Must be substantial
                    return full_address, b, 0.85
    
    return None, None, 0.0


def pick_site_address(blocks: List[Dict[str, Any]]) -> Tuple[Optional[str], Optional[Dict[str, Any]], float]:
    """
    Pick site address with multiple strategies:
    1. Structured extraction from "Site location" section (highest confidence)
    2. Pattern extraction from "demolition of" text (for site notices)
    3. Heuristic extraction from plan sheets (lowest confidence, filtered for noise)
    """
    # Strategy 1: Structured extraction from Site Location section (best for application forms)
    addr, block, conf = extract_site_address_from_section(blocks)
    if addr and conf >= 0.9:
        return addr, block, conf
    
    # Strategy 2: Extract from "demolition of" pattern (for site notices)
    addr, block, conf = extract_address_from_demolition_pattern(blocks)
    if addr and conf >= 0.8:
        return addr, block, conf
    
    # Strategy 3: Heuristic extraction (for plan sheets, but filter noise carefully)
    best_match = None
    best_block = None
    best_confidence = 0.0
    
    for i, b in enumerate(blocks[:100]):
        t = _norm(b.get("content", b.get("text", "")))
        if not t or _is_noise(t):
            continue
        
        # Skip if it's a disclaimer or too short
        if len(t) < 5 or "disclaimer" in t.lower() or "for information" in t.lower():
            continue
        
        # Skip if it looks like a map grid reference (just numbers like "4 2447")
        if re.match(r"^\s*\d+\s+\d+\s*$", t):
            continue
        
        # Skip if it's just numbers (grid coordinates)
        if re.match(r"^\s*\d+\s*$", t):
            continue
        
        # Check if it's in Site Location section (high confidence)
        in_site_section = _is_in_site_location_section(blocks, i)
        
        # Check if it matches address pattern
        if ADDRESS_LIKE.match(t):
            confidence = 0.7 if in_site_section else 0.4
            if confidence > best_confidence:
                best_match = t
                best_block = b
                best_confidence = confidence
        # Also try labeled extraction
        elif any(label in t.lower() for label in ["site address", "address of site", "site location"]):
            # Try to extract value after colon
            parts = re.split(r":", t, maxsplit=1)
            if len(parts) == 2 and _norm(parts[1]):
                val = _norm(parts[1])
                if len(val) > 5:  # Must be substantial
                    confidence = 0.8 if in_site_section else 0.6
                    if confidence > best_confidence:
                        best_match = val
                        best_block = b
                        best_confidence = confidence
    
    if best_match and best_confidence > 0.3:
        return best_match, best_block, best_confidence
    
    return None, None, 0.0


def pick_proposed_use(blocks: List[Dict[str, Any]]) -> Tuple[Optional[str], Optional[Dict[str, Any]], float]:
    """Pick proposed use from plan sheet (all caps sentence with proposal keywords)."""
    for b in blocks[:80]:
        t = _norm(b.get("content", b.get("text", "")))
        if not t or _is_noise(t):
            continue
        if PROPOSAL_HINTS.search(t) and (len(t) >= 20) and (_looks_like_allcaps(t) or t.endswith(".")):
            confidence = 0.7 if len(t) >= 30 else 0.5
            return t, b, confidence
    return None, None, 0.0


def classify_document(text_blocks: List[Dict[str, Any]]) -> str:
    """Classify document type from text content."""
    text = " ".join(_norm(b.get("content", b.get("text", ""))) for b in text_blocks[:200]).lower()
    
    # Priority order: check more specific types first
    # application_form and site_notice should be checked before generic types
    priority_order = ["application_form", "site_notice", "site_plan", "design_statement", "heritage", "drawing"]
    
    best = ("unknown", 0)
    for dtype in priority_order:
        if dtype not in DOC_TYPE_HINTS:
            continue
        hints = DOC_TYPE_HINTS[dtype]
        score = sum(1 for h in hints if re.search(h, text))
        if score > best[1]:
            best = (dtype, score)
    
    # If no match found, check remaining types
    if best[1] == 0:
        for dtype, hints in DOC_TYPE_HINTS.items():
            if dtype not in priority_order:
                score = sum(1 for h in hints if re.search(h, text))
                if score > best[1]:
                    best = (dtype, score)
    
    return best[0]


# Form field labels to filter out (not actual values)
FORM_LABEL_NOISE = [
    r"\bfirst\s*name\b", r"\bsurname\b", r"\blast\s*name\b", r"\bmiddle\s*name\b",
    r"\btitle\b", r"\bmr\b", r"\bmrs\b", r"\bmiss\b", r"\bms\b", r"\bdr\b",
    r"\bunselected:\s*yes\b", r"\b:selected:\s*no\b", r"\bunselected\b", r"\b:selected\b"
]

def _is_form_label_noise(text: str) -> bool:
    """Check if text is just form labels, not actual data."""
    tl = text.lower().strip()
    # Check for common form label patterns
    return any(re.search(pattern, tl, re.I) for pattern in FORM_LABEL_NOISE)

def _clean_extracted_value(value: str, field_name: str = "") -> str:
    """Clean extracted value by removing form labels."""
    # Remove form label words
    cleaned = value
    for pattern in FORM_LABEL_NOISE:
        cleaned = re.sub(pattern, "", cleaned, flags=re.I)
    
    # For names, clean up common patterns
    if "name" in field_name:
        # Remove standalone title words
        cleaned = re.sub(r"\b(Mr|Mrs|Miss|Ms|Dr)\.?\s*", "", cleaned, flags=re.I)
        # Remove "Surname" or "First name" if they appear alone
        if re.match(r"^(surname|first\s*name|last\s*name)$", cleaned.strip(), re.I):
            return ""  # Return empty if only label remains
    
    # For descriptions, remove checkbox states
    if "description" in field_name or "proposal" in field_name:
        # Remove checkbox patterns like "unselected: Yes :selected: No"
        cleaned = re.sub(r"\bunselected:\s*\w+\s*:?selected:\s*\w+\b", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\b:?selected:\s*\w+\b", "", cleaned, flags=re.I)
        cleaned = re.sub(r"\bunselected:\s*\w+\b", "", cleaned, flags=re.I)
    
    return _norm(cleaned).strip()

def extract_by_label(text_blocks: List[Dict[str, Any]], label_patterns: List[str], field_name: str = "") -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """Extract field value by looking for label patterns, with form label filtering."""
    # look for label in a block, then take same block after ":" or next 1–2 blocks
    for i, b in enumerate(text_blocks):
        t = _norm(b.get("content", b.get("text", "")))
        tl = t.lower()
        if any(re.search(p, tl) for p in label_patterns):
            # For description fields, skip blocks that are questions about the proposal
            # (not the proposal itself)
            if "description" in field_name or "proposal" in field_name:
                # Skip questions like "Does the proposal involve..."
                if tl.startswith("does the proposal") or tl.startswith("is the proposal"):
                    continue
                # Skip checkbox-heavy blocks (more than 2 checkbox patterns)
                checkbox_count = len(re.findall(r":selected:|:unselected:", t))
                if checkbox_count > 1:
                    continue
            
            # try "Label: value"
            m = re.split(r":", t, maxsplit=1)
            if len(m) == 2 and _norm(m[1]):
                value = _clean_extracted_value(_norm(m[1]), field_name)
                if value and not _is_form_label_noise(value):
                    return value, b
            
            # else take next blocks
            # For description fields, gather more content (up to 200 chars)
            max_blocks = 8 if ("description" in field_name or "proposal" in field_name) else 4
            target_length = 150 if ("description" in field_name or "proposal" in field_name) else 20
            
            nxt = []
            for j in range(1, max_blocks):
                if i + j < len(text_blocks):
                    nxt_txt = _norm(text_blocks[i+j].get("content", text_blocks[i+j].get("text", "")))
                    # Skip form labels, empty blocks, and checkbox-heavy blocks
                    if nxt_txt and not _is_form_label_noise(nxt_txt):
                        # For descriptions, skip blocks with checkboxes
                        if "description" in field_name or "proposal" in field_name:
                            if ":selected:" in nxt_txt or ":unselected:" in nxt_txt:
                                continue
                        nxt.append(nxt_txt)
                if len(" ".join(nxt)) >= target_length:
                    break
            if nxt:
                value = _clean_extracted_value(_norm(" ".join(nxt)), field_name)
                if value and len(value) > 10:  # Require substantial content for descriptions
                    return value, b
    return None, None


def detect_application_type(blocks: List[Dict[str, Any]]) -> str:
    """Detect application type from document content."""
    text_sample = " ".join([_norm(b.get("content", b.get("text", ""))) for b in blocks[:50]]).lower()
    
    # Check for prior approval
    if any(pattern in text_sample for pattern in ["prior approval", "i/we hereby apply for prior approval", "part 11"]):
        return "prior_approval"
    
    # Check for householder
    if any(pattern in text_sample for pattern in ["householder", "single dwelling", "home extension"]):
        return "householder"
    
    # Check for listed building
    if any(pattern in text_sample for pattern in ["listed building", "listed building consent"]):
        return "listed_building"
    
    # Check for advertisement
    if "advertisement" in text_sample:
        return "advertisement"
    
    # Check for full planning
    if "full planning" in text_sample or "planning application" in text_sample:
        return "full_planning"
    
    # Default
    return "unknown"


def classify_plan_type(blocks: List[Dict[str, Any]]) -> Optional[str]:
    """
    Classify plan drawing type: location_plan, site_plan, block_plan, 
    floor_plan, elevation, section, etc.
    """
    text_sample = " ".join([_norm(b.get("content", b.get("text", ""))) for b in blocks[:150]]).lower()
    
    # Check for location plan (typically 1:1250 or 1:2500 scale)
    if any(pattern in text_sample for pattern in ["location plan", "1:1250", "1:2500"]):
        return "location_plan"
    
    # Check for block plan (typically 1:500 scale)
    if any(pattern in text_sample for pattern in ["block plan", "1:500"]):
        return "block_plan"
    
    # Check for site plan
    if "site plan" in text_sample:
        return "site_plan"
    
    # Check for floor plan
    if any(pattern in text_sample for pattern in ["floor plan", "ground floor", "first floor"]):
        return "floor_plan"
    
    # Check for elevations
    if any(pattern in text_sample for pattern in ["elevation", "front elevation", "rear elevation", "side elevation"]):
        return "elevation"
    
    # Check for sections
    if any(pattern in text_sample for pattern in ["section", "cross section", "longitudinal section"]):
        return "section"
    
    return None


def extract_scale_ratio(blocks: List[Dict[str, Any]]) -> Tuple[Optional[str], Optional[Dict[str, Any]], float]:
    """
    Extract scale ratio from plan drawings.
    Common scales: 1:100, 1:200, 1:500, 1:1250, 1:2500, etc.
    """
    # Scale pattern: 1:digits or @ 1:digits or Scale 1:digits
    scale_pattern = re.compile(r"(?:scale|@)?\s*1\s*:\s*(\d+)", re.I)
    
    for b in blocks[:150]:  # Check first 150 blocks
        t = _norm(b.get("content", b.get("text", "")))
        m = scale_pattern.search(t)
        if m:
            scale_value = m.group(1)
            scale_ratio = f"1:{scale_value}"
            
            # Common architectural scales for validation
            common_scales = ["1:100", "1:200", "1:500", "1:1250", "1:2500", "1:50", "1:20"]
            confidence = 0.9 if scale_ratio in common_scales else 0.7
            
            return scale_ratio, b, confidence
    
    return None, None, 0.0


def detect_north_arrow(blocks: List[Dict[str, Any]]) -> Tuple[bool, Optional[Dict[str, Any]], float]:
    """
    Detect presence of north arrow indicator.
    Looks for text like "N", "North", "↑ N", "Grid North", or north arrow labels.
    """
    north_indicators = [
        r"\bn\b(?!\w)",  # Standalone "N" (not part of another word) - lowercase for tl matching
        r"north\s*arrow",
        r"north\s*point",
        r"grid\s*north",  # OS maps often have "Grid North"
        r"↑\s*n",  # Arrow + N (lowercase for matching)
        r"⬆\s*n",
    ]
    
    for b in blocks:
        t = _norm(b.get("content", b.get("text", "")))
        tl = t.lower()
        
        # Check for north indicators
        for pattern in north_indicators:
            if re.search(pattern, tl):
                # Additional validation: Should be short text (not "Northern")
                if len(t) <= 20 and "north" in tl:
                    return True, b, 0.8
                elif len(t) <= 5 and (tl == "n" or re.match(r"^[n↑⬆\s]+$", tl)):
                    return True, b, 0.9
    
    return False, None, 0.0


def detect_scale_bar(blocks: List[Dict[str, Any]]) -> Tuple[bool, Optional[Dict[str, Any]], float]:
    """
    Detect presence of scale bar.
    Looks for scale bar labels like "Scale Bar", "0 5 10 15 20m", etc.
    """
    scale_bar_patterns = [
        r"scale\s*bar",
        r"0\s+\d+\s+\d+\s+\d+m(?:etres)?",  # e.g., "0 5 10 15 20m" (last number attached to unit)
        r"0\s+\d+\s+\d+\s*m(?:etres)?",  # e.g., "0 5 10 m" (with or without space before unit)
        r"graphic\s*scale",
    ]
    
    for b in blocks:
        t = _norm(b.get("content", b.get("text", "")))
        tl = t.lower()
        
        for pattern in scale_bar_patterns:
            if re.search(pattern, tl):
                return True, b, 0.8
    
    return False, None, 0.0


def extract_drawing_number(blocks: List[Dict[str, Any]]) -> Tuple[Optional[str], Optional[Dict[str, Any]], float]:
    """
    Extract drawing number from plan drawings.
    Common formats: "Drawing No: 123/45", "Dwg No: ABC-001", "Drawing Number: P01"
    """
    drawing_patterns = [
        r"(?:drawing|dwg)\s*(?:no|number|num)[\s.:]*([A-Z0-9\-/]+)",
        r"project\s*(?:no|number)[\s.:]*([A-Z0-9\-/]+)",
    ]
    
    for b in blocks[:150]:  # Check first 150 blocks
        t = _norm(b.get("content", b.get("text", "")))
        
        for pattern in drawing_patterns:
            m = re.search(pattern, t, re.I)
            if m:
                drawing_num = m.group(1).strip()
                # Validate: should have at least one digit
                if re.search(r"\d", drawing_num):
                    return drawing_num, b, 0.8
    
    return None, None, 0.0


def extract_revision(blocks: List[Dict[str, Any]]) -> Tuple[Optional[str], Optional[Dict[str, Any]], float]:
    """
    Extract revision from plan drawings.
    Common formats: "Rev: A", "Revision: P01", "Rev. B"
    """
    revision_patterns = [
        r"(?:rev|revision)[\s.:]+(P?\d+|[A-Z])",
    ]
    
    for b in blocks[:150]:
        t = _norm(b.get("content", b.get("text", "")))
        
        for pattern in revision_patterns:
            m = re.search(pattern, t, re.I)
            if m:
                revision = m.group(1).strip().upper()
                return revision, b, 0.8
    
    return None, None, 0.0


# ============================================================================
# PHASE 3: MEASUREMENT EXTRACTION
# ============================================================================

# Measurement regex patterns
# Supports: 8.5m, 100 sqm, 12.5 metres, 150 sq m, 2.4m², 20,512 ft2, etc.
# Order matters: longer patterns first (ft2 before ft, m2 before m)
MEASUREMENT_PATTERN = re.compile(
    r"([\d,]+(?:\.\d+)?)\s*(?:(sqm|sq\s*m|m[²2]|ft[²2]|hectares?|acres?|ha)|(m(?:etres?)?|mm|cm|km|feet|ft))",
    re.I
)

# Context keywords for measurements
MEASUREMENT_CONTEXTS = {
    "height": [
        r"ridge\s+height", r"eaves\s+height", r"max(?:imum)?\s+height",
        r"height\s+(?:to|at)\s+(?:ridge|eaves)", r"overall\s+height",
        r"building\s+height", r"total\s+height"
    ],
    "area": [
        r"gross\s+internal\s+area", r"gia", r"floor\s+area", r"site\s+area",
        r"total\s+area", r"footprint", r"plot\s+area"
    ],
    "width": [r"width", r"wide"],
    "length": [r"length", r"long"],
    "depth": [r"depth", r"deep"],
    "distance": [r"distance", r"setback", r"separation"],
}

# Entity keywords (rooms, spaces, building parts)
ENTITY_PATTERNS = {
    "room": [
        r"bedroom\s+\d+", r"living\s+room", r"kitchen", r"bathroom",
        r"en[\-\s]?suite", r"wc", r"utility", r"study", r"dining\s+room"
    ],
    "space": [
        r"extension", r"loft", r"dormer", r"conservatory", r"garage",
        r"porch", r"balcony", r"terrace"
    ],
    "building": [
        r"existing\s+building", r"proposed\s+building", r"main\s+building",
        r"dwelling", r"house", r"property"
    ]
}

# Datum keywords (reference points for measurements)
DATUM_PATTERNS = [
    r"ground\s+level", r"ground\s+floor\s+level", r"ffl", r"finished\s+floor\s+level",
    r"ridge", r"eaves", r"existing\s+ground", r"proposed\s+ground",
    r"boundary", r"mean\s+ground\s+level"
]


def extract_measurements(blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract measurements from text blocks with context, entities, and datums.
    
    Returns list of measurement dictionaries:
    {
        "value": float,
        "unit": str,
        "raw_text": str,
        "context": str (height/area/width/length/depth/distance),
        "entity": str (optional - what is being measured),
        "datum": str (optional - reference point),
        "existing_or_proposed": str (existing/proposed/unknown),
        "page": int,
        "block_id": str,
        "confidence": float
    }
    """
    measurements = []
    
    for i, b in enumerate(blocks):
        t = _norm(b.get("content", b.get("text", "")))
        tl = t.lower()
        
        # Find all measurements in this block
        for match in MEASUREMENT_PATTERN.finditer(t):
            value_str = match.group(1).replace(",", "")  # Remove commas from numbers
            # Unit is in either group 2 (area units) or group 3 (length units)
            unit_str = match.group(2) if match.group(2) else match.group(3)
            
            try:
                value = float(value_str)
            except ValueError:
                continue
            
            # Normalize unit
            unit = _normalize_unit(unit_str)
            
            # Get context window (current block + previous/next blocks)
            context_blocks = blocks[max(0, i-2):min(len(blocks), i+3)]
            context_text = " ".join([_norm(cb.get("content", cb.get("text", ""))) for cb in context_blocks])
            context_text_lower = context_text.lower()
            
            # Detect measurement context (height, area, etc.)
            measurement_context = _detect_measurement_context(context_text_lower)
            
            # Detect entity being measured
            entity = _detect_entity(context_text_lower)
            
            # Detect datum (reference point)
            datum = _detect_datum(context_text_lower)
            
            # Detect existing vs proposed
            existing_or_proposed = _detect_existing_or_proposed(context_text_lower)
            
            # Calculate confidence based on context clarity
            confidence = 0.5  # Base confidence
            if measurement_context != "unknown":
                confidence += 0.2
            if entity:
                confidence += 0.15
            if datum:
                confidence += 0.15
            confidence = min(confidence, 1.0)
            
            page_num = int(b.get("page_number", b.get("page", 0)))
            block_id = f"p{page_num}b{b.get('index', '')}"
            
            measurements.append({
                "value": value,
                "unit": unit,
                "raw_text": match.group(0),
                "context": measurement_context,
                "entity": entity,
                "datum": datum,
                "existing_or_proposed": existing_or_proposed,
                "page": page_num,
                "block_id": block_id,
                "snippet": t[:100],
                "confidence": confidence,
                "bbox": b.get("bounding_box", b.get("bbox"))
            })
    
    return measurements


def _normalize_unit(unit_str: str) -> str:
    """Normalize measurement units to standard form."""
    unit_lower = unit_str.lower().strip()
    
    # Length units
    if unit_lower in ["m", "metre", "metres", "meter", "meters"]:
        return "m"
    elif unit_lower in ["mm", "millimetre", "millimetres"]:
        return "mm"
    elif unit_lower in ["cm", "centimetre", "centimetres"]:
        return "cm"
    elif unit_lower in ["km", "kilometre", "kilometres"]:
        return "km"
    elif unit_lower in ["ft", "foot", "feet"]:
        return "ft"
    
    # Area units (including superscript 2 and regular 2)
    elif unit_lower in ["sqm", "sq m", "m²", "m2", "square metres", "square meters"]:
        return "sqm"
    elif unit_lower in ["ft²", "ft2", "square feet", "sq ft"]:
        return "sqft"
    elif unit_lower in ["ha", "hectare", "hectares"]:
        return "ha"
    elif unit_lower in ["acre", "acres"]:
        return "acres"
    
    return unit_lower


def _detect_measurement_context(text: str) -> str:
    """Detect what type of measurement this is (height, area, etc.)."""
    for context_type, patterns in MEASUREMENT_CONTEXTS.items():
        for pattern in patterns:
            if re.search(pattern, text, re.I):
                return context_type
    return "unknown"


def _detect_entity(text: str) -> Optional[str]:
    """Detect what entity is being measured (room, extension, etc.)."""
    for entity_type, patterns in ENTITY_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, text, re.I)
            if match:
                return match.group(0)
    return None


def _detect_datum(text: str) -> Optional[str]:
    """Detect measurement datum (reference point)."""
    for pattern in DATUM_PATTERNS:
        match = re.search(pattern, text, re.I)
        if match:
            return match.group(0)
    return None


def _detect_existing_or_proposed(text: str) -> str:
    """Detect if measurement is for existing or proposed structure."""
    if re.search(r"\bproposed\b", text, re.I):
        return "proposed"
    elif re.search(r"\bexisting\b", text, re.I):
        return "existing"
    return "unknown"


# ============================================================================
# PHASE 4: CERTIFICATES & FEES EXTRACTION
# ============================================================================

# Certificate type patterns
CERTIFICATE_PATTERNS = {
    "A": [
        r"certificate\s+a\b",
        r"\bcertificate\s+a\s*[-:]\s*ownership",
        r"ownership\s+certificate\s+a\b",
        r"sole\s+owner",
        r"i\s+(?:am|certify\s+that\s+i\s+am)\s+the\s+(?:sole\s+)?owner"
    ],
    "B": [
        r"certificate\s+b\b",
        r"\bcertificate\s+b\s*[-:]\s*ownership",
        r"ownership\s+certificate\s+b\b",
        r"some\s+of\s+the\s+land",
        r"notice\s+has\s+been\s+given"
    ],
    "C": [
        r"certificate\s+c\b",
        r"\bcertificate\s+c\s*[-:]\s*ownership",
        r"ownership\s+certificate\s+c\b",
        r"unknown\s+owner",
        r"unable\s+to\s+issue\s+certificate"
    ],
    "D": [
        r"certificate\s+d\b",
        r"\bcertificate\s+d\s*[-:]\s*agricultural",
        r"agricultural\s+holding",
        r"agricultural\s+tenant"
    ]
}

# Signature patterns
SIGNATURE_PATTERNS = [
    r"signed\s*(?:by)?[\s:]*",
    r"signature[\s:]*",
    r"applicant\s+signature",
    r"agent\s+signature",
    r"i\s+(?:hereby\s+)?certify",
    r"declaration"
]

# Fee amount patterns - £123.45, $123, 123.00 GBP, etc.
FEE_PATTERN = re.compile(
    r"(?:£|GBP|USD|\$)\s*(\d{1,6}(?:,\d{3})*(?:\.\d{2})?)|(\d{1,6}(?:,\d{3})*(?:\.\d{2})?)\s*(?:£|GBP|pounds?)",
    re.I
)

# Fee exemption patterns
FEE_EXEMPTION_PATTERNS = [
    r"fee\s+(?:paid\s+)?exempt(?:ion)?",
    r"no\s+fee\s+(?:payable|required)",
    r"exempt\s+from\s+(?:planning\s+)?fee",
    r"prior\s+approval.*?no\s+fee"
]


def detect_certificate_type(blocks: List[Dict[str, Any]]) -> Tuple[Optional[str], Optional[Dict[str, Any]], float]:
    """
    Detect ownership certificate type (A, B, C, or D).
    
    Returns:
        (certificate_type, source_block, confidence)
    """
    # Search through blocks for certificate indicators
    for i, b in enumerate(blocks):
        t = _norm(b.get("content", b.get("text", "")))
        tl = t.lower()
        
        # Check each certificate type
        for cert_type, patterns in CERTIFICATE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, tl):
                    # Higher confidence if "certificate" is explicitly mentioned
                    confidence = 0.9 if "certificate" in tl else 0.7
                    return cert_type, b, confidence
    
    return None, None, 0.0


def detect_signatures(blocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Detect signature fields in the document.
    
    Returns:
        List of signature detections with:
        {
            "type": "applicant" | "agent" | "general",
            "is_signed": bool,
            "page": int,
            "block_id": str,
            "snippet": str,
            "confidence": float
        }
    """
    signatures = []
    
    for i, b in enumerate(blocks):
        t = _norm(b.get("content", b.get("text", "")))
        tl = t.lower()
        
        # Check for signature patterns
        for pattern in SIGNATURE_PATTERNS:
            if re.search(pattern, tl):
                # Determine signature type
                sig_type = "general"
                if "applicant" in tl:
                    sig_type = "applicant"
                elif "agent" in tl:
                    sig_type = "agent"
                
                # Check if actually signed (look for name/text after signature field)
                # If we see "signed by:" followed by empty space or just the word "signature",
                # it's likely unsigned
                is_signed = False
                confidence = 0.5
                
                # Look at current and next few blocks for evidence of signing
                context_blocks = blocks[i:min(len(blocks), i+3)]
                context_text = " ".join([_norm(cb.get("content", cb.get("text", ""))) for cb in context_blocks])
                context_lower = context_text.lower()
                
                # Heuristics for signed documents:
                # - Contains "certify" (declaration signed)
                # - Contains actual name text after "signed by"
                # - Has date near signature field
                if "certify" in context_lower:
                    is_signed = True
                    confidence = 0.8
                elif re.search(r"signed\s*(?:by)?[\s:]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)", context_text, re.IGNORECASE):
                    # Found "Signed by: John Smith" pattern (case-insensitive for "signed", case-sensitive for names)
                    is_signed = True
                    confidence = 0.85
                elif re.search(r"\d{1,2}[./-]\d{1,2}[./-]\d{2,4}", context_text):
                    # Has date near signature field
                    is_signed = True
                    confidence = 0.7
                
                page_num = int(b.get("page_number", b.get("page", 0)))
                block_id = f"p{page_num}b{b.get('index', '')}"
                
                signatures.append({
                    "type": sig_type,
                    "is_signed": is_signed,
                    "page": page_num,
                    "block_id": block_id,
                    "snippet": t[:100],
                    "confidence": confidence,
                    "bbox": b.get("bounding_box", b.get("bbox"))
                })
                
                break  # Only record one signature per block
    
    return signatures


def extract_fee_amount(blocks: List[Dict[str, Any]]) -> Tuple[Optional[float], Optional[Dict[str, Any]], float]:
    """
    Extract fee amount from document.
    
    Returns:
        (fee_amount_gbp, source_block, confidence)
    """
    for b in blocks:
        t = _norm(b.get("content", b.get("text", "")))
        tl = t.lower()
        
        # Look for fee-related context
        if any(keyword in tl for keyword in ["fee", "payment", "charge", "cost"]):
            # Try to extract amount
            match = FEE_PATTERN.search(t)
            if match:
                # Extract amount from either group 1 (prefix currency) or group 2 (suffix currency)
                amount_str = match.group(1) if match.group(1) else match.group(2)
                amount_str = amount_str.replace(",", "")
                
                try:
                    amount = float(amount_str)
                    
                    # Sanity check: planning fees typically £100-£10,000
                    if 50 <= amount <= 50000:
                        confidence = 0.9 if "fee" in tl else 0.7
                        return amount, b, confidence
                except ValueError:
                    continue
    
    return None, None, 0.0


def detect_fee_exemption(blocks: List[Dict[str, Any]]) -> Tuple[bool, Optional[Dict[str, Any]], float]:
    """
    Detect if fee exemption is claimed.
    
    Returns:
        (is_exempt, source_block, confidence)
    """
    for b in blocks:
        t = _norm(b.get("content", b.get("text", "")))
        tl = t.lower()
        
        # Check exemption patterns
        for pattern in FEE_EXEMPTION_PATTERNS:
            if re.search(pattern, tl):
                confidence = 0.9 if "exempt" in tl else 0.7
                return True, b, confidence
    
    return False, None, 0.0


def map_fields(extracted_layout: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract structured fields from extracted layout.
    
    Returns:
        {
            "fields": {field_name: value, ...},
            "evidence_index": {field_name: [{"page": int, "block_id": str, "snippet": str, "confidence": float, "extraction_method": str, "bbox": dict}, ...]}
        }
    """
    blocks = extracted_layout.get("text_blocks", []) or []
    fields: Dict[str, Any] = {}
    evidence: Dict[str, List[Dict[str, Any]]] = {}

    # document type
    dtype = classify_document(blocks)
    fields["document_type"] = dtype
    
    # application type
    app_type = detect_application_type(blocks)
    fields["application_type"] = app_type

    # app ref - try PP-\d+ pattern first (more common), then year-based pattern
    # Pattern: \bPP-\d{6,}\b (e.g., PP-14469287)
    for b in blocks[:400]:
        t = b.get("content", b.get("text", ""))
        m = APPREF_RE.search(t)
        if m:
            ref = m.group(1).upper()
            # Normalize PP-14469287 format
            if ref.startswith("PP-"):
                fields["application_ref"] = ref
            else:
                fields["application_ref"] = ref
            fields["application_ref_confidence"] = 0.9 if "PP-" in ref else 0.8
            page_num = int(b.get("page_number", b.get("page", 0)))
            block_id = f"p{page_num}b{b.get('index', '')}"
            confidence = 0.9 if "PP-" in ref else 0.8
            bbox = b.get("bounding_box", b.get("bbox"))
            _add_ev(evidence, "application_ref", page_num, block_id, t, confidence, dtype, 
                   extraction_method="regex", bbox=bbox)
            break

    # site_address - use improved heuristic
    if "site_address" not in fields:
        addr, src, conf = pick_site_address(blocks)
        if addr:
            fields["site_address"] = addr
            fields["site_address_confidence"] = conf
            page_num = int(src.get("page_number", src.get("page", 0)))
            block_id = f"p{page_num}b{src.get('index', '')}"
            bbox = src.get("bounding_box", src.get("bbox"))
            _add_ev(evidence, "site_address", page_num, block_id, src.get("content", src.get("text", "")), 
                   conf, dtype, extraction_method="heuristic", bbox=bbox)
    
    # proposed_use - try Prior Approval pattern first, then heuristic
    if "proposed_use" not in fields:
        # Try to extract from "I/We hereby apply for Prior Approval:" pattern
        for i, b in enumerate(blocks[:100]):
            t = _norm(b.get("content", b.get("text", "")))
            tl = t.lower()
            if "i/we hereby apply for prior approval" in tl or "prior approval for" in tl:
                # Extract the description after the colon or "for"
                parts = re.split(r":|for", t, maxsplit=1)
                if len(parts) == 2:
                    prop_text = _norm(parts[1])
                    if len(prop_text) > 10:
                        fields["proposed_use"] = prop_text
                        fields["proposed_use_confidence"] = 0.9
                        page_num = int(b.get("page_number", b.get("page", 0)))
                        block_id = f"p{page_num}b{b.get('index', '')}"
                        bbox = b.get("bounding_box", b.get("bbox"))
                        _add_ev(evidence, "proposed_use", page_num, block_id, t, 0.9, dtype,
                               extraction_method="pattern", bbox=bbox)
                        break
        
        # Fallback to heuristic extraction
        if "proposed_use" not in fields:
            prop, src, conf = pick_proposed_use(blocks)
            if prop:
                fields["proposed_use"] = prop
                fields["proposed_use_confidence"] = conf
                page_num = int(src.get("page_number", src.get("page", 0)))
                block_id = f"p{page_num}b{src.get('index', '')}"
                bbox = src.get("bounding_box", src.get("bbox"))
                _add_ev(evidence, "proposed_use", page_num, block_id, src.get("content", src.get("text", "")), 
                       conf, dtype, extraction_method="heuristic", bbox=bbox)

    # labeled fields (fallback for other fields)
    for field, pats in LABEL_PATTERNS.items():
        if field not in fields:  # Skip if already found
            val, src = extract_by_label(blocks, pats, field_name=field)
            if val:
                fields[field] = val
                fields[f"{field}_confidence"] = 0.7  # Label-based extraction is medium confidence
                page_num = int(src.get("page_number", src.get("page", 0)))
                block_id = f"p{page_num}b{src.get('index', '')}"
                bbox = src.get("bounding_box", src.get("bbox"))
                _add_ev(evidence, field, page_num, block_id, src.get("content", src.get("text", "")), 
                       0.7, dtype, extraction_method="label", bbox=bbox)

    # regex fields (email/phone/postcode) - exclude council contact info
    site_location_blocks = []  # Track blocks in Site Location section
    for i, b in enumerate(blocks[:400]):
        t = b.get("content", b.get("text", ""))
        if _is_in_site_location_section(blocks, i):
            site_location_blocks.append((i, b, t))
    
    # Postcode extraction with context ranking
    # Strategy: Prefer postcodes near "Site location" or "Postcode" label
    # Hard-deprioritize PO Box postcodes (B1 1TU) when near council contact info
    postcode_candidates = []
    
    # First: Collect all postcodes with context scoring
    for i, b in enumerate(blocks[:400]):
        t = b.get("content", b.get("text", ""))
        m = POSTCODE_RE.search(t)
        if m:
            postcode = m.group(1).upper()
            confidence = 0.5  # Base confidence
            
            # Check context for ranking
            in_site_section = _is_in_site_location_section(blocks, i)
            tl = t.lower()
            
            # High confidence: In Site Location section or near "Postcode" label
            if in_site_section or "postcode" in tl:
                confidence = 0.9
            # Medium confidence: Near "Site" or "Address" keywords
            elif "site" in tl or "address" in tl:
                confidence = 0.7
            # Low confidence: Default
            else:
                confidence = 0.5
            
            # Hard-deprioritize PO Box postcodes (B1 1TU, etc.) when near council contact info
            if _is_council_contact(t) or "po box" in tl or "birmingham city council" in tl:
                # Reduce confidence significantly for council PO box postcodes
                if postcode.startswith("B1 1TU") or "po box" in tl:
                    confidence = 0.1  # Very low - likely council PO box, not site postcode
            
            postcode_candidates.append((postcode, b, confidence, i))
    
    # If we have candidates, use the highest confidence one
    if postcode_candidates and "postcode" not in fields:
        # Sort by confidence (highest first)
        postcode_candidates.sort(key=lambda x: x[2], reverse=True)
        postcode, b, conf, idx = postcode_candidates[0]
        
        # Only use if confidence is reasonable (avoid council PO boxes)
        if conf >= 0.3:
            fields["postcode"] = postcode
            fields["postcode_confidence"] = conf
            page_num = int(b.get("page_number", b.get("page", 0)))
            block_id = f"p{page_num}b{b.get('index', '')}"
            bbox = b.get("bounding_box", b.get("bbox"))
            _add_ev(evidence, "postcode", page_num, block_id, b.get("content", b.get("text", "")), 
                   conf, dtype, extraction_method="regex", bbox=bbox)
    
    # Applicant email/phone - exclude council contact info
    for i, b in enumerate(blocks[:400]):
        t = b.get("content", b.get("text", ""))
        
        # Skip council contact blocks
        if _is_council_contact(t):
            continue
        
        if "applicant_email" not in fields:
            m = EMAIL_RE.search(t)
            if m:
                # Additional check: prefer emails near "applicant" context
                context_blocks = blocks[max(0, i-2):min(len(blocks), i+3)]
                context = " ".join([_norm(cb.get("content", cb.get("text", ""))) for cb in context_blocks]).lower()
                confidence = 0.8 if "applicant" in context else 0.5
                fields["applicant_email"] = m.group(0)
                fields["applicant_email_confidence"] = confidence
                page_num = int(b.get("page_number", b.get("page", 0)))
                block_id = f"p{page_num}b{b.get('index', '')}"
                bbox = b.get("bounding_box", b.get("bbox"))
                _add_ev(evidence, "applicant_email", page_num, block_id, t, confidence, dtype,
                       extraction_method="regex", bbox=bbox)
        
        if "applicant_phone" not in fields:
            m = PHONE_RE.search(t)
            if m and looks_like_phone(m.group(1)) and len(_norm(m.group(1))) >= 9:
                # Additional check: prefer phones near "applicant" context
                context_blocks = blocks[max(0, i-2):min(len(blocks), i+3)]
                context = " ".join([_norm(cb.get("content", cb.get("text", ""))) for cb in context_blocks]).lower()
                confidence = 0.8 if "applicant" in context else 0.5
                fields["applicant_phone"] = _norm(m.group(1))
                fields["applicant_phone_confidence"] = confidence
                page_num = int(b.get("page_number", b.get("page", 0)))
                block_id = f"p{page_num}b{b.get('index', '')}"
                bbox = b.get("bounding_box", b.get("bbox"))
                _add_ev(evidence, "applicant_phone", page_num, block_id, t, confidence, dtype,
                       extraction_method="regex", bbox=bbox)

    # ========================================================================
    # PHASE 2: PLAN METADATA EXTRACTION
    # ========================================================================
    # Only extract plan metadata for drawing-type documents
    if dtype in ["site_plan", "drawing"]:
        
        # Plan type classification
        plan_type = classify_plan_type(blocks)
        if plan_type:
            fields["plan_type"] = plan_type
            # No confidence field needed - this is a classification, not extraction
        
        # Scale ratio extraction
        scale, scale_src, scale_conf = extract_scale_ratio(blocks)
        if scale:
            fields["scale_ratio"] = scale
            fields["scale_ratio_confidence"] = scale_conf
            page_num = int(scale_src.get("page_number", scale_src.get("page", 0)))
            block_id = f"p{page_num}b{scale_src.get('index', '')}"
            bbox = scale_src.get("bounding_box", scale_src.get("bbox"))
            _add_ev(evidence, "scale_ratio", page_num, block_id, 
                   scale_src.get("content", scale_src.get("text", "")), 
                   scale_conf, dtype, extraction_method="regex", bbox=bbox)
        
        # North arrow detection
        has_north, north_src, north_conf = detect_north_arrow(blocks)
        fields["north_arrow_present"] = has_north
        if has_north and north_src:
            fields["north_arrow_confidence"] = north_conf
            page_num = int(north_src.get("page_number", north_src.get("page", 0)))
            block_id = f"p{page_num}b{north_src.get('index', '')}"
            bbox = north_src.get("bounding_box", north_src.get("bbox"))
            _add_ev(evidence, "north_arrow_present", page_num, block_id,
                   north_src.get("content", north_src.get("text", "")),
                   north_conf, dtype, extraction_method="pattern", bbox=bbox)
        
        # Scale bar detection
        has_scale_bar, scale_bar_src, scale_bar_conf = detect_scale_bar(blocks)
        fields["scale_bar_present"] = has_scale_bar
        if has_scale_bar and scale_bar_src:
            fields["scale_bar_confidence"] = scale_bar_conf
            page_num = int(scale_bar_src.get("page_number", scale_bar_src.get("page", 0)))
            block_id = f"p{page_num}b{scale_bar_src.get('index', '')}"
            bbox = scale_bar_src.get("bounding_box", scale_bar_src.get("bbox"))
            _add_ev(evidence, "scale_bar_present", page_num, block_id,
                   scale_bar_src.get("content", scale_bar_src.get("text", "")),
                   scale_bar_conf, dtype, extraction_method="pattern", bbox=bbox)
        
        # Drawing number extraction
        drawing_num, drawing_src, drawing_conf = extract_drawing_number(blocks)
        if drawing_num:
            fields["drawing_number"] = drawing_num
            fields["drawing_number_confidence"] = drawing_conf
            page_num = int(drawing_src.get("page_number", drawing_src.get("page", 0)))
            block_id = f"p{page_num}b{drawing_src.get('index', '')}"
            bbox = drawing_src.get("bounding_box", drawing_src.get("bbox"))
            _add_ev(evidence, "drawing_number", page_num, block_id,
                   drawing_src.get("content", drawing_src.get("text", "")),
                   drawing_conf, dtype, extraction_method="regex", bbox=bbox)
        
        # Revision extraction
        revision, rev_src, rev_conf = extract_revision(blocks)
        if revision:
            fields["revision"] = revision
            fields["revision_confidence"] = rev_conf
            page_num = int(rev_src.get("page_number", rev_src.get("page", 0)))
            block_id = f"p{page_num}b{rev_src.get('index', '')}"
            bbox = rev_src.get("bounding_box", rev_src.get("bbox"))
            _add_ev(evidence, "revision", page_num, block_id,
                   rev_src.get("content", rev_src.get("text", "")),
                   rev_conf, dtype, extraction_method="regex", bbox=bbox)

    # ========================================================================
    # PHASE 3: MEASUREMENT EXTRACTION
    # ========================================================================
    # Extract measurements from all document types (forms, plans, etc.)
    measurements = extract_measurements(blocks)
    
    if measurements:
        # Store measurements list in fields
        fields["measurements"] = measurements
        
        # Add evidence for measurements (store as "measurements" key)
        for measurement in measurements:
            _add_ev(
                evidence, 
                "measurements", 
                measurement["page"], 
                measurement["block_id"],
                measurement["snippet"],
                measurement["confidence"],
                dtype,
                extraction_method="regex",
                bbox=measurement.get("bbox")
            )
        
        # Extract key measurements for business rules
        # R10: Ridge height (max height to ridge)
        ridge_heights = [m for m in measurements 
                        if "ridge" in m.get("context", "") 
                        or (m.get("datum") and "ridge" in m.get("datum", "").lower())]
        if ridge_heights:
            max_ridge = max(ridge_heights, key=lambda x: x["value"])
            fields["ridge_height_m"] = max_ridge["value"]
            fields["ridge_height_confidence"] = max_ridge["confidence"]
        
        # R11: Site area
        site_areas = [m for m in measurements 
                     if m.get("context") == "area" 
                     and ("site" in m.get("snippet", "").lower() or "plot" in m.get("snippet", "").lower())
                     and m.get("unit") in ["sqm", "ha", "acres"]]
        if site_areas:
            # Prefer the largest area measurement (likely total site area)
            max_area = max(site_areas, key=lambda x: x["value"] if x["unit"] == "sqm" else x["value"] * 10000 if x["unit"] == "ha" else x["value"] * 4046.86)
            fields["site_area_sqm"] = max_area["value"] if max_area["unit"] == "sqm" else (max_area["value"] * 10000 if max_area["unit"] == "ha" else max_area["value"] * 4046.86)
            fields["site_area_confidence"] = max_area["confidence"]
        
        # R12: Room areas (for minimum standards)
        room_areas = [m for m in measurements 
                     if m.get("context") == "area" 
                     and m.get("entity") 
                     and any(room_type in m.get("entity", "").lower() for room_type in ["bedroom", "living", "kitchen"])]
        if room_areas:
            fields["room_areas"] = room_areas

    # ========================================================================
    # PHASE 4: CERTIFICATES & FEES EXTRACTION
    # ========================================================================
    # Only extract certificates and fees from application forms
    if dtype == "application_form":
        
        # Ownership certificate detection
        cert_type, cert_src, cert_conf = detect_certificate_type(blocks)
        if cert_type:
            fields["certificate_type"] = cert_type
            fields["certificate_confidence"] = cert_conf
            page_num = int(cert_src.get("page_number", cert_src.get("page", 0)))
            block_id = f"p{page_num}b{cert_src.get('index', '')}"
            bbox = cert_src.get("bounding_box", cert_src.get("bbox"))
            _add_ev(evidence, "certificate_type", page_num, block_id,
                   cert_src.get("content", cert_src.get("text", "")),
                   cert_conf, dtype, extraction_method="pattern", bbox=bbox)
        
        # Signature detection
        signatures = detect_signatures(blocks)
        if signatures:
            # Store all signatures in fields
            fields["signatures"] = signatures
            
            # Set overall is_signed flag if any signature is signed
            fields["is_signed"] = any(sig["is_signed"] for sig in signatures)
            
            # Add evidence for each signature
            for sig in signatures:
                _add_ev(
                    evidence,
                    "signatures",
                    sig["page"],
                    sig["block_id"],
                    sig["snippet"],
                    sig["confidence"],
                    dtype,
                    extraction_method="pattern",
                    bbox=sig.get("bbox")
                )
        else:
            fields["is_signed"] = False
        
        # Fee amount extraction
        fee_amount, fee_src, fee_conf = extract_fee_amount(blocks)
        if fee_amount:
            fields["fee_paid_amount"] = fee_amount
            fields["fee_amount_confidence"] = fee_conf
            page_num = int(fee_src.get("page_number", fee_src.get("page", 0)))
            block_id = f"p{page_num}b{fee_src.get('index', '')}"
            bbox = fee_src.get("bounding_box", fee_src.get("bbox"))
            _add_ev(evidence, "fee_paid_amount", page_num, block_id,
                   fee_src.get("content", fee_src.get("text", "")),
                   fee_conf, dtype, extraction_method="regex", bbox=bbox)
        
        # Fee exemption detection
        is_exempt, exemption_src, exemption_conf = detect_fee_exemption(blocks)
        if is_exempt:
            fields["exemption_claimed"] = True
            fields["exemption_confidence"] = exemption_conf
            page_num = int(exemption_src.get("page_number", exemption_src.get("page", 0)))
            block_id = f"p{page_num}b{exemption_src.get('index', '')}"
            bbox = exemption_src.get("bounding_box", exemption_src.get("bbox"))
            _add_ev(evidence, "exemption_claimed", page_num, block_id,
                   exemption_src.get("content", exemption_src.get("text", "")),
                   exemption_conf, dtype, extraction_method="pattern", bbox=bbox)
        else:
            fields["exemption_claimed"] = False

    return {"fields": fields, "evidence_index": evidence}

