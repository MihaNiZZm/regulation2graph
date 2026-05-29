"""
Модуль маркеров для детекции структурных элементов регламентов.

Маркеры — это слова и фразы, указывающие на:
- Условия (condition): "если", "когда", "в случае"
- Альтернативы (alternative): "иначе", "в противном случае"
- Циклы (loop): "пока не", "до тех пор" (TODO)

Пример использования:
    >>> from regulation2graph.markers import MarkerDetector
    >>> detector = MarkerDetector()
    >>> detector.detect_condition("Если документ согласован, менеджер подписывает")
    ConditionMatch(marker='если', text='документ согласован')
"""

from __future__ import annotations

from dataclasses import dataclass

from regulation2graph.markers.alternative import (
    ALTERNATIVE_MARKERS,
    ALTERNATIVE_MARKERS_SORTED,
    extract_alternative_marker,
    is_alternative_marker,
    strip_alternative_marker,
)
from regulation2graph.markers.condition import (
    CONDITION_MARKERS,
    CONDITION_MARKERS_SORTED,
    extract_condition_marker,
    is_condition_marker,
    strip_condition_marker,
)
from regulation2graph.markers.loop import (
    LOOP_MARKERS,
    LOOP_MARKERS_SORTED,
    contains_loop_marker,
    extract_loop_marker,
    is_loop_marker,
)


@dataclass(frozen=True)
class ConditionMatch:
    """Результат детекции маркера условия."""

    marker: str  # Найденный маркер ("если", "в случае" и т.д.)
    remaining_text: str  # Текст после маркера


@dataclass(frozen=True)
class AlternativeMatch:
    """Результат детекции маркера альтернативы."""

    marker: str  # Найденный маркер ("иначе", "в противном случае" и т.д.)
    remaining_text: str  # Текст после маркера


@dataclass(frozen=True)
class LoopMatch:
    """Результат детекции маркера цикла."""

    marker: str  # Найденный маркер ("пока не", "до тех пор" и т.д.)
    remaining_text: str  # Текст после маркера


class MarkerDetector:
    """
    Единый интерфейс для детекции маркеров.

    Предоставляет методы для обнаружения условий, альтернатив и циклов
    в тексте регламентов.

    Example:
        >>> detector = MarkerDetector()
        >>> match = detector.detect_condition("Если заявка одобрена, менеджер подписывает")
        >>> match.marker
        'если'
        >>> match.remaining_text
        'заявка одобрена, менеджер подписывает'
    """

    def detect_condition(self, text: str) -> ConditionMatch | None:
        """
        Обнаруживает маркер условия в начале текста.

        Args:
            text: Текст для анализа.

        Returns:
            ConditionMatch если маркер найден, иначе None.
        """
        marker = extract_condition_marker(text)
        if marker:
            remaining = strip_condition_marker(text)
            return ConditionMatch(marker=marker, remaining_text=remaining)
        return None

    def detect_alternative(self, text: str) -> AlternativeMatch | None:
        """
        Обнаруживает маркер альтернативы в начале текста.

        Args:
            text: Текст для анализа.

        Returns:
            AlternativeMatch если маркер найден, иначе None.
        """
        marker = extract_alternative_marker(text)
        if marker:
            remaining = strip_alternative_marker(text)
            return AlternativeMatch(marker=marker, remaining_text=remaining)
        return None

    def detect_loop(self, text: str) -> LoopMatch | None:
        """
        Обнаруживает маркер цикла в начале текста.

        Args:
            text: Текст для анализа.

        Returns:
            LoopMatch если маркер найден, иначе None.

        Note:
            Функция готова, но интеграция в extractor требует
            дополнительной логики резолва целевого узла.
        """
        marker = extract_loop_marker(text)
        if marker:
            remaining = text[len(marker):].lstrip(" ,:")
            return LoopMatch(marker=marker, remaining_text=remaining)
        return None

    def has_any_marker(self, text: str) -> bool:
        """
        Проверяет, начинается ли текст с любого маркера.

        Args:
            text: Текст для анализа.

        Returns:
            True если текст начинается с маркера условия, альтернативы или цикла.
        """
        return (
            self.detect_condition(text) is not None
            or self.detect_alternative(text) is not None
            or self.detect_loop(text) is not None
        )


# Публичный API модуля
__all__ = [
    # Классы
    "MarkerDetector",
    "ConditionMatch",
    "AlternativeMatch",
    "LoopMatch",
    # Константы — условия
    "CONDITION_MARKERS",
    "CONDITION_MARKERS_SORTED",
    # Константы — альтернативы
    "ALTERNATIVE_MARKERS",
    "ALTERNATIVE_MARKERS_SORTED",
    # Константы — циклы
    "LOOP_MARKERS",
    "LOOP_MARKERS_SORTED",
    # Функции — условия
    "is_condition_marker",
    "extract_condition_marker",
    "strip_condition_marker",
    # Функции — альтернативы
    "is_alternative_marker",
    "extract_alternative_marker",
    "strip_alternative_marker",
    # Функции — циклы
    "is_loop_marker",
    "extract_loop_marker",
    "contains_loop_marker",
]
