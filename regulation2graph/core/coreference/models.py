"""
Модели данных для разрешения кореференции.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Mention:
    """Упоминание сущности в тексте."""

    text: str  # Текст упоминания ("менеджер", "он")
    start: int  # Начальная позиция в тексте
    end: int  # Конечная позиция в тексте

    def __post_init__(self) -> None:
        if self.start < 0 or self.end < self.start:
            raise ValueError(f"Invalid span: [{self.start}, {self.end})")


@dataclass(frozen=True)
class CoreferenceCluster:
    """
    Кластер упоминаний одной сущности.

    Содержит все упоминания (mentions) одной и той же сущности,
    включая местоимения и именные группы.

    Example:
        >>> cluster = CoreferenceCluster(
        ...     mentions=(
        ...         Mention("Менеджер", 0, 8),
        ...         Mention("он", 25, 27),
        ...     ),
        ...     head_index=0,
        ... )
        >>> cluster.head
        Mention(text='Менеджер', start=0, end=8)
    """

    mentions: tuple[Mention, ...]  # Все упоминания сущности
    head_index: int = 0  # Индекс главного упоминания (антецедента)

    @property
    def head(self) -> Mention:
        """Главное упоминание (антецедент)."""
        return self.mentions[self.head_index]

    def __post_init__(self) -> None:
        if not self.mentions:
            raise ValueError("Cluster must have at least one mention")
        if not 0 <= self.head_index < len(self.mentions):
            raise ValueError(f"Invalid head_index: {self.head_index}")


@dataclass(frozen=True)
class CoreferenceResult:
    """
    Результат разрешения кореференции.

    Содержит исходный текст, текст с заменёнными местоимениями,
    и кластеры кореференции.

    Example:
        >>> result = CoreferenceResult(
        ...     original_text="Менеджер проверяет. Он подписывает.",
        ...     resolved_text="Менеджер проверяет. Менеджер подписывает.",
        ...     clusters=(cluster,),
        ... )
    """

    original_text: str  # Исходный текст
    resolved_text: str  # Текст с заменёнными местоимениями
    clusters: tuple[CoreferenceCluster, ...]  # Кластеры кореференции

    @property
    def has_coreferences(self) -> bool:
        """Есть ли в тексте кореференции."""
        return len(self.clusters) > 0

    @property
    def was_modified(self) -> bool:
        """Был ли текст изменён."""
        return self.original_text != self.resolved_text
