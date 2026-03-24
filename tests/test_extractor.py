"""
Unit-тесты для RuleBasedExtractor.

Запуск:
    pytest tests/test_extractor.py -v
"""

import pytest

from regulation2graph.core import RuleBasedExtractor
from regulation2graph.models import Triplet


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
