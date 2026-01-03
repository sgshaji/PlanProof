"""
LLM-assisted submission type classification.

Uses Azure OpenAI to intelligently determine if a submission is:
- modification: Changes to existing proposal (same site, altered plans)
- new_construction: Entirely new development
- resubmission: Resubmitting after rejection/withdrawal
"""

import logging
from typing import Dict, Optional
from planproof.aoai import AzureOpenAIClient

LOGGER = logging.getLogger(__name__)


def classify_submission_type(
    extraction: Dict,
    parent_submission_extraction: Optional[Dict],
    aoai_client: AzureOpenAIClient
) -> Dict[str, any]:
    """
    Use LLM to classify submission type with fallback to heuristics.

    Args:
        extraction: Current submission extraction with fields + evidence
        parent_submission_extraction: Parent submission extraction (if exists)
        aoai_client: Azure OpenAI client

    Returns:
        {
            "submission_type": "modification" | "new_construction" | "resubmission",
            "confidence": 0.0-1.0,
            "reasoning": "Why this classification was chosen",
            "key_indicators": ["list", "of", "supporting", "evidence"]
        }

    Example:
        >>> classification = classify_submission_type(v1_extraction, v0_extraction, aoai)
        >>> print(classification["submission_type"])  # "modification"
        >>> print(classification["confidence"])  # 0.92
    """

    # Extract key fields
    current_fields = extraction.get("fields", {})
    parent_fields = parent_submission_extraction.get("fields", {}) if parent_submission_extraction else {}

    # Build classification prompt
    prompt = _build_classification_prompt(current_fields, parent_fields)

    try:
        response = aoai_client.chat_json(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1  # Low temperature for consistency
        )

        classification = response["response"]

        # Validate response structure
        if not all(k in classification for k in ["submission_type", "confidence", "reasoning"]):
            raise ValueError("LLM response missing required fields")

        # Validate submission_type is one of allowed values
        allowed_types = {"modification", "new_construction", "resubmission"}
        if classification["submission_type"] not in allowed_types:
            raise ValueError(f"Invalid submission_type: {classification['submission_type']}")

        LOGGER.info(
            f"LLM classified submission as '{classification['submission_type']}' "
            f"(confidence: {classification['confidence']:.2f})"
        )

        return classification

    except Exception as e:
        LOGGER.warning(f"LLM classification failed: {e}. Falling back to heuristic.")
        # Fallback to heuristic classification
        return _heuristic_classification(current_fields, parent_fields)


def _build_classification_prompt(current: Dict, parent: Dict) -> str:
    """Build the LLM classification prompt."""

    has_parent = bool(parent)

    prompt = f"""You are analyzing a planning application submission to determine its type.

**CURRENT SUBMISSION FIELDS:**
- Site Address: {current.get('site_address', 'N/A')}
- Proposed Use: {current.get('proposed_use', 'N/A')}
- Development Type: {current.get('development_type', 'N/A')}
- Application Description: {current.get('application_description', 'N/A')}
- Proposed Height: {current.get('proposed_height', 'N/A')}
- Proposed Floor Area: {current.get('proposed_floor_area', 'N/A')}

{'**PARENT SUBMISSION FIELDS (existing proposal being modified):**' if has_parent else '**NO PARENT SUBMISSION (this is the first submission)**'}
{f'''- Site Address: {parent.get('site_address', 'N/A')}
- Proposed Use: {parent.get('proposed_use', 'N/A')}
- Development Type: {parent.get('development_type', 'N/A')}
- Application Description: {parent.get('application_description', 'N/A')}
- Proposed Height: {parent.get('proposed_height', 'N/A')}
- Proposed Floor Area: {parent.get('proposed_floor_area', 'N/A')}''' if has_parent else ''}

**CLASSIFICATION TASK:**
Determine if this submission is:

1. **modification**: Changes to an existing approved/submitted proposal
   - Same site, same core use, with specific alterations
   - Examples: "increase height from 10m to 12m", "add 2 extra bedrooms", "amend materials"
   - Keywords: "amendment", "revised", "alteration", "extension", "change from approved"

2. **new_construction**: Entirely new development proposal
   - Different site OR completely different use
   - Examples: "new dwelling", "new office building", "proposed construction"
   - Keywords: "new development", "proposed construction", "erection of"

3. **resubmission**: Resubmitting after rejection/withdrawal
   - Same proposal as previous, addressing refusal reasons
   - Examples: "following refusal", "resubmission of", "addressing previous concerns"
   - Keywords: "resubmission", "following refusal", "addressing officer comments"

**DECISION CRITERIA:**
- If NO parent exists → likely "new_construction" (unless description says "resubmission")
- If parent exists AND description mentions changes/amendments → "modification"
- If parent exists AND description is identical/similar → "resubmission"
- Compare site addresses: different address → "new_construction"
- Compare proposed uses: completely different use → "new_construction"

**CONFIDENCE SCORING:**
- 0.9-1.0: Very clear indicators in description + field comparisons match
- 0.7-0.8: Good indicators but some ambiguity
- 0.5-0.6: Weak indicators, mostly based on heuristics
- <0.5: Highly uncertain, may need human review

Return JSON (STRICT FORMAT):
{{
    "submission_type": "modification|new_construction|resubmission",
    "confidence": 0.0-1.0,
    "reasoning": "2-3 sentence explanation of why this classification was chosen",
    "key_indicators": ["list of specific phrases or field comparisons supporting this classification"]
}}"""

    return prompt


def _heuristic_classification(current: Dict, parent: Dict) -> Dict:
    """
    Fallback heuristic classification if LLM fails.

    Uses simple keyword matching and field comparison.
    """

    # Get application description for keyword analysis
    description = current.get("application_description", "").lower()

    # If no parent submission exists
    if not parent:
        # Check for resubmission keywords
        resubmission_keywords = ["resubmission", "following refusal", "following rejection", "resubmit"]
        if any(kw in description for kw in resubmission_keywords):
            return {
                "submission_type": "resubmission",
                "confidence": 0.6,
                "reasoning": "No parent found but description contains resubmission keywords",
                "key_indicators": [kw for kw in resubmission_keywords if kw in description]
            }

        # Default to new construction if no parent
        return {
            "submission_type": "new_construction",
            "confidence": 0.6,
            "reasoning": "No parent submission found; assuming new construction",
            "key_indicators": ["no_parent"]
        }

    # Parent exists - check for modification keywords
    mod_keywords = [
        "amendment", "revised", "alteration", "extension", "change from",
        "modification", "variation", "amended", "change to", "increase", "decrease"
    ]
    found_mod_keywords = [kw for kw in mod_keywords if kw in description]

    if found_mod_keywords:
        return {
            "submission_type": "modification",
            "confidence": 0.7,
            "reasoning": f"Description contains modification keywords: {', '.join(found_mod_keywords)}",
            "key_indicators": found_mod_keywords
        }

    # Check if site addresses are different
    current_address = current.get("site_address", "").lower()
    parent_address = parent.get("site_address", "").lower()

    if current_address and parent_address and current_address != parent_address:
        return {
            "submission_type": "new_construction",
            "confidence": 0.8,
            "reasoning": "Site address differs from parent submission",
            "key_indicators": [f"current: {current_address}", f"parent: {parent_address}"]
        }

    # Check if proposed uses are completely different
    current_use = current.get("proposed_use", "").lower()
    parent_use = parent.get("proposed_use", "").lower()

    if current_use and parent_use and current_use != parent_use:
        # Different uses - likely new construction
        return {
            "submission_type": "new_construction",
            "confidence": 0.75,
            "reasoning": "Proposed use differs significantly from parent",
            "key_indicators": [f"current use: {current_use}", f"parent use: {parent_use}"]
        }

    # Default to modification if parent exists but no strong indicators
    return {
        "submission_type": "modification",
        "confidence": 0.5,
        "reasoning": "Parent submission exists; assuming modification by default",
        "key_indicators": ["parent_exists", "no_strong_indicators"]
    }


def should_request_hitl_confirmation(classification: Dict, threshold: float = 0.8) -> bool:
    """
    Determine if HITL (Human-in-the-Loop) confirmation is needed.

    Args:
        classification: Classification result from classify_submission_type()
        threshold: Confidence threshold below which to request human confirmation

    Returns:
        True if confidence < threshold (needs human review)
    """
    return classification["confidence"] < threshold
