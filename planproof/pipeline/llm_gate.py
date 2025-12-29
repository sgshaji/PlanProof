"""
LLM Gate module: Use Azure OpenAI to resolve validation issues when deterministic rules fail.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from planproof.aoai import AzureOpenAIClient
from planproof.db import Database, Document, ValidationResult, ValidationStatus
from planproof.pipeline.extract import get_extraction_result
from planproof.docintel import DocumentIntelligence


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
    if aoai_client is None:
        aoai_client = AzureOpenAIClient()
    if db is None:
        db = Database()
    if docintel is None:
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
    docintel: DocumentIntelligence
) -> str:
    """Build a text context from extraction result for LLM."""
    text_parts = []

    # Add text blocks (prioritize headings and important content)
    for block in extraction_result.get("text_blocks", []):
        content = block.get("content", "")
        if content:
            role = block.get("role", "")
            if role in ["title", "sectionHeading"]:
                text_parts.append(f"## {content}")
            else:
                text_parts.append(content)

    # Add table summaries
    for table in extraction_result.get("tables", []):
        table_text = []
        for cell in table.get("cells", []):
            if cell.get("content"):
                table_text.append(cell["content"])
        if table_text:
            text_parts.append(" | ".join(table_text))

    return "\n\n".join(text_parts)


def _get_field_context(
    field_name: str,
    extraction_result: Dict[str, Any],
    full_context: str
) -> str:
    """Get relevant context for a specific field."""
    # For now, return full context. In production, you might:
    # - Extract relevant sections based on field name
    # - Use semantic search to find most relevant paragraphs
    # - Include surrounding context from the document

    # Add field-specific hints
    field_hints = {
        "site_address": "Look for address information, postcodes, street names",
        "proposed_use": "Look for descriptions of proposed development, use classes",
        "application_ref": "Look for application reference numbers, planning references"
    }

    hint = field_hints.get(field_name, "")
    if hint:
        return f"{hint}\n\n{full_context}"

    return full_context


def _get_validation_rules_for_field(field_name: str) -> str:
    """Get validation rules description for a field (for LLM context)."""
    rules = {
        "site_address": "Site address must be a valid UK address with postcode",
        "proposed_use": "Proposed use must be clearly stated and match planning use classes",
        "application_ref": "Application reference must follow format APP/YYYY/NNNN"
    }

    return rules.get(field_name, f"Field {field_name} must be valid and complete")

