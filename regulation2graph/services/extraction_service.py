"""Сервис извлечения триплетов из текста регламента."""

from regulation2graph.core import RuleBasedExtractor
from regulation2graph.models import Triplet


def extract_process(text: str) -> list[Triplet]:
    """Извлекает шаги процесса из текста.

    Args:
        text: Текст регламента.

    Returns:
        Список извлечённых триплетов.
    """
    extractor = RuleBasedExtractor()
    return extractor.parse_text(text)


def print_results(triplets: list[Triplet]) -> None:
    """Выводит извлечённые шаги в консоль.

    Args:
        triplets: Список триплетов для отображения.
    """
    print(f"\nИзвлечено {len(triplets)} шагов процесса:\n")
    for i, t in enumerate(triplets, 1):
        condition_info = f" [Условие: {t.condition_text}]" if t.has_condition else ""
        alt_info = " [Альтернатива]" if t.is_alternative else ""
        print(f"  {i}. {t.actor} → {t.action} → {t.obj}{condition_info}{alt_info}")
