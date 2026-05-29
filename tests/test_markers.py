"""
Тесты для модуля маркеров (markers/).

Проверяет детекцию условий, альтернатив и циклов.
"""

import pytest

from regulation2graph.markers import (
    ALTERNATIVE_MARKERS,
    ALTERNATIVE_MARKERS_SORTED,
    CONDITION_MARKERS,
    CONDITION_MARKERS_SORTED,
    LOOP_MARKERS,
    LOOP_MARKERS_SORTED,
    AlternativeMatch,
    ConditionMatch,
    LoopMatch,
    MarkerDetector,
    contains_loop_marker,
    extract_alternative_marker,
    extract_condition_marker,
    extract_loop_marker,
    is_alternative_marker,
    is_condition_marker,
    is_loop_marker,
    strip_alternative_marker,
    strip_condition_marker,
)


class TestConditionMarkers:
    """Тесты для маркеров условий."""

    def test_condition_markers_is_frozenset(self):
        """Маркеры условий — frozenset."""
        assert isinstance(CONDITION_MARKERS, frozenset)

    def test_condition_markers_sorted_by_length(self):
        """Маркеры отсортированы по длине (от длинных к коротким)."""
        lengths = [len(m) for m in CONDITION_MARKERS_SORTED]
        assert lengths == sorted(lengths, reverse=True)

    def test_is_condition_marker_basic(self):
        """Проверка базовых маркеров условия."""
        assert is_condition_marker("если")
        assert is_condition_marker("когда")
        assert is_condition_marker("ЕСЛИ")  # регистр
        assert is_condition_marker(" если ")  # пробелы

    def test_is_condition_marker_composite(self):
        """Проверка составных маркеров условия."""
        assert is_condition_marker("в случае")
        assert is_condition_marker("в случае если")
        assert is_condition_marker("при условии что")

    def test_is_condition_marker_negative(self):
        """Не-маркеры не должны детектиться."""
        assert not is_condition_marker("менеджер")
        assert not is_condition_marker("иначе")
        assert not is_condition_marker("")

    def test_extract_condition_marker_basic(self):
        """Извлечение базового маркера из текста."""
        assert extract_condition_marker("Если документ согласован") == "если"
        assert extract_condition_marker("Когда заявка одобрена") == "когда"

    def test_extract_condition_marker_composite(self):
        """Извлечение составного маркера (длинный должен иметь приоритет)."""
        # "в случае если" должен извлечься вместо "в случае"
        marker = extract_condition_marker("В случае если заявка одобрена")
        assert marker == "в случае если"

        marker = extract_condition_marker("В случае отклонения")
        assert marker == "в случае"

    def test_extract_condition_marker_boundary(self):
        """Маркер должен быть отделён от остального текста."""
        # "если" как часть слова не должно извлекаться
        assert extract_condition_marker("еслибы") is None
        assert extract_condition_marker("Если,") == "если"  # запятая — ОК

    def test_extract_condition_marker_none(self):
        """Если маркера нет, возвращается None."""
        assert extract_condition_marker("Менеджер проверяет") is None
        assert extract_condition_marker("") is None

    def test_strip_condition_marker(self):
        """Удаление маркера из начала текста."""
        assert strip_condition_marker("Если документ согласован") == "документ согласован"
        assert strip_condition_marker("В случае если заявка одобрена") == "заявка одобрена"
        assert strip_condition_marker("Менеджер проверяет") == "Менеджер проверяет"


class TestAlternativeMarkers:
    """Тесты для маркеров альтернатив."""

    def test_alternative_markers_is_frozenset(self):
        """Маркеры альтернатив — frozenset."""
        assert isinstance(ALTERNATIVE_MARKERS, frozenset)

    def test_alternative_markers_sorted_by_length(self):
        """Маркеры отсортированы по длине."""
        lengths = [len(m) for m in ALTERNATIVE_MARKERS_SORTED]
        assert lengths == sorted(lengths, reverse=True)

    def test_is_alternative_marker_basic(self):
        """Проверка базовых маркеров альтернативы."""
        assert is_alternative_marker("иначе")
        assert is_alternative_marker("ИНАЧЕ")

    def test_is_alternative_marker_composite(self):
        """Проверка составных маркеров альтернативы."""
        assert is_alternative_marker("в противном случае")
        assert is_alternative_marker("если нет")
        assert is_alternative_marker("при отклонении")

    def test_is_alternative_marker_negative(self):
        """Не-маркеры не должны детектиться."""
        assert not is_alternative_marker("если")
        assert not is_alternative_marker("менеджер")

    def test_extract_alternative_marker(self):
        """Извлечение маркера альтернативы."""
        assert extract_alternative_marker("Иначе секретарь возвращает") == "иначе"
        assert extract_alternative_marker("В противном случае заявка отклоняется") == "в противном случае"

    def test_extract_alternative_marker_boundary(self):
        """Маркер должен быть отделён от остального текста."""
        assert extract_alternative_marker("иначе,") == "иначе"
        assert extract_alternative_marker("иначеже") is None

    def test_strip_alternative_marker(self):
        """Удаление маркера альтернативы из текста."""
        assert strip_alternative_marker("Иначе секретарь возвращает") == "секретарь возвращает"
        assert strip_alternative_marker("В противном случае: отклонить") == "отклонить"


class TestLoopMarkers:
    """Тесты для маркеров циклов."""

    def test_loop_markers_is_frozenset(self):
        """Маркеры циклов — frozenset."""
        assert isinstance(LOOP_MARKERS, frozenset)

    def test_loop_markers_sorted_by_length(self):
        """Маркеры отсортированы по длине."""
        lengths = [len(m) for m in LOOP_MARKERS_SORTED]
        assert lengths == sorted(lengths, reverse=True)

    def test_is_loop_marker_basic(self):
        """Проверка базовых маркеров цикла."""
        assert is_loop_marker("пока")
        assert is_loop_marker("пока не")
        assert is_loop_marker("на доработку")

    def test_is_loop_marker_composite(self):
        """Проверка составных маркеров цикла."""
        assert is_loop_marker("до тех пор пока не")
        assert is_loop_marker("возвращается на")

    def test_extract_loop_marker(self):
        """Извлечение маркера цикла."""
        assert extract_loop_marker("Пока документ не согласован") == "пока"
        assert extract_loop_marker("До тех пор пока не получено одобрение") == "до тех пор пока не"

    def test_contains_loop_marker(self):
        """Проверка содержания маркера цикла в любом месте текста."""
        assert contains_loop_marker("Заявка возвращается на доработку")
        assert contains_loop_marker("Процесс повторяется пока не получено одобрение")
        assert not contains_loop_marker("Менеджер проверяет заявку")


class TestMarkerDetector:
    """Тесты для класса MarkerDetector."""

    @pytest.fixture
    def detector(self):
        """Создаёт экземпляр детектора."""
        return MarkerDetector()

    def test_detect_condition_returns_match(self, detector):
        """detect_condition возвращает ConditionMatch."""
        match = detector.detect_condition("Если документ согласован, менеджер подписывает")
        assert match is not None
        assert isinstance(match, ConditionMatch)
        assert match.marker == "если"
        assert match.remaining_text == "документ согласован, менеджер подписывает"

    def test_detect_condition_returns_none(self, detector):
        """detect_condition возвращает None если маркера нет."""
        match = detector.detect_condition("Менеджер проверяет заявку")
        assert match is None

    def test_detect_alternative_returns_match(self, detector):
        """detect_alternative возвращает AlternativeMatch."""
        match = detector.detect_alternative("Иначе секретарь возвращает документ")
        assert match is not None
        assert isinstance(match, AlternativeMatch)
        assert match.marker == "иначе"
        assert match.remaining_text == "секретарь возвращает документ"

    def test_detect_alternative_composite(self, detector):
        """detect_alternative работает с составными маркерами."""
        match = detector.detect_alternative("В противном случае заявка отклоняется")
        assert match is not None
        assert match.marker == "в противном случае"

    def test_detect_loop_returns_match(self, detector):
        """detect_loop возвращает LoopMatch."""
        match = detector.detect_loop("Пока не получено одобрение, процесс повторяется")
        assert match is not None
        assert isinstance(match, LoopMatch)
        assert match.marker == "пока не"

    def test_has_any_marker_condition(self, detector):
        """has_any_marker детектирует условия."""
        assert detector.has_any_marker("Если заявка одобрена")

    def test_has_any_marker_alternative(self, detector):
        """has_any_marker детектирует альтернативы."""
        assert detector.has_any_marker("Иначе отклонить")

    def test_has_any_marker_loop(self, detector):
        """has_any_marker детектирует циклы."""
        assert detector.has_any_marker("Пока не согласовано")

    def test_has_any_marker_none(self, detector):
        """has_any_marker возвращает False без маркеров."""
        assert not detector.has_any_marker("Менеджер проверяет заявку")


class TestMarkerDetectorIntegration:
    """Интеграционные тесты для детектора маркеров."""

    @pytest.fixture
    def detector(self):
        return MarkerDetector()

    def test_real_regulation_with_condition(self, detector):
        """Детекция условия в реальном тексте регламента."""
        text = "Если документ согласован, менеджер подписывает договор."
        match = detector.detect_condition(text)
        assert match is not None
        assert "документ согласован" in match.remaining_text

    def test_real_regulation_with_alternative(self, detector):
        """Детекция альтернативы в реальном тексте регламента."""
        text = "В противном случае секретарь возвращает документ на доработку."
        match = detector.detect_alternative(text)
        assert match is not None
        assert "секретарь возвращает" in match.remaining_text

    def test_condition_then_alternative(self, detector):
        """Последовательное использование условия и альтернативы."""
        condition_text = "Если заявка одобрена, менеджер подписывает."
        alternative_text = "Иначе секретарь возвращает заявку."

        condition_match = detector.detect_condition(condition_text)
        alternative_match = detector.detect_alternative(alternative_text)

        assert condition_match is not None
        assert alternative_match is not None
        assert condition_match.marker == "если"
        assert alternative_match.marker == "иначе"
