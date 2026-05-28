"""
Unit-тесты для RuleBasedExtractor.

Запуск:
    pytest tests/test_extractor.py -v
"""

import pytest

from regulation2graph.core import RuleBasedExtractor
from regulation2graph.models import Triplet, WorkflowNet, PlaceType


class TestSimpleSentences:
    """Тесты на простые предложения (активный залог)."""

    def test_simple_sentence(self, extractor: RuleBasedExtractor) -> None:
        """Базовый тест: субъект + действие + объект."""
        triplets = extractor.parse_text("Менеджер создает заявку.")

        assert len(triplets) == 1
        t = triplets[0]
        assert t.actor == "менеджер"
        assert "созда" in t.action.lower()
        assert t.obj == "заявка"
        assert t.has_condition is False

    def test_multiple_sentences(self, extractor: RuleBasedExtractor) -> None:
        """Несколько предложений подряд."""
        text = "Менеджер создает заявку. Директор подписывает приказ."
        triplets = extractor.parse_text(text)

        assert len(triplets) == 2
        assert triplets[0].actor == "менеджер"
        assert triplets[1].actor == "директор"


class TestConditions:
    """Тесты на предложения с условиями."""

    def test_condition_if(self, extractor: RuleBasedExtractor) -> None:
        """Условие с 'если'."""
        triplets = extractor.parse_text(
            "Если документ согласован, секретарь печатает договор."
        )

        assert len(triplets) == 1
        t = triplets[0]
        assert t.actor == "секретарь"
        assert t.has_condition is True
        assert t.condition_text is not None

    def test_condition_when(self, extractor: RuleBasedExtractor) -> None:
        """Условие с 'когда'."""
        triplets = extractor.parse_text("Когда товар готов, курьер забирает посылку.")

        assert len(triplets) == 1
        t = triplets[0]
        assert t.has_condition is True

    def test_alternative_branch(self, extractor: RuleBasedExtractor) -> None:
        """Альтернативная ветка с 'иначе'."""
        triplets = extractor.parse_text("Иначе менеджер возвращает заявку клиенту.")

        assert len(triplets) == 1
        t = triplets[0]
        assert t.is_alternative is True


class TestTripletModel:
    """Тесты модели Triplet."""

    def test_triplet_creation(self) -> None:
        """Создание триплета."""
        t = Triplet(
            actor="менеджер",
            action="проверять",
            obj="заявка",
        )
        assert t.actor == "менеджер"
        assert t.has_condition is False

    def test_triplet_with_condition(self) -> None:
        """Триплет с условием."""
        t = Triplet(
            actor="менеджер",
            action="проверять",
            obj="заявка",
            condition_text="документ согласован",
        )
        assert t.has_condition is True

    def test_triplet_to_dict(self) -> None:
        """Конвертация в словарь."""
        t = Triplet(actor="менеджер", action="проверять", obj="заявка")
        d = t.to_dict()

        assert d["actor"] == "менеджер"
        assert d["action"] == "проверять"
        assert d["object"] == "заявка"

    def test_triplet_from_dict(self) -> None:
        """Создание из словаря."""
        d = {"actor": "менеджер", "action": "проверять", "object": "заявка"}
        t = Triplet.from_dict(d)

        assert t.actor == "менеджер"
        assert t.action == "проверять"
        assert t.obj == "заявка"

    def test_triplet_immutable(self) -> None:
        """Триплет неизменяемый (frozen)."""
        t = Triplet(actor="менеджер", action="проверять", obj="заявка")

        with pytest.raises(AttributeError):
            t.actor = "директор"  # type: ignore

    def test_triplet_requires_action(self) -> None:
        """Действие обязательно."""
        with pytest.raises(ValueError, match="Action cannot be empty"):
            Triplet(actor="менеджер", action="", obj="заявка")


class TestWorkflowNetExtraction:
    """Тесты нового метода extract() для WorkflowNet."""

    def test_extract_returns_workflow_net(self, extractor: RuleBasedExtractor) -> None:
        """extract() возвращает WorkflowNet."""
        workflow = extractor.extract("Менеджер проверяет заявку.")
        assert isinstance(workflow, WorkflowNet)

    def test_extract_simple_has_start_and_end(self, extractor: RuleBasedExtractor) -> None:
        """WorkflowNet имеет начальное и конечное места."""
        workflow = extractor.extract("Менеджер проверяет заявку.")
        assert workflow.start_place is not None
        assert workflow.start_place.place_type == PlaceType.START
        assert workflow.end_place is not None
        assert workflow.end_place.place_type == PlaceType.END

    def test_extract_simple_creates_transitions(self, extractor: RuleBasedExtractor) -> None:
        """Извлекаются Transitions из предложений."""
        workflow = extractor.extract("Менеджер проверяет заявку. Директор подписывает документ.")
        assert len(workflow.transitions) == 2
        assert workflow.transitions[0].actor == "менеджер"
        assert workflow.transitions[1].actor == "директор"

    def test_extract_creates_intermediate_places(self, extractor: RuleBasedExtractor) -> None:
        """Создаются промежуточные Places между Transitions."""
        workflow = extractor.extract("Менеджер проверяет. Директор подписывает.")
        # start + 2 intermediate + end = 4 places
        assert len(workflow.places) >= 4

    def test_extract_creates_arcs(self, extractor: RuleBasedExtractor) -> None:
        """Создаются Arcs между Places и Transitions."""
        workflow = extractor.extract("Менеджер проверяет заявку.")
        # p_start -> t0 -> p1 -> p_end = минимум 3 arcs
        assert len(workflow.arcs) >= 3

    def test_extract_condition_creates_guard(self, extractor: RuleBasedExtractor) -> None:
        """Условие в тексте создаёт guard на Transition."""
        workflow = extractor.extract("Если документ согласован, менеджер подписывает договор.")
        assert len(workflow.transitions) == 1
        assert workflow.transitions[0].has_guard is True
        assert workflow.transitions[0].guard is not None

    def test_extract_condition_creates_labeled_arcs(self, extractor: RuleBasedExtractor) -> None:
        """Условие создаёт дуги с метками 'Да'/'Нет'."""
        workflow = extractor.extract("Если документ согласован, менеджер подписывает договор.")
        labels = [arc.label for arc in workflow.arcs if arc.label]
        assert "Да" in labels
        # "Нет" тоже должен быть (к p_end, если нет альтернативы)
        assert "Нет" in labels

    def test_extract_with_alternative_branch(self, extractor: RuleBasedExtractor) -> None:
        """Альтернативная ветка корректно обрабатывается."""
        workflow = extractor.extract(
            "Если документ согласован, менеджер подписывает. "
            "Иначе секретарь возвращает."
        )
        assert len(workflow.transitions) == 2
        labels = [arc.label for arc in workflow.arcs if arc.label]
        assert "Да" in labels
        assert "Нет" in labels

    def test_extract_empty_text(self, extractor: RuleBasedExtractor) -> None:
        """Пустой текст возвращает минимальный WorkflowNet."""
        workflow = extractor.extract("")
        assert workflow.start_place is not None
        assert workflow.end_place is not None
        assert len(workflow.transitions) == 0


class TestCompoundSentences:
    """Тесты на многоосновные (сложносочинённые) предложения."""

    def test_two_independent_clauses(self, extractor: RuleBasedExtractor) -> None:
        """Два независимых действия с разными субъектами."""
        workflow = extractor.extract(
            "Менеджер проверяет заявку и директор подписывает договор."
        )

        assert len(workflow.transitions) == 2
        t1, t2 = workflow.transitions

        assert t1.actor == "менеджер"
        assert t1.action == "проверять"
        assert t1.obj == "заявка"

        assert t2.actor == "директор"
        assert t2.action == "подписывать"
        assert t2.obj == "договор"

    def test_shared_subject_two_verbs(self, extractor: RuleBasedExtractor) -> None:
        """Один субъект, два глагола с общим объектом."""
        workflow = extractor.extract("Менеджер проверяет и подписывает заявку.")

        assert len(workflow.transitions) == 2
        t1, t2 = workflow.transitions

        # Оба действия имеют одного актора
        assert t1.actor == "менеджер"
        assert t2.actor == "менеджер"

        # Оба действия имеют один объект (унаследованный)
        assert t1.obj == "заявка"
        assert t2.obj == "заявка"

        # Разные действия
        assert t1.action == "проверять"
        assert t2.action == "подписывать"

    def test_compound_subject(self, extractor: RuleBasedExtractor) -> None:
        """Составной субъект (А и Б)."""
        workflow = extractor.extract("Менеджер и директор проверяют заявку.")

        assert len(workflow.transitions) == 1
        t = workflow.transitions[0]

        # Составной актор
        assert "менеджер" in t.actor
        assert "директор" in t.actor
        assert " и " in t.actor

        assert t.action == "проверять"
        assert t.obj == "заявка"

    def test_three_independent_clauses(self, extractor: RuleBasedExtractor) -> None:
        """Три независимых действия с разными субъектами."""
        workflow = extractor.extract(
            "Секретарь регистрирует документ, "
            "бухгалтер проверяет расчёты, "
            "директор утверждает бюджет."
        )

        assert len(workflow.transitions) == 3

        actors = [t.actor for t in workflow.transitions]
        assert "секретарь" in actors
        assert "бухгалтер" in actors
        assert "директор" in actors

        actions = [t.action for t in workflow.transitions]
        assert "регистрировать" in actions
        assert "проверять" in actions
        assert "утверждать" in actions

    def test_compound_with_condition(self, extractor: RuleBasedExtractor) -> None:
        """Сложное предложение с условием в первой части."""
        workflow = extractor.extract(
            "Если заявка одобрена, менеджер подписывает и секретарь регистрирует."
        )

        assert len(workflow.transitions) == 2
        t1, t2 = workflow.transitions

        # Условие только у первого действия
        assert t1.has_guard is True
        assert t2.has_guard is False

    def test_workflow_net_structure_with_compound(
        self, extractor: RuleBasedExtractor
    ) -> None:
        """WorkflowNet корректно строится для многоосновного предложения."""
        workflow = extractor.extract(
            "Менеджер проверяет заявку и директор подписывает договор."
        )

        # start + 2 intermediate + end = 4 places
        assert len(workflow.places) == 4

        # Проверяем, что все transitions связаны arcs
        transition_ids = {t.id for t in workflow.transitions}
        arc_sources = {arc.source_id for arc in workflow.arcs}
        arc_targets = {arc.target_id for arc in workflow.arcs}

        # Каждый transition должен быть и source, и target
        for t_id in transition_ids:
            assert t_id in arc_sources or t_id in arc_targets
