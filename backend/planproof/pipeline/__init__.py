"""
PlanProof pipeline modules for document processing workflow.
"""

from __future__ import annotations

import importlib
from typing import Any

__all__ = [
    "ingest_pdf",
    "ingest_folder",
    "extract_document",
    "validate_document",
    "resolve_with_llm",
]

_LAZY_IMPORTS = {
    "ingest_pdf": ("planproof.pipeline.ingest", "ingest_pdf"),
    "ingest_folder": ("planproof.pipeline.ingest", "ingest_folder"),
    "extract_document": ("planproof.pipeline.extract", "extract_document"),
    "validate_document": ("planproof.pipeline.validate", "validate_document"),
    "resolve_with_llm": ("planproof.pipeline.llm_gate", "resolve_with_llm"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_IMPORTS:
        module_name, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_name)
        return getattr(module, attr_name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(list(globals().keys()) + list(_LAZY_IMPORTS.keys()))
