"""
Regulation2Graph - автоматическое моделирование бизнес-процессов из текстов регламентов.

Основные компоненты:
- RuleBasedExtractor: Извлечение WorkflowNet из текста
- WorkflowNet: Модель бизнес-процесса (Petri Net)
- Neo4jLoader: Сохранение в графовую БД

Example:
    >>> from regulation2graph import RuleBasedExtractor
    >>>
    >>> extractor = RuleBasedExtractor()
    >>> workflow = extractor.extract("Менеджер проверяет заявку.")
    >>> print(workflow.transitions[0].actor)
    'менеджер'
"""

from regulation2graph.core import RuleBasedExtractor
from regulation2graph.graph import Neo4jLoader
from regulation2graph.models import (
    Arc,
    Place,
    PlaceType,
    Transition,
    TransitionType,
    Triplet,
    WorkflowNet,
)

__version__ = "0.2.0"
__all__ = [
    "RuleBasedExtractor",
    "Neo4jLoader",
    "WorkflowNet",
    "Place",
    "PlaceType",
    "Transition",
    "TransitionType",
    "Arc",
    "Triplet",  # Legacy
]
