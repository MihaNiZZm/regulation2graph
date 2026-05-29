"""
Маркеры условий (condition markers).

Слова и фразы, указывающие на условное выполнение действия:
- "если", "когда", "в случае", "при условии" и т.д.

Используются для детекции XOR-split в Workflow Net.
"""

from __future__ import annotations

# Маркеры условий — frozenset для быстрой проверки вхождения
# Все маркеры в нижнем регистре
CONDITION_MARKERS: frozenset[str] = frozenset({
    # Базовые
    "если",
    "когда",

    # Составные с "случае"
    "в случае",
    "в случае если",
    "в случае когда",
    "в том случае если",
    "в том случае когда",

    # Составные с "условии"
    "при условии",
    "при условии что",
    "при условии если",

    # Составные с "наличии"
    "при наличии",

    # Другие
    "в ситуации когда",
    "в ситуации если",
    "при",  # "при согласовании", "при отклонении"
    "после того как",
    "в момент когда",
})

# Маркеры, отсортированные по длине (от длинных к коротким)
# Важно для корректного извлечения — сначала проверяем длинные фразы
CONDITION_MARKERS_SORTED: tuple[str, ...] = tuple(
    sorted(CONDITION_MARKERS, key=len, reverse=True)
)


def is_condition_marker(text: str) -> bool:
    """
    Проверяет, является ли текст маркером условия.

    Args:
        text: Текст для проверки (будет приведён к нижнему регистру).

    Returns:
        True если текст — маркер условия.
    """
    return text.lower().strip() in CONDITION_MARKERS


def extract_condition_marker(text: str) -> str | None:
    """
    Извлекает маркер условия из начала текста.

    Args:
        text: Текст, возможно начинающийся с маркера условия.

    Returns:
        Найденный маркер или None.

    Example:
        >>> extract_condition_marker("Если документ согласован")
        'если'
        >>> extract_condition_marker("В случае если заявка одобрена")
        'в случае если'
    """
    text_lower = text.lower().strip()

    for marker in CONDITION_MARKERS_SORTED:
        if text_lower.startswith(marker):
            # Проверяем, что после маркера идёт пробел или конец строки
            # (чтобы "если" не матчилось в "еслибы")
            rest = text_lower[len(marker):]
            if not rest or rest[0].isspace() or rest[0] in ",:;":
                return marker

    return None


def strip_condition_marker(text: str) -> str:
    """
    Удаляет маркер условия из начала текста.

    Args:
        text: Текст, возможно начинающийся с маркера условия.

    Returns:
        Текст без маркера (с сохранением регистра остальной части).

    Example:
        >>> strip_condition_marker("Если документ согласован")
        'документ согласован'
    """
    marker = extract_condition_marker(text)
    if marker:
        # Удаляем маркер, сохраняя регистр остального текста
        return text[len(marker):].lstrip(" ,:")
    return text
