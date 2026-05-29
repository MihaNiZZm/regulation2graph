"""
Протокол для резолверов кореференции.

Позволяет легко заменять реализации:
- RuleBasedResolver (лёгкий, CPU)
- RuBertResolver (точный, GPU)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from regulation2graph.core.coreference.models import CoreferenceResult


@runtime_checkable
class CoreferenceResolver(Protocol):
    """
    Протокол для резолверов кореференции.

    Все резолверы должны реализовывать метод `resolve`,
    который принимает текст и возвращает CoreferenceResult.

    Example:
        >>> resolver: CoreferenceResolver = RuleBasedResolver()
        >>> result = resolver.resolve("Менеджер проверяет. Он подписывает.")
        >>> result.resolved_text
        'Менеджер проверяет. Менеджер подписывает.'
    """

    def resolve(self, text: str) -> CoreferenceResult:
        """
        Разрешает кореференции в тексте.

        Заменяет местоимения (он, она, они, его, её, их)
        на их антецеденты (существительные, на которые они ссылаются).

        Args:
            text: Текст регламента.

        Returns:
            CoreferenceResult с исходным текстом, разрешённым текстом
            и кластерами кореференции.
        """
        ...
