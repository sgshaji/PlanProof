"""Synthetic planning document generation using Azure OpenAI.

Generates planning application documents with known ground truth
for evaluation purposes. Supports three variation modes:
  - "standard": Complete, consistent documents
  - "incomplete": Documents with deliberately missing fields
  - "conflicting": Documents with deliberate inconsistencies
"""

import json
import logging
import os
from dataclasses import dataclass, asdict
from typing import Optional

from openai import AzureOpenAI

from research.config import ResearchConfig
from research.evaluation.ground_truth import (
    GroundTruthAnnotation,
    GroundTruthEntity,
    GroundTruthRelationship,
    GroundTruthConflict,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a planning application document generator for Birmingham City Council.
Generate realistic UK planning application data including:
- Site address (Birmingham area)
- Applicant details
- Proposal description
- Room measurements (area in sqm, heights in metres)
- Site boundary distances
- Building dimensions

Output JSON with these keys:
- fields: dict of field_name -> value
- measurements: list of {entity, context, value, unit}
- entities: list of {entity_id, entity_type, label, properties}
- relationships: list of {source_id, target_id, relationship_type}
"""

VARIATION_PROMPTS = {
    "standard": "Generate a complete, internally consistent householder planning application.",
    "incomplete": (
        "Generate a householder planning application with 3-4 fields deliberately "
        "left blank or marked as 'N/A'. The missing fields should include at least "
        "one critical measurement (area or height)."
    ),
    "conflicting": (
        "Generate a householder planning application where the form states a different "
        "room area than the drawings. Include at least 2 measurement conflicts: "
        "one area conflict and one height conflict. In the output JSON, add a "
        "'conflicts' list with {conflict_type, field_name, value_a, value_b, severity}."
    ),
}


@dataclass
class SyntheticDocument:
    """A synthetically generated planning document."""

    doc_id: str
    variation: str  # "standard", "incomplete", "conflicting"
    fields: dict
    measurements: list[dict]
    ground_truth: GroundTruthAnnotation


def generate_synthetic_document(
    variation: str = "standard",
    submission_id: int = -1,
    config: Optional[ResearchConfig] = None,
) -> SyntheticDocument:
    """Generate a synthetic planning document using Azure OpenAI.

    Args:
        variation: One of "standard", "incomplete", "conflicting".
        submission_id: Synthetic submission ID (negative to distinguish from real).
        config: Research configuration.

    Returns:
        SyntheticDocument with fields, measurements, and ground truth.
    """
    cfg = config or ResearchConfig()

    if not cfg.azure_openai_endpoint or not cfg.azure_openai_api_key:
        raise ValueError(
            "Azure OpenAI credentials not configured. "
            "Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY."
        )

    client = AzureOpenAI(
        azure_endpoint=cfg.azure_openai_endpoint,
        api_key=cfg.azure_openai_api_key,
        api_version=cfg.azure_openai_api_version,
    )

    user_prompt = VARIATION_PROMPTS.get(variation, VARIATION_PROMPTS["standard"])

    response = client.chat.completions.create(
        model=cfg.azure_openai_chat_deployment,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.8,
        max_tokens=2000,
        response_format={"type": "json_object"},
    )

    raw = json.loads(response.choices[0].message.content)

    # Build ground truth from LLM output
    entities = [
        GroundTruthEntity(
            entity_id=e["entity_id"],
            entity_type=e["entity_type"],
            label=e["label"],
            properties=e.get("properties", {}),
            match_key=e.get("label", ""),
        )
        for e in raw.get("entities", [])
    ]

    relationships = [
        GroundTruthRelationship(
            source_id=r["source_id"],
            target_id=r["target_id"],
            relationship_type=r["relationship_type"],
        )
        for r in raw.get("relationships", [])
    ]

    conflicts = []
    if variation == "conflicting":
        for c in raw.get("conflicts", []):
            conflicts.append(GroundTruthConflict(
                conflict_id=f"synth_{c.get('field_name', 'unknown')}",
                conflict_type=c.get("conflict_type", "value"),
                entity_a_id=c.get("entity_a_id", ""),
                entity_b_id=c.get("entity_b_id", ""),
                field_name=c.get("field_name", ""),
                value_a=str(c.get("value_a", "")),
                value_b=str(c.get("value_b", "")),
                severity=c.get("severity", "medium"),
            ))

    from datetime import date
    ground_truth = GroundTruthAnnotation(
        submission_id=submission_id,
        annotator="synthetic_generator",
        annotation_date=date.today().isoformat(),
        is_synthetic=True,
        source="synthetic",
        entities=entities,
        relationships=relationships,
        conflicts=conflicts,
    )

    doc = SyntheticDocument(
        doc_id=f"synth_{abs(submission_id)}",
        variation=variation,
        fields=raw.get("fields", {}),
        measurements=raw.get("measurements", []),
        ground_truth=ground_truth,
    )

    logger.info(
        "Generated synthetic doc %s (variation=%s): %d entities, %d rels, %d conflicts",
        doc.doc_id, variation, len(entities), len(relationships), len(conflicts),
    )
    return doc


def generate_batch(
    n_standard: int = 5,
    n_incomplete: int = 3,
    n_conflicting: int = 3,
    config: Optional[ResearchConfig] = None,
) -> list[SyntheticDocument]:
    """Generate a batch of synthetic documents across all variations."""
    docs = []
    sid = -1

    for i in range(n_standard):
        docs.append(generate_synthetic_document("standard", sid, config))
        sid -= 1

    for i in range(n_incomplete):
        docs.append(generate_synthetic_document("incomplete", sid, config))
        sid -= 1

    for i in range(n_conflicting):
        docs.append(generate_synthetic_document("conflicting", sid, config))
        sid -= 1

    logger.info("Generated batch of %d synthetic documents", len(docs))
    return docs
