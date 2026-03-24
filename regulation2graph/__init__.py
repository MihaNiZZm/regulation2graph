"""
Regulation2Graph - автоматическое моделирование бизнес-процессов из текстов регламентов.

Основные компоненты:
- RuleBasedExtractor: Извлечение триплетов из текста
- GraphVisualizer: Визуализация графа процесса
- Triplet: Модель данных для представления действия

Example:
    >>> from regulation2graph import RuleBasedExtractor, GraphVisualizer
    >>>
    >>> extractor = RuleBasedExtractor()
    >>> triplets = extractor.parse_text("Менеджер проверяет заявку.")
    >>>
    >>> viz = GraphVisualizer()
    >>> viz.build_and_show(triplets)
"""

from regulation2graph.core import RuleBasedExtractor
from regulation2graph.graph import GraphVisualizer
from regulation2graph.models import Triplet

__version__ = "0.1.0"
__all__ = ["RuleBasedExtractor", "GraphVisualizer", "Triplet"]
