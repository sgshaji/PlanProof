"""
LLM Gate module: Use Azure OpenAI to resolve validation issues when deterministic rules fail.
"""

from __future__ import annotations

from typing import Dict, Any, List, Optional, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from planproof.aoai import AzureOpenAIClient
    from planproof.db import Database
    from planproof.docintel import DocumentIntelligence
from planproof.config import get_settings


def resolve_with_llm(
    document_id: int,
    field_name: Optional[str] = None,
    min_confidence_threshold: float = 0.7,
    aoai_client: Optional[AzureOpenAIClient] = None,
    db: Optional[Database] = None,
    docintel: Optional[DocumentIntelligence] = None
) -> List[Dict[str, Any]]:
    """
    Use LLM to resolve validation issues for fields that:
    - Are missing
    - Have conflicts
    - Have low confidence scores

    Args:
        document_id: Document ID
        field_name: Optional specific field to resolve. If None, resolves all fields needing review.
        min_confidence_threshold: Minimum confidence threshold (default: 0.7)
        aoai_client: Optional AzureOpenAIClient instance
        db: Optional Database instance
        docintel: Optional DocumentIntelligence instance (for context extraction)

    Returns:
        List of resolution results
    """
    from planproof.aoai import AzureOpenAIClient
    from planproof.db import Database, Document, ValidationResult, ValidationStatus
    from planproof.pipeline.extract import get_extraction_result

    if aoai_client is None:
        aoai_client = AzureOpenAIClient()
    if db is None:
        db = Database()
    if docintel is None:
        from planproof.docintel import DocumentIntelligence

        docintel = DocumentIntelligence()

    session = db.get_session()
    try:
        # Get document
        document = session.query(Document).filter(Document.id == document_id).first()
        if document is None:
            raise ValueError(f"Document not found: {document_id}")

        # Get validation results that need LLM resolution
        query = session.query(ValidationResult).filter(
            ValidationResult.document_id == document_id,
            ValidationResult.status.in_([
                ValidationStatus.FAIL,
                ValidationStatus.NEEDS_REVIEW,
                ValidationStatus.PENDING
            ])
        )

        if field_name:
            query = query.filter(ValidationResult.field_name == field_name)

        validation_results = query.all()

        if not validation_results:
            return []

        # Get extraction result for context
        extraction_result = get_extraction_result(document_id, db=db)
        if extraction_result is None:
            raise ValueError(f"No extraction result found for document {document_id}")

        # Build document context
        context = _build_document_context(extraction_result, docintel)

        resolution_results = []

        for vr in validation_results:
            # Determine if LLM resolution is needed
            needs_resolution = (
                vr.status == ValidationStatus.FAIL or
                vr.status == ValidationStatus.NEEDS_REVIEW or
                (vr.confidence is not None and vr.confidence < min_confidence_threshold)
            )

            if not needs_resolution:
                continue

            # Get relevant context for this field
            field_context = _get_field_context(vr.field_name, extraction_result, context)

            # Resolve with LLM
            if vr.extracted_value is None or vr.status == ValidationStatus.FAIL:
                # Missing or failed - try to resolve
                resolution = aoai_client.resolve_field_conflict(
                    field_name=vr.field_name,
                    extracted_value=vr.extracted_value or "",
                    context=field_context,
                    validation_issue=vr.error_message or "Field validation failed"
                )

                # Update validation result
                vr.extracted_value = resolution.get("resolved_value") or vr.extracted_value
                vr.confidence = resolution.get("confidence", vr.confidence)
                vr.llm_resolution = resolution.get("reasoning", "")
                vr.updated_at = datetime.utcnow()

                # Update status based on resolution
                if resolution.get("resolved_value"):
                    if resolution.get("confidence", 0) >= min_confidence_threshold:
                        vr.status = ValidationStatus.PASS
                    else:
                        vr.status = ValidationStatus.NEEDS_REVIEW
                else:
                    vr.status = ValidationStatus.FAIL

            else:
                # Low confidence - validate with LLM
                validation_rules = _get_validation_rules_for_field(vr.field_name)
                llm_validation = aoai_client.validate_with_llm(
                    field_name=vr.field_name,
                    extracted_value=vr.extracted_value,
                    validation_rules=validation_rules,
                    document_context=field_context
                )

                # Update validation result
                vr.confidence = llm_validation.get("confidence", vr.confidence)
                vr.llm_resolution = llm_validation.get("reasoning", "")
                vr.updated_at = datetime.utcnow()

                if llm_validation.get("is_valid"):
                    vr.status = ValidationStatus.PASS
                else:
                    vr.status = ValidationStatus.NEEDS_REVIEW
                    if llm_validation.get("suggested_value"):
                        vr.extracted_value = llm_validation["suggested_value"]

            resolution_results.append({
                "field_name": vr.field_name,
                "status": vr.status.value,
                "confidence": vr.confidence,
                "resolved_value": vr.extracted_value,
                "reasoning": vr.llm_resolution
            })

        session.commit()
        return resolution_results

    finally:
        session.close()


def _build_document_context(
    extraction_result: Dict[str, Any],
    docintel: DocumentIntelligence,
    *,
    max_chars: int = 6000,
    max_blocks: int = 80
) -> str:
    """Build a bounded text context from extraction result for LLM."""
    settings = get_settings()
    max_chars = settings.llm_context_max_chars
    max_blocks = settings.llm_context_max_blocks
    text_parts = []

    text_blocks = extraction_result.get("text_blocks", [])
    tables = extraction_result.get("tables", [])

    def _block_priority(block: Dict[str, Any]) -> int:
        role = block.get("role", "")
        if role in ["title", "sectionHeading"]:
            return 0
        return 1

    sorted_blocks = sorted(text_blocks, key=_block_priority)[:max_blocks]
    for block in sorted_blocks:
        content = block.get("content", "")
        if not content:
            continue
        role = block.get("role", "")
        if role in ["title", "sectionHeading"]:
            text_parts.append(f"## {content}")
        else:
            text_parts.append(content)
        if sum(len(part) for part in text_parts) >= max_chars:
            break

    if sum(len(part) for part in text_parts) < max_chars:
        for table in tables[:10]:
            table_text = []
            for cell in table.get("cells", [])[:30]:
                if cell.get("content"):
                    table_text.append(cell["content"])
            if table_text:
                text_parts.append(" | ".join(table_text))
            if sum(len(part) for part in text_parts) >= max_chars:
                break

    return "\n\n".join(text_parts)[:max_chars]


def _get_field_context(
    field_name: str,
    extraction_result: Dict[str, Any],
    full_context: str,
    *,
    max_chars: int = 4000,
    max_blocks: int = 30
) -> str:
    """Get relevant context for a specific field with lightweight retrieval."""
    settings = get_settings()
    max_chars = settings.llm_field_context_max_chars
    max_blocks = settings.llm_field_context_max_blocks
    field_hints = {
        "site_address": "Look for address information, postcodes, street names",
        "proposed_use": "Look for descriptions of proposed development, use classes",
        "application_ref": "Look for application reference numbers, planning references"
    }

    keywords = []
    if field_name:
        keywords.append(field_name.replace("_", " "))
    hint = field_hints.get(field_name, "")
    if hint:
        keywords.extend(hint.lower().split())

    def _score_block(block: Dict[str, Any]) -> int:
        content = (block.get("content") or "").lower()
        return sum(1 for kw in keywords if kw in content)

    blocks = extraction_result.get("text_blocks", [])
    ranked_blocks = sorted(blocks, key=_score_block, reverse=True)[:max_blocks]
    selected = [b.get("content", "") for b in ranked_blocks if b.get("content")]
    context = "\n\n".join(selected)
    if not context:
        context = full_context

    if hint:
        return f"{hint}\n\n{context[:max_chars]}"
    return context[:max_chars]


def _get_validation_rules_for_field(field_name: str) -> str:
    """Get validation rules description for a field (for LLM context)."""
    rules = {
        "site_address": "Site address must be a valid UK address with postcode",
        "proposed_use": "Proposed use must be clearly stated and match planning use classes",
        "application_ref": "Application reference must follow format APP/YYYY/NNNN"
    }

    return rules.get(field_name, f"Field {field_name} must be valid and complete")


# Field ownership: which doc types can extract which fields
DOC_FIELD_OWNERSHIP = {
    "application_form": {"application_ref", "site_address", "postcode", "proposed_use", "applicant_name", "agent_name", "applicant_phone", "applicant_email"},
    "site_notice": {"site_address", "postcode", "proposed_use"},  # Supporting evidence, not primary source
    "site_plan": {"site_address", "postcode"},  # Optional - may not always have address
    "drawing": {"proposed_use"},  # Drawings might have use descriptions
    "design_statement": {"proposed_use", "site_address"},
    "unknown": {"site_address", "proposed_use"},  # Fallback
}


def should_trigger_llm(
    validation: Dict[str, Any],
    extraction: Dict[str, Any],
    resolved_fields: Optional[Dict[str, Any]] = None,
    application_ref: Optional[str] = None,
    submission_id: Optional[int] = None,
    db: Optional[Database] = None
) -> bool:
    """
    Check if LLM resolution should be triggered based on validation results.
    
    Only triggers if:
    - Missing field is extractable from THIS doc type (field ownership)
    - Doc has enough text coverage
    - At least one rule is blocking (severity error) - warnings don't trigger
    - Field hasn't already been resolved earlier in the submission/application (application-level cache)
    
    Args:
        validation: Validation result dictionary
        extraction: Extraction result dictionary
        resolved_fields: Resolved fields from current submission (optional)
        application_ref: Application reference for application-level cache lookup (optional)
        submission_id: Submission ID for submission-level cache lookup (optional, preferred)
        db: Database instance for cache lookup (optional)
    """
    resolved_fields = resolved_fields or {}
    
    # If submission_id is provided, check submission-level cache (preferred)
    if submission_id and db:
        submission_resolved = db.get_resolved_fields_for_submission(submission_id)
        resolved_fields = {**submission_resolved, **resolved_fields}  # Merge, current submission takes precedence
    
    # If application_ref is provided, check application-level cache (fallback)
    elif application_ref and db:
        app_resolved = db.get_resolved_fields_for_application(application_ref)
        resolved_fields = {**app_resolved, **resolved_fields}  # Merge, current submission takes precedence
    
    # Check if needs_llm flag is set
    if not validation.get("summary", {}).get("needs_llm"):
        return False
    
    # Get document type
    doc_type = extraction.get("fields", {}).get("document_type", "unknown")
    
    # Get missing fields from validation findings (only errors, not warnings)
    missing_fields = []
    has_error_severity = False
    
    for finding in validation.get("findings", []):
        # Only consider error severity for LLM trigger
        if finding.get("severity") != "error":
            continue
            
        if finding.get("status") in ["needs_review", "fail"]:
            missing = finding.get("missing_fields", [])
            # Skip if field already resolved
            missing = [f for f in missing if f not in resolved_fields]
            missing_fields.extend(missing)
            has_error_severity = True
    
    if not missing_fields or not has_error_severity:
        return False
    
    # Check field ownership: only extract fields this doc type can provide
    allowed_fields = DOC_FIELD_OWNERSHIP.get(doc_type, set())
    missing_allowed = [f for f in missing_fields if f in allowed_fields]
    
    if not missing_allowed:
        return False
    
    # Check text coverage (at least some text blocks)
    text_blocks = extraction.get("text_blocks", [])
    if len(text_blocks) < 5:  # Too little text to justify LLM
        return False
    
    return True


def build_llm_prompt(extraction: Dict[str, Any], validation: Dict[str, Any]) -> Dict[str, Any]:
    """Build LLM prompt for resolving missing fields."""
    # Keep it schema-bound: ask for missing fields only.
    missing_fields: List[str] = []
    for f in validation.get("findings", []):
        missing_fields.extend(f.get("missing_fields", []))
    missing_fields = sorted(set(missing_fields))

    return {
        "task": "Fill missing structured fields from extracted evidence only. If not found, return null.",
        "missing_fields": missing_fields,
        "extraction_fields": extraction.get("fields", {}),
        "evidence_index": extraction.get("evidence_index", {}),
        "return_schema": {
            "filled_fields": {k: "string|number|object|null" for k in missing_fields},
            "notes": "string",
            "citations": [
                {
                    "field": "string",
                    "evidence_key": "string",
                    "page": "number",
                    "quote": "string"
                }
            ],
        },
    }


def resolve_with_llm_new(extraction: Dict[str, Any], validation: Dict[str, Any], aoai_client: Optional[AzureOpenAIClient] = None) -> Dict[str, Any]:
    """
    Use LLM to resolve missing fields from extraction and validation results.

    Now with graceful degradation: if LLM fails, marks fields as needs_review
    instead of silently continuing.

    Args:
        extraction: Extraction result dictionary
        validation: Validation result dictionary
        aoai_client: Optional AzureOpenAIClient instance

    Returns:
        Dictionary with triggered flag, request, response, gate logging info, llm_call_count, and status
    """
    import logging
    from datetime import datetime, timezone

    LOGGER = logging.getLogger(__name__)

    if aoai_client is None:
        from planproof.aoai import AzureOpenAIClient
        aoai_client = AzureOpenAIClient()

    # Get call count before the LLM call
    call_count_before = aoai_client.get_call_count()

    # Collect missing fields and affected rule IDs for logging
    missing_fields: List[str] = []
    affected_rule_ids: List[str] = []

    for finding in validation.get("findings", []):
        if finding.get("status") in ["needs_review", "fail"]:
            missing = finding.get("missing_fields", [])
            missing_fields.extend(missing)
            rule_id = finding.get("rule_id")
            if rule_id:
                affected_rule_ids.append(rule_id)

    missing_fields = sorted(set(missing_fields))
    affected_rule_ids = sorted(set(affected_rule_ids))

    try:
        prompt_obj = build_llm_prompt(extraction, validation)
        response_payload = aoai_client.chat_json_with_metadata(prompt_obj)
        resp = response_payload.get("data", {})
        call_metadata = response_payload.get("metadata") or {}

        # Get call count after the LLM call
        call_count_after = aoai_client.get_call_count()
        llm_calls_made = call_count_after - call_count_before
        llm_call_details = []
        if call_metadata:
            llm_call_details.append({
                "timestamp": call_metadata.get("timestamp"),
                "purpose": "Resolve missing fields",
                "rule_type": "llm_gate",
                "tokens_used": call_metadata.get("tokens_used", 0),
                "model": call_metadata.get("model"),
                "response_time_ms": call_metadata.get("response_time_ms", 0)
            })

        return {
            "triggered": True,
            "gate_reason": {
                "missing_fields": missing_fields,
                "affected_rule_ids": affected_rule_ids,
                "validation_summary": validation.get("summary", {})
            },
            "request": prompt_obj,
            "response": resp,
            "llm_call_count": llm_calls_made,
            "llm_calls": llm_call_details,
            "status": "success"
        }

    except Exception as e:
        # 🛑 GRACEFUL DEGRADATION: Don't silently continue!
        LOGGER.error(f"LLM resolution failed: {e}", exc_info=True)

        # Mark fields as needs_review instead of losing data
        return {
            "triggered": True,
            "gate_reason": {
                "missing_fields": missing_fields,
                "affected_rule_ids": affected_rule_ids,
                "validation_summary": validation.get("summary", {})
            },
            "request": None,
            "response": {
                "filled_fields": {},  # Empty - LLM failed
                "citations": [],
                "needs_review": missing_fields,  # ← Flag all fields for officer review
                "error": str(e)
            },
            "llm_call_count": 0,
            "llm_calls": [],
            "status": "failed",
            "error_details": {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "affected_fields": missing_fields
            }
        }


def resolve_low_confidence_extractions(
    extraction: Dict[str, Any],
    min_confidence: float = 0.7,
    aoai_client: Optional[AzureOpenAIClient] = None,
    db: Optional[Database] = None
) -> Dict[str, Any]:
    """
    Use LLM to verify or improve low-confidence field extractions.
    
    Args:
        extraction: Extraction result with fields and confidence scores
        min_confidence: Minimum acceptable confidence threshold (default: 0.7)
        aoai_client: Optional AzureOpenAIClient instance
        db: Optional Database instance
        
    Returns:
        Dictionary with improved fields and updated confidence scores
    """
    if aoai_client is None:
        from planproof.aoai import AzureOpenAIClient
        aoai_client = AzureOpenAIClient()
    
    fields = extraction.get("fields", {})
    evidence_index = extraction.get("evidence_index", {})
    
    # Find low-confidence fields
    low_confidence_fields = {}
    for field_key, evidence_list in evidence_index.items():
        if isinstance(evidence_list, list):
            for evidence in evidence_list:
                confidence = evidence.get("confidence", 1.0)
                if confidence < min_confidence:
                    field_value = fields.get(field_key)
                    if field_value:
                        low_confidence_fields[field_key] = {
                            "value": field_value,
                            "confidence": confidence,
                            "evidence": evidence
                        }
                        break
    
    if not low_confidence_fields:
        return {
            "improved_fields": {},
            "unchanged_fields": list(fields.keys()),
            "llm_triggered": False
        }
    
    # Build LLM prompt for verification
    prompt = {
        "task": "Verify and improve low-confidence field extractions. Confirm if values are correct or suggest better values.",
        "low_confidence_fields": {
            k: {"value": v["value"], "confidence": v["confidence"]}
            for k, v in low_confidence_fields.items()
        },
        "document_context": _build_document_context(extraction, None, max_chars=4000, max_blocks=50),
        "return_schema": {
            "verified_fields": {
                "field_name": "string",
                "original_value": "string",
                "improved_value": "string or null if no improvement",
                "confidence": "float 0-1",
                "reasoning": "string"
            }
        }
    }
    
    response = aoai_client.chat_json(prompt)
    
    improved_fields = {}
    for field_data in response.get("verified_fields", []):
        field_name = field_data.get("field_name")
        improved_value = field_data.get("improved_value")
        new_confidence = field_data.get("confidence", 0.8)
        
        if improved_value and improved_value != field_data.get("original_value"):
            improved_fields[field_name] = {
                "old_value": field_data.get("original_value"),
                "new_value": improved_value,
                "confidence": new_confidence,
                "reasoning": field_data.get("reasoning", "")
            }
            
            # Update fields in extraction
            fields[field_name] = improved_value
            
            # Update evidence index with new confidence
            if field_name in evidence_index and isinstance(evidence_index[field_name], list):
                for evidence in evidence_index[field_name]:
                    evidence["confidence"] = new_confidence
    
    return {
        "improved_fields": improved_fields,
        "unchanged_fields": [k for k in low_confidence_fields.keys() if k not in improved_fields],
        "llm_triggered": True,
        "total_checked": len(low_confidence_fields),
        "total_improved": len(improved_fields)
    }


def resolve_field_conflicts(
    document_id: int,
    submission_id: Optional[int] = None,
    aoai_client: Optional[AzureOpenAIClient] = None,
    db: Optional[Database] = None
) -> Dict[str, Any]:
    """
    Use LLM to resolve conflicting field values from multiple documents.
    
    Args:
        document_id: Primary document ID
        submission_id: Optional submission ID to check all documents
        aoai_client: Optional AzureOpenAIClient instance
        db: Optional Database instance
        
    Returns:
        Dictionary with resolved conflicts
    """
    if aoai_client is None:
        from planproof.aoai import AzureOpenAIClient
        aoai_client = AzureOpenAIClient()
    
    if db is None:
        from planproof.db import Database
        db = Database()
    
    from planproof.db import ExtractedField, Document
    
    session = db.get_session()
    try:
        # Get all extracted fields for submission (if provided) or just this document
        if submission_id:
            extracted_fields = session.query(ExtractedField).filter(
                ExtractedField.submission_id == submission_id
            ).all()
        else:
            extracted_fields = session.query(ExtractedField).filter(
                ExtractedField.document_id == document_id
            ).all()
        
        # Group by field name to find conflicts
        field_groups = {}
        for ef in extracted_fields:
            if ef.field_name not in field_groups:
                field_groups[ef.field_name] = []
            field_groups[ef.field_name].append(ef)
        
        # Find conflicts (multiple different values for same field)
        conflicts = {}
        for field_name, field_list in field_groups.items():
            unique_values = {}
            for ef in field_list:
                value = ef.field_value
                if value not in unique_values:
                    unique_values[value] = []
                unique_values[value].append(ef)
            
            if len(unique_values) > 1:
                # Get document names for context
                doc_context = []
                for value, efs in unique_values.items():
                    for ef in efs:
                        doc = session.query(Document).filter(Document.id == ef.document_id).first()
                        doc_context.append({
                            "value": value,
                            "document": doc.filename if doc else f"doc_{ef.document_id}",
                            "document_type": doc.document_type if doc else "unknown",
                            "confidence": ef.confidence
                        })
                
                conflicts[field_name] = {
                    "values": list(unique_values.keys()),
                    "context": doc_context
                }
        
        if not conflicts:
            return {
                "conflicts_found": 0,
                "resolved_conflicts": {},
                "llm_triggered": False
            }
        
        # Build LLM prompt for conflict resolution
        prompt = {
            "task": "Resolve conflicting field values from multiple documents. Select the most reliable value or suggest a merged value.",
            "conflicts": conflicts,
            "return_schema": {
                "resolutions": [
                    {
                        "field_name": "string",
                        "selected_value": "string",
                        "confidence": "float 0-1",
                        "reasoning": "string explanation of why this value was selected"
                    }
                ]
            }
        }
        
        response = aoai_client.chat_json(prompt)
        
        resolved_conflicts = {}
        for resolution in response.get("resolutions", []):
            field_name = resolution.get("field_name")
            selected_value = resolution.get("selected_value")
            confidence = resolution.get("confidence", 0.8)
            reasoning = resolution.get("reasoning", "")
            
            resolved_conflicts[field_name] = {
                "selected_value": selected_value,
                "confidence": confidence,
                "reasoning": reasoning,
                "original_values": conflicts[field_name]["values"]
            }
        
        return {
            "conflicts_found": len(conflicts),
            "resolved_conflicts": resolved_conflicts,
            "llm_triggered": True
        }
    
    finally:
        session.close()
