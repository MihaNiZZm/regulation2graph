"""
Triplet model - основная единица представления действия в бизнес-процессе.

Аналог DTO/Entity в Spring:
- Иммутабельный (frozen=True)
- С валидацией через __post_init__
- С типизацией
"""

from dataclasses import dataclass, field
from enum import Enum


class GatewayType(Enum):
    """Тип шлюза (gateway) в BPMN-нотации."""

    EXCLUSIVE = "exclusive"       # XOR — либо одно, либо другое
    PARALLEL = "parallel"         # AND — одновременно оба
    INCLUSIVE = "inclusive"       # OR — одно или оба


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
    gateway_type: GatewayType | None = None  # Тип шлюза, если есть условие
    gateway_condition: str | None = None     # Условие для шлюза (дублирует condition_text)

    def __post_init__(self) -> None:
        """Валидация после создания."""
        object.__setattr__(self, "gateway_condition", self.condition_text)
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
        """Конвертация в словарь."""
        return {
            "actor": self.actor,
            "action": self.action,
            "object": self.obj,
            "condition": self.condition_text,
            "is_alternative": self.is_alternative,
            "full_text": self.full_text,
            "gateway_type": self.gateway_type.value if self.gateway_type else None,
            "gateway_condition": self.gateway_condition,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Triplet":
        """Создание из словаря."""
        gateway_type = None
        if data.get("gateway_type"):
            gateway_type = GatewayType(data["gateway_type"])

        return cls(
            actor=data.get("actor", "Unknown"),
            action=data["action"],
            obj=data.get("object", "-"),
            condition_text=data.get("condition"),
            is_alternative=data.get("is_alternative", False),
            full_text=data.get("full_text", ""),
            gateway_type=gateway_type,
            gateway_condition=data.get("gateway_condition"),
        )
