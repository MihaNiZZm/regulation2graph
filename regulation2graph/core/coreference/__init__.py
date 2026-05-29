"""
Модуль разрешения кореференции для русского языка.

Поддерживает:
- Личные местоимения: он, она, они, оно
- Притяжательные местоимения: его, её, их

Текущая реализация:
- RuleBasedResolver: быстрый, без GPU, на pymorphy3

TODO: Интеграция RuCoBERT для более точного разрешения кореференции.

Пример использования:
    >>> from regulation2graph.core.coreference import create_resolver
    >>> resolver = create_resolver()
    >>> result = resolver.resolve("Менеджер проверяет. Он подписывает.")
    >>> result.resolved_text
    'Менеджер проверяет. Менеджер подписывает.'
"""

from __future__ import annotations

from typing import Literal

from regulation2graph.core.coreference.models import (
    CoreferenceCluster,
    CoreferenceResult,
    Mention,
)
from regulation2graph.core.coreference.protocol import CoreferenceResolver
from regulation2graph.core.coreference.rule_based import RuleBasedResolver


def create_resolver(
    backend: Literal["rules"] = "rules",
) -> CoreferenceResolver:
    """
    Создаёт резолвер кореференции.

    Args:
        backend: Выбор резолвера ("rules" — единственный доступный).

    Returns:
        Экземпляр CoreferenceResolver.

    Example:
        >>> resolver = create_resolver()
        >>> result = resolver.resolve("Менеджер проверяет. Он подписывает.")
    """
    if backend == "rules":
        return RuleBasedResolver()

    raise ValueError(f"Unknown backend: {backend}")


def resolve_coreferences(
    text: str,
    backend: Literal["rules"] = "rules",
) -> str:
    """
    Удобная функция для быстрого резолва кореференций.

    Args:
        text: Текст для обработки.
        backend: Выбор резолвера.

    Returns:
        Текст с заменёнными местоимениями.

    Example:
        >>> resolve_coreferences("Менеджер проверяет. Он подписывает.")
        'Менеджер проверяет. Менеджер подписывает.'
    """
    resolver = create_resolver(backend=backend)
    result = resolver.resolve(text)
    return result.resolved_text


__all__ = [
    # Протокол
    "CoreferenceResolver",
    # Модели данных
    "CoreferenceResult",
    "CoreferenceCluster",
    "Mention",
    # Резолверы
    "RuleBasedResolver",
    # Фабрика
    "create_resolver",
    # Удобная функция
    "resolve_coreferences",
]
