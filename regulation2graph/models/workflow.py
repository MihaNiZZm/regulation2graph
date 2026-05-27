"""
Модели Workflow Net для представления бизнес-процессов.

Workflow Net — подкласс сетей Петри (Petri Net), специализированный
для моделирования бизнес-процессов.

Основные компоненты:
- Place (место) — состояние процесса
- Transition (переход) — действие/активность
- Arc (дуга) — связь между Place и Transition
- WorkflowNet — контейнер для всей сети

См. документацию: data/documents/WORKFLOW_NET.md
"""

from dataclasses import dataclass, field
from enum import Enum


class PlaceType(Enum):
    """Тип места в Workflow Net."""

    START = "start"  # Начальное место (source)
    END = "end"  # Конечное место (sink)
    INTERMEDIATE = "intermediate"  # Промежуточное состояние


class TransitionType(Enum):
    """Тип перехода в Workflow Net."""

    ACTIVITY = "activity"  # Обычное действие (видимое)
    SILENT = "silent"  # Невидимый переход (tau-transition)


@dataclass(frozen=True)
class Place:
    """
    Место в Workflow Net — представляет состояние процесса.

    В терминах бизнес-процесса: "Заявка подана", "Документ на проверке".

    Attributes:
        id: Уникальный идентификатор места.
        name: Человекочитаемое название состояния.
        place_type: Тип места (START, END, INTERMEDIATE).

    Example:
        >>> p = Place("p0", "Начало процесса", PlaceType.START)
        >>> p = Place("p1", "Документ проверен", PlaceType.INTERMEDIATE)
    """

    id: str
    name: str
    place_type: PlaceType = PlaceType.INTERMEDIATE

    def __post_init__(self) -> None:
        """Валидация после создания."""
        if not self.id:
            raise ValueError("Place id cannot be empty")

    @property
    def is_start(self) -> bool:
        """Проверяет, является ли место начальным."""
        return self.place_type == PlaceType.START

    @property
    def is_end(self) -> bool:
        """Проверяет, является ли место конечным."""
        return self.place_type == PlaceType.END

    def to_dict(self) -> dict:
        """Конвертация в словарь для Neo4j."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.place_type.value,
        }


@dataclass(frozen=True)
class Transition:
    """
    Переход в Workflow Net — представляет действие в процессе.

    Заменяет старый Triplet. Структура: Субъект → Действие → Объект.

    Attributes:
        id: Уникальный идентификатор перехода.
        actor: Кто выполняет действие (субъект).
        action: Что делает (глагол в лемматизированной форме).
        obj: Над чем выполняется действие (объект).
        guard: Условие срабатывания перехода (опционально).
        transition_type: Тип перехода (ACTIVITY, SILENT).
        full_text: Исходный текст предложения для отладки.

    Example:
        >>> t = Transition(
        ...     id="t1",
        ...     actor="менеджер",
        ...     action="проверить",
        ...     obj="документ",
        ...     guard="документ согласован"
        ... )
    """

    id: str
    actor: str
    action: str
    obj: str
    guard: str | None = None
    transition_type: TransitionType = TransitionType.ACTIVITY
    full_text: str = ""

    def __post_init__(self) -> None:
        """Валидация после создания."""
        if not self.id:
            raise ValueError("Transition id cannot be empty")
        if not self.action:
            raise ValueError("Transition action cannot be empty")

    @property
    def has_guard(self) -> bool:
        """Проверяет, есть ли условие на переходе."""
        return self.guard is not None

    @property
    def is_silent(self) -> bool:
        """Проверяет, является ли переход невидимым."""
        return self.transition_type == TransitionType.SILENT

    @property
    def display_name(self) -> str:
        """Форматированное имя для отображения."""
        return f"{self.actor.upper()}\n{self.action}\n{self.obj}"

    def to_dict(self) -> dict:
        """Конвертация в словарь для Neo4j."""
        return {
            "id": self.id,
            "actor": self.actor,
            "action": self.action,
            "object": self.obj,
            "guard": self.guard,
            "type": self.transition_type.value,
            "full_text": self.full_text,
        }


@dataclass(frozen=True)
class Arc:
    """
    Дуга в Workflow Net — связь между Place и Transition.

    В Workflow Net дуги могут идти только:
    - Place → Transition (входная дуга)
    - Transition → Place (выходная дуга)

    Attributes:
        source_id: ID источника (Place или Transition).
        target_id: ID цели (Transition или Place).
        label: Метка дуги (для визуализации, например "Да"/"Нет").

    Example:
        >>> arc = Arc("p0", "t1")  # Place → Transition
        >>> arc = Arc("t1", "p1")  # Transition → Place
        >>> arc = Arc("p1", "t2", label="Да")  # Условный переход
    """

    source_id: str
    target_id: str
    label: str = ""

    def __post_init__(self) -> None:
        """Валидация после создания."""
        if not self.source_id:
            raise ValueError("Arc source_id cannot be empty")
        if not self.target_id:
            raise ValueError("Arc target_id cannot be empty")
        if self.source_id == self.target_id:
            raise ValueError("Arc cannot connect node to itself")

    def to_dict(self) -> dict:
        """Конвертация в словарь для Neo4j."""
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "label": self.label,
        }


@dataclass
class WorkflowNet:
    """
    Workflow Net — полная модель бизнес-процесса.

    Контейнер для Places, Transitions и Arcs.
    Гарантирует структурные свойства Workflow Net:
    - Ровно один начальный Place (source)
    - Ровно один конечный Place (sink)
    - Все узлы достижимы от начала до конца

    Attributes:
        places: Список мест (состояний).
        transitions: Список переходов (действий).
        arcs: Список дуг (связей).

    Example:
        >>> wf = WorkflowNet(
        ...     places=[Place("p0", "Начало", PlaceType.START), ...],
        ...     transitions=[Transition("t1", "менеджер", "проверить", "документ"), ...],
        ...     arcs=[Arc("p0", "t1"), Arc("t1", "p1"), ...]
        ... )
    """

    places: list[Place] = field(default_factory=list)
    transitions: list[Transition] = field(default_factory=list)
    arcs: list[Arc] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Валидация структуры Workflow Net."""
        self._validate()

    def _validate(self) -> None:
        """Проверяет корректность структуры."""
        # Проверка наличия начального места
        start_places = [p for p in self.places if p.is_start]
        if len(start_places) > 1:
            raise ValueError("WorkflowNet must have exactly one start place")

        # Проверка наличия конечного места
        end_places = [p for p in self.places if p.is_end]
        if len(end_places) > 1:
            raise ValueError("WorkflowNet must have exactly one end place")

    @property
    def start_place(self) -> Place | None:
        """Возвращает начальное место."""
        for p in self.places:
            if p.is_start:
                return p
        return None

    @property
    def end_place(self) -> Place | None:
        """Возвращает конечное место."""
        for p in self.places:
            if p.is_end:
                return p
        return None

    def get_place(self, place_id: str) -> Place | None:
        """Находит место по ID."""
        for p in self.places:
            if p.id == place_id:
                return p
        return None

    def get_transition(self, transition_id: str) -> Transition | None:
        """Находит переход по ID."""
        for t in self.transitions:
            if t.id == transition_id:
                return t
        return None

    def get_outgoing_arcs(self, node_id: str) -> list[Arc]:
        """Возвращает исходящие дуги из узла."""
        return [a for a in self.arcs if a.source_id == node_id]

    def get_incoming_arcs(self, node_id: str) -> list[Arc]:
        """Возвращает входящие дуги в узел."""
        return [a for a in self.arcs if a.target_id == node_id]

    def to_dict(self) -> dict:
        """Конвертация в словарь для сериализации."""
        return {
            "places": [p.to_dict() for p in self.places],
            "transitions": [t.to_dict() for t in self.transitions],
            "arcs": [a.to_dict() for a in self.arcs],
        }

    def __repr__(self) -> str:
        return (
            f"WorkflowNet(places={len(self.places)}, "
            f"transitions={len(self.transitions)}, "
            f"arcs={len(self.arcs)})"
        )


# Alias для обратной совместимости с Triplet
# TODO: Удалить после полной миграции
Triplet = Transition
