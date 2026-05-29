"""
Маркеры циклов (loop markers).

Слова и фразы, указывающие на повторение действий:
- "пока не", "до тех пор", "повторять" и т.д.

TODO: Этот модуль требует дополнительного исследования.
      Основная сложность — резолв узла, к которому возвращаться.

Используются для детекции циклов в Workflow Net.
"""

from __future__ import annotations

# Маркеры циклов — frozenset для быстрой проверки вхождения
# Все маркеры в нижнем регистре
LOOP_MARKERS: frozenset[str] = frozenset({
    # Составные с "пока"
    "пока",
    "пока не",
    "пока не будет",

    # Составные с "до"
    "до тех пор",
    "до тех пор пока",
    "до тех пор пока не",
    "до момента",
    "до момента когда",

    # С глаголами повторения
    "повторять до",
    "повторять пока",
    "повторно",

    # Неявные маркеры возврата
    "возвращается на",
    "возвращается к",
    "направляется обратно",
    "отправляется на доработку",
    "на доработку",
})

# Маркеры, отсортированные по длине (от длинных к коротким)
LOOP_MARKERS_SORTED: tuple[str, ...] = tuple(
    sorted(LOOP_MARKERS, key=len, reverse=True)
)


def is_loop_marker(text: str) -> bool:
    """
    Проверяет, является ли текст маркером цикла.

    Args:
        text: Текст для проверки (будет приведён к нижнему регистру).

    Returns:
        True если текст — маркер цикла.

    Note:
        Функция готова, но интеграция в extractor требует
        дополнительной логики резолва целевого узла.
    """
    return text.lower().strip() in LOOP_MARKERS


def extract_loop_marker(text: str) -> str | None:
    """
    Извлекает маркер цикла из текста.

    Args:
        text: Текст, возможно содержащий маркер цикла.

    Returns:
        Найденный маркер или None.

    Example:
        >>> extract_loop_marker("Пока документ не согласован")
        'пока'
        >>> extract_loop_marker("До тех пор пока не получено одобрение")
        'до тех пор пока не'
    """
    text_lower = text.lower().strip()

    for marker in LOOP_MARKERS_SORTED:
        if text_lower.startswith(marker):
            rest = text_lower[len(marker):]
            if not rest or rest[0].isspace() or rest[0] in ",:;":
                return marker

    return None


def contains_loop_marker(text: str) -> bool:
    """
    Проверяет, содержит ли текст маркер цикла (не только в начале).

    Полезно для обнаружения неявных циклов типа
    "заявка возвращается на доработку".

    Args:
        text: Текст для проверки.

    Returns:
        True если текст содержит маркер цикла.
    """
    text_lower = text.lower()
    return any(marker in text_lower for marker in LOOP_MARKERS)
