"""
Маркеры альтернативных веток (alternative markers).

Слова и фразы, указывающие на альтернативный путь выполнения:
- "иначе", "в противном случае", "если нет" и т.д.

Используются для детекции IF_FALSE ветки после XOR-split.
"""

from __future__ import annotations

# Маркеры альтернатив — frozenset для быстрой проверки вхождения
# Все маркеры в нижнем регистре
ALTERNATIVE_MARKERS: frozenset[str] = frozenset({
    # Базовые
    "иначе",
    "иначе же",

    # Составные с "случае"
    "в противном случае",
    "в ином случае",
    "в обратном случае",
    "в другом случае",

    # Составные с "если"
    "если нет",
    "если же нет",
    "если не",

    # Составные с "при"
    "при невыполнении",
    "при несоблюдении",
    "при отсутствии",
    "при отклонении",
    "при отказе",

    # Другие
    "в остальных случаях",
    "во всех остальных случаях",
    "при других обстоятельствах",
    "в любом другом случае",
})

# Маркеры, отсортированные по длине (от длинных к коротким)
ALTERNATIVE_MARKERS_SORTED: tuple[str, ...] = tuple(
    sorted(ALTERNATIVE_MARKERS, key=len, reverse=True)
)


def is_alternative_marker(text: str) -> bool:
    """
    Проверяет, является ли текст маркером альтернативы.

    Args:
        text: Текст для проверки (будет приведён к нижнему регистру).

    Returns:
        True если текст — маркер альтернативы.
    """
    return text.lower().strip() in ALTERNATIVE_MARKERS


def extract_alternative_marker(text: str) -> str | None:
    """
    Извлекает маркер альтернативы из начала текста.

    Args:
        text: Текст, возможно начинающийся с маркера альтернативы.

    Returns:
        Найденный маркер или None.

    Example:
        >>> extract_alternative_marker("Иначе секретарь возвращает")
        'иначе'
        >>> extract_alternative_marker("В противном случае заявка отклоняется")
        'в противном случае'
    """
    text_lower = text.lower().strip()

    for marker in ALTERNATIVE_MARKERS_SORTED:
        if text_lower.startswith(marker):
            # Проверяем, что после маркера идёт пробел или конец строки
            rest = text_lower[len(marker):]
            if not rest or rest[0].isspace() or rest[0] in ",:;":
                return marker

    return None


def strip_alternative_marker(text: str) -> str:
    """
    Удаляет маркер альтернативы из начала текста.

    Args:
        text: Текст, возможно начинающийся с маркера альтернативы.

    Returns:
        Текст без маркера (с сохранением регистра остальной части).

    Example:
        >>> strip_alternative_marker("Иначе секретарь возвращает")
        'секретарь возвращает'
    """
    marker = extract_alternative_marker(text)
    if marker:
        return text[len(marker):].lstrip(" ,:")
    return text
