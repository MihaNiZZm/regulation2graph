"""Core extraction logic."""

from regulation2graph.core.coreference import (
    CoreferenceResolver,
    CoreferenceResult,
    RuleBasedResolver,
    create_resolver,
    resolve_coreferences,
)
from regulation2graph.core.extractor import RuleBasedExtractor

__all__ = [
    # Extractor
    "RuleBasedExtractor",
    # Coreference
    "CoreferenceResolver",
    "CoreferenceResult",
    "RuleBasedResolver",
    "create_resolver",
    "resolve_coreferences",
]
