"""
Triplet model - основная единица представления действия в бизнес-процессе.

Аналог DTO/Entity в Spring:
- Иммутабельный (frozen=True)
- С валидацией через __post_init__
- С типизацией
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Triplet:
    """
    Представляет одно действие в бизнес-процессе.

    Структура: Субъект → Действие → Объект

    Attributes:
        actor: Кто выполняет действие (субъект). "Unknown" если не определён.
        action: Что делает (глагол в лемматизированной форме).
        obj: Над чем выполняется действие (объект). "-" если отсутствует.
        condition_text: Текст условия, если действие условное. None если безусловное.
        is_alternative: True если это альтернативная ветка (после "иначе").
        full_text: Исходный текст предложения для отладки.

    Example:
        >>> t = Triplet(
        ...     actor="менеджер",
        ...     action="проверять",
        ...     obj="заявка",
        ...     condition_text="документ согласован",
        ...     full_text="Если документ согласован, менеджер проверяет заявку."
        ... )
    """

    actor: str
    action: str
    obj: str  # "object" - зарезервированное слово в Python
    condition_text: str | None = None
    is_alternative: bool = False
    full_text: str = ""

    def __post_init__(self) -> None:
        """Валидация после создания (как @Valid в Spring)."""
        if not self.action:
            raise ValueError("Action cannot be empty")

    @property
    def has_condition(self) -> bool:
        """Проверяет, является ли действие условным."""
        return self.condition_text is not None

    @property
    def display_name(self) -> str:
        """Форматированное имя для отображения в графе."""
        return f"{self.actor.upper()}\n{self.action}\n{self.obj}"

    def to_dict(self) -> dict:
        """Конвертация в словарь (для совместимости с legacy кодом)."""
        return {
            "actor": self.actor,
            "action": self.action,
            "object": self.obj,
            "condition": self.condition_text,  # legacy name
            "is_alternative": self.is_alternative,
            "full_text": self.full_text,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Triplet":
        """Создание из словаря (для совместимости с legacy кодом)."""
        return cls(
            actor=data.get("actor", "Unknown"),
            action=data["action"],
            obj=data.get("object", "-"),
            condition_text=data.get("condition"),
            is_alternative=data.get("is_alternative", False),
            full_text=data.get("full_text", ""),
        )
