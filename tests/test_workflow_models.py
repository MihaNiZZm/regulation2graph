"""
Unit-тесты для моделей Workflow Net.

Запуск:
    pytest tests/test_workflow_models.py -v
"""

import pytest

from regulation2graph.models import (
    Arc,
    Place,
    PlaceType,
    Transition,
    TransitionType,
    WorkflowNet,
)


class TestPlace:
    """Тесты для модели Place."""

    def test_place_creation(self) -> None:
        """Создание Place с параметрами по умолчанию."""
        place = Place("p1", "Документ проверен")
        assert place.id == "p1"
        assert place.name == "Документ проверен"
        assert place.place_type == PlaceType.INTERMEDIATE

    def test_place_start(self) -> None:
        """Создание начального Place."""
        place = Place("p_start", "Начало", PlaceType.START)
        assert place.is_start is True
        assert place.is_end is False

    def test_place_end(self) -> None:
        """Создание конечного Place."""
        place = Place("p_end", "Конец", PlaceType.END)
        assert place.is_start is False
        assert place.is_end is True

    def test_place_to_dict(self) -> None:
        """Конвертация Place в словарь."""
        place = Place("p1", "Состояние", PlaceType.INTERMEDIATE)
        d = place.to_dict()
        assert d["id"] == "p1"
        assert d["name"] == "Состояние"
        assert d["type"] == "intermediate"

    def test_place_empty_id_raises(self) -> None:
        """Пустой id вызывает ошибку."""
        with pytest.raises(ValueError, match="id cannot be empty"):
            Place("", "Name")

    def test_place_immutable(self) -> None:
        """Place иммутабелен."""
        place = Place("p1", "Test")
        with pytest.raises(AttributeError):
            place.name = "New name"  # type: ignore


class TestTransition:
    """Тесты для модели Transition."""

    def test_transition_creation(self) -> None:
        """Создание Transition."""
        t = Transition("t1", "менеджер", "проверить", "документ")
        assert t.id == "t1"
        assert t.actor == "менеджер"
        assert t.action == "проверить"
        assert t.obj == "документ"
        assert t.guard is None
        assert t.has_guard is False

    def test_transition_with_guard(self) -> None:
        """Transition с условием (guard)."""
        t = Transition(
            "t1", "менеджер", "подписать", "договор",
            guard="документ согласован"
        )
        assert t.has_guard is True
        assert t.guard == "документ согласован"

    def test_transition_display_name(self) -> None:
        """Форматированное имя для отображения."""
        t = Transition("t1", "менеджер", "проверить", "документ")
        assert "МЕНЕДЖЕР" in t.display_name
        assert "проверить" in t.display_name
        assert "документ" in t.display_name

    def test_transition_to_dict(self) -> None:
        """Конвертация Transition в словарь."""
        t = Transition("t1", "актор", "действие", "объект", guard="условие")
        d = t.to_dict()
        assert d["id"] == "t1"
        assert d["actor"] == "актор"
        assert d["action"] == "действие"
        assert d["object"] == "объект"
        assert d["guard"] == "условие"

    def test_transition_empty_action_raises(self) -> None:
        """Пустое действие вызывает ошибку."""
        with pytest.raises(ValueError, match="action cannot be empty"):
            Transition("t1", "актор", "", "объект")

    def test_transition_silent(self) -> None:
        """Silent transition (tau-переход)."""
        t = Transition(
            "t1", "", "tau", "",
            transition_type=TransitionType.SILENT
        )
        assert t.is_silent is True


class TestArc:
    """Тесты для модели Arc."""

    def test_arc_creation(self) -> None:
        """Создание Arc."""
        arc = Arc("p1", "t1")
        assert arc.source_id == "p1"
        assert arc.target_id == "t1"
        assert arc.label == ""

    def test_arc_with_label(self) -> None:
        """Arc с меткой."""
        arc = Arc("p1", "t1", label="Да")
        assert arc.label == "Да"

    def test_arc_to_dict(self) -> None:
        """Конвертация Arc в словарь."""
        arc = Arc("p1", "t1", "Нет")
        d = arc.to_dict()
        assert d["source_id"] == "p1"
        assert d["target_id"] == "t1"
        assert d["label"] == "Нет"

    def test_arc_self_loop_raises(self) -> None:
        """Петля (self-loop) вызывает ошибку."""
        with pytest.raises(ValueError, match="cannot connect node to itself"):
            Arc("p1", "p1")


class TestWorkflowNet:
    """Тесты для модели WorkflowNet."""

    def test_empty_workflow(self) -> None:
        """Пустой WorkflowNet."""
        wf = WorkflowNet()
        assert len(wf.places) == 0
        assert len(wf.transitions) == 0
        assert len(wf.arcs) == 0

    def test_simple_workflow(self) -> None:
        """Простой WorkflowNet с одним переходом."""
        wf = WorkflowNet(
            places=[
                Place("p_start", "Начало", PlaceType.START),
                Place("p1", "После"),
                Place("p_end", "Конец", PlaceType.END),
            ],
            transitions=[
                Transition("t1", "актор", "действие", "объект"),
            ],
            arcs=[
                Arc("p_start", "t1"),
                Arc("t1", "p1"),
                Arc("p1", "p_end"),
            ],
        )
        assert len(wf.places) == 3
        assert len(wf.transitions) == 1
        assert len(wf.arcs) == 3

    def test_start_place(self) -> None:
        """Получение начального места."""
        wf = WorkflowNet(
            places=[
                Place("p_start", "Начало", PlaceType.START),
                Place("p_end", "Конец", PlaceType.END),
            ]
        )
        assert wf.start_place is not None
        assert wf.start_place.id == "p_start"

    def test_end_place(self) -> None:
        """Получение конечного места."""
        wf = WorkflowNet(
            places=[
                Place("p_start", "Начало", PlaceType.START),
                Place("p_end", "Конец", PlaceType.END),
            ]
        )
        assert wf.end_place is not None
        assert wf.end_place.id == "p_end"

    def test_get_place(self) -> None:
        """Поиск места по ID."""
        wf = WorkflowNet(
            places=[Place("p1", "Test")],
        )
        assert wf.get_place("p1") is not None
        assert wf.get_place("nonexistent") is None

    def test_get_transition(self) -> None:
        """Поиск перехода по ID."""
        wf = WorkflowNet(
            transitions=[Transition("t1", "a", "b", "c")],
        )
        assert wf.get_transition("t1") is not None
        assert wf.get_transition("nonexistent") is None

    def test_multiple_start_places_raises(self) -> None:
        """Несколько начальных мест вызывает ошибку."""
        with pytest.raises(ValueError, match="exactly one start place"):
            WorkflowNet(
                places=[
                    Place("p1", "Start1", PlaceType.START),
                    Place("p2", "Start2", PlaceType.START),
                ]
            )

    def test_multiple_end_places_raises(self) -> None:
        """Несколько конечных мест вызывает ошибку."""
        with pytest.raises(ValueError, match="exactly one end place"):
            WorkflowNet(
                places=[
                    Place("p1", "End1", PlaceType.END),
                    Place("p2", "End2", PlaceType.END),
                ]
            )

    def test_to_dict(self) -> None:
        """Конвертация WorkflowNet в словарь."""
        wf = WorkflowNet(
            places=[Place("p1", "Test")],
            transitions=[Transition("t1", "a", "b", "c")],
            arcs=[Arc("p1", "t1")],
        )
        d = wf.to_dict()
        assert len(d["places"]) == 1
        assert len(d["transitions"]) == 1
        assert len(d["arcs"]) == 1

    def test_repr(self) -> None:
        """Строковое представление WorkflowNet."""
        wf = WorkflowNet(
            places=[Place("p1", "Test")],
            transitions=[Transition("t1", "a", "b", "c")],
            arcs=[Arc("p1", "t1")],
        )
        assert "places=1" in repr(wf)
        assert "transitions=1" in repr(wf)
        assert "arcs=1" in repr(wf)
