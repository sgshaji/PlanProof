"""
Automatic parent application discovery service.

Finds potential parent applications for modification/resubmission scenarios
by searching across multiple attributes (address, postcode, reference).
"""

import logging
import re
from typing import Dict, List, Optional, Tuple
from fuzzywuzzy import fuzz

from planproof.db import Database, Application, Submission

LOGGER = logging.getLogger(__name__)


# Planning application reference patterns
APP_REF_PATTERNS = [
    r'APP[-/]?\d{4}[-/]?\d+',  # APP-2024-001, APP/2024/001
    r'PP[-]?\d+',               # PP-14469287
    r'\d{8}[/-][A-Z]+',        # 20240615/HOU
    r'[A-Z]+[-/]?\d{4}[-/]?\d+',  # HOU-2024-001
]


def discover_parent_application(
    extracted_fields: Dict[str, any],
    current_application_id: Optional[int] = None,
    db: Optional[Database] = None
) -> Tuple[Optional[int], float, str]:
    """
    Automatically discover parent application for modifications/resubmissions.
    
    Uses multiple strategies:
    1. Extract parent reference from description
    2. Search by site address
    3. Search by postcode
    
    Args:
        extracted_fields: Dictionary of extracted fields (site_address, postcode, proposed_use, etc.)
        current_application_id: ID of current application (to exclude from search)
        db: Optional Database instance
    
    Returns:
        Tuple of (parent_submission_id, confidence, reason)
        - parent_submission_id: ID of parent submission, or None if not found
        - confidence: 0.0-1.0 confidence score
        - reason: Human-readable explanation of how parent was found
    
    Example:
        >>> parent_id, confidence, reason = discover_parent_application(fields)
        >>> print(f"Found parent {parent_id} with {confidence:.0%} confidence: {reason}")
    """
    if db is None:
        db = Database()
    
    # Strategy 1: Extract parent reference from description
    parent_ref = _extract_parent_reference(extracted_fields)
    if parent_ref:
        parent_app = db.get_application_by_ref(parent_ref)
        if parent_app:
            parent_submission_id = _get_latest_submission_id(parent_app.id, db)
            if parent_submission_id:
                LOGGER.info(
                    f"Found parent by reference extraction: {parent_ref} "
                    f"(submission_id={parent_submission_id})"
                )
                return (
                    parent_submission_id,
                    0.95,
                    f"Parent reference '{parent_ref}' found in description"
                )
    
    # Strategy 2: Search by site address
    site_address = extracted_fields.get("site_address")
    if site_address:
        candidates = db.find_applications_by_address(
            site_address,
            exclude_application_id=current_application_id
        )
        
        if candidates:
            # Score candidates by address similarity
            best_match = _find_best_address_match(site_address, candidates)
            
            if best_match:
                app, similarity = best_match
                parent_submission_id = _get_latest_submission_id(app.id, db)
                
                if parent_submission_id and similarity >= 0.90:
                    LOGGER.info(
                        f"Found parent by address match: {app.application_ref} "
                        f"(similarity={similarity:.2f}, submission_id={parent_submission_id})"
                    )
                    return (
                        parent_submission_id,
                        similarity,
                        f"Address match: {app.site_address} (similarity: {similarity:.0%})"
                    )
    
    # Strategy 3: Search by postcode (fallback)
    postcode = extracted_fields.get("postcode")
    if postcode:
        candidates = db.find_applications_by_postcode(
            postcode,
            exclude_application_id=current_application_id
        )
        
        if candidates:
            # If only one match, return it with medium confidence
            if len(candidates) == 1:
                app = candidates[0]
                parent_submission_id = _get_latest_submission_id(app.id, db)
                
                if parent_submission_id:
                    LOGGER.info(
                        f"Found single parent by postcode: {app.application_ref} "
                        f"(submission_id={parent_submission_id})"
                    )
                    return (
                        parent_submission_id,
                        0.70,
                        f"Single application found at postcode {postcode}"
                    )
            
            # Multiple matches - need user selection
            if len(candidates) > 1:
                LOGGER.info(
                    f"Found {len(candidates)} potential parents by postcode {postcode}. "
                    "User selection required."
                )
                # Return None to indicate manual selection needed
                return (None, 0.0, f"{len(candidates)} applications found at postcode {postcode}")
    
    # No parent found
    LOGGER.info("No parent application found. This appears to be a new application.")
    return (None, 0.0, "No parent application found")


def get_potential_parents(
    extracted_fields: Dict[str, any],
    current_application_id: Optional[int] = None,
    db: Optional[Database] = None
) -> List[Dict]:
    """
    Get list of potential parent applications for user selection.
    
    Returns all candidates found by address or postcode matching.
    
    Args:
        extracted_fields: Dictionary of extracted fields
        current_application_id: ID of current application (to exclude)
        db: Optional Database instance
    
    Returns:
        List of dicts with parent application details:
        [
            {
                "application_id": 123,
                "application_ref": "APP-2024-001",
                "site_address": "123 Main Street",
                "status": "approved",
                "created_at": "2024-06-15",
                "latest_submission_id": 456
            },
            ...
        ]
    """
    if db is None:
        db = Database()
    
    candidates = []
    
    # Search by address
    site_address = extracted_fields.get("site_address")
    if site_address:
        address_matches = db.find_applications_by_address(
            site_address,
            exclude_application_id=current_application_id
        )
        candidates.extend(address_matches)
    
    # Search by postcode if no address matches
    if not candidates:
        postcode = extracted_fields.get("postcode")
        if postcode:
            postcode_matches = db.find_applications_by_postcode(
                postcode,
                exclude_application_id=current_application_id
            )
            candidates.extend(postcode_matches)
    
    # Format results
    results = []
    for app in candidates:
        latest_submission_id = _get_latest_submission_id(app.id, db)
        
        results.append({
            "application_id": app.id,
            "application_ref": app.application_ref,
            "site_address": app.site_address,
            "postcode": app.postcode,
            "status": getattr(app, "status", "unknown"),
            "created_at": app.created_at.isoformat() if app.created_at else None,
            "latest_submission_id": latest_submission_id
        })
    
    return results


def _extract_parent_reference(extracted_fields: Dict[str, any]) -> Optional[str]:
    """
    Extract parent application reference from description or proposed use.
    
    Looks for patterns like:
    - "in relation to APP-2024-001"
    - "amendment to planning permission PP-14469287"
    - "following approval of 20240615/HOU"
    """
    # Fields to search
    search_fields = [
        extracted_fields.get("proposed_use", ""),
        extracted_fields.get("application_description", ""),
        extracted_fields.get("description", "")
    ]
    
    for field_value in search_fields:
        if not field_value:
            continue
        
        # Try each pattern
        for pattern in APP_REF_PATTERNS:
            match = re.search(pattern, str(field_value), re.IGNORECASE)
            if match:
                ref = match.group(0)
                LOGGER.info(f"Extracted parent reference from description: {ref}")
                return ref
    
    return None


def _find_best_address_match(
    target_address: str,
    candidates: List[Application]
) -> Optional[Tuple[Application, float]]:
    """
    Find best matching application by address similarity.
    
    Uses fuzzy string matching to score similarity.
    
    Returns:
        Tuple of (best_application, similarity_score) or None
    """
    if not candidates:
        return None
    
    best_app = None
    best_similarity = 0.0
    
    target_clean = target_address.lower().strip()
    
    for app in candidates:
        if not app.site_address:
            continue
        
        candidate_clean = app.site_address.lower().strip()
        
        # Use fuzzy ratio (accounts for typos, word order)
        similarity = fuzz.ratio(target_clean, candidate_clean) / 100.0
        
        if similarity > best_similarity:
            best_similarity = similarity
            best_app = app
    
    if best_app:
        return (best_app, best_similarity)
    
    return None


def _get_latest_submission_id(application_id: int, db: Database) -> Optional[int]:
    """Get the latest submission ID for an application."""
    session = db.get_session()
    try:
        latest_submission = session.query(Submission).filter(
            Submission.planning_case_id == application_id
        ).order_by(Submission.created_at.desc()).first()
        
        return latest_submission.id if latest_submission else None
    finally:
        session.close()
