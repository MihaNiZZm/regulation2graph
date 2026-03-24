"""
Unit-тесты для GraphVisualizer с логикой ветвления.

Запуск:
    pytest tests/test_visualizer.py -v
"""

import pytest

from regulation2graph.graph import GraphVisualizer
from regulation2graph.models import Triplet


@pytest.fixture
def visualizer() -> GraphVisualizer:
    """Фикстура для GraphVisualizer."""
    return GraphVisualizer()


class TestLinearGraph:
    """Тесты на линейный граф (без условий)."""

    def test_empty_triplets(self, visualizer: GraphVisualizer) -> None:
        """Пустой список триплетов."""
        graph = visualizer._build_graph([])
        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0

    def test_single_triplet(self, visualizer: GraphVisualizer) -> None:
        """Один триплет - один узел, без рёбер."""
        triplets = [Triplet(actor="менеджер", action="создать", obj="заявка")]
        graph = visualizer._build_graph(triplets)

        assert len(graph.nodes) == 1
        assert len(graph.edges) == 0

    def test_two_triplets_linear(self, visualizer: GraphVisualizer) -> None:
        """Два триплета без условий - линейная связь."""
        triplets = [
            Triplet(actor="менеджер", action="создать", obj="заявка"),
            Triplet(actor="директор", action="подписать", obj="документ"),
        ]
        graph = visualizer._build_graph(triplets)

        assert len(graph.nodes) == 2
        assert len(graph.edges) == 1


class TestBranchingWithAlternative:
    """Тесты на ветвление с альтернативой (иначе)."""

    def test_condition_with_alternative_and_merge(
        self, visualizer: GraphVisualizer
    ) -> None:
        """
        Условие с альтернативой, затем слияние.

        Вход: [условие] -> [альтернатива] -> [общий шаг]
        Граф:
            [условие] --Да--> [общий шаг]
                      --Нет--> [альтернатива] --> [общий шаг]
        """
        triplets = [
            Triplet(
                actor="менеджер",
                action="подписать",
                obj="договор",
                condition_text="документ согласован",
            ),
            Triplet(
                actor="секретарь",
                action="вернуть",
                obj="документ",
                is_alternative=True,
            ),
            Triplet(actor="директор", action="утвердить", obj="решение"),
        ]
        graph = visualizer._build_graph(triplets)

        # 3 узла триплетов, без "Конец процесса" (есть альтернатива)
        assert len(graph.nodes) == 3
        assert "Конец процесса" not in graph.nodes

        # Проверяем рёбра
        edges = list(graph.edges(data=True))
        labels = {(u, v): d.get("label", "") for u, v, d in edges}

        # Должно быть 3 ребра:
        # 1. условие --Да--> общий шаг
        # 2. условие --Нет--> альтернатива
        # 3. альтернатива --> общий шаг
        assert len(edges) == 3

        # Проверяем что есть рёбра "Да" и "Нет"
        edge_labels = [d.get("label") for _, _, d in edges]
        assert "Да" in edge_labels
        assert "Нет" in edge_labels


class TestBranchingWithoutAlternative:
    """Тесты на ветвление без альтернативы (к "Конец процесса")."""

    def test_condition_without_alternative(self, visualizer: GraphVisualizer) -> None:
        """
        Условие без альтернативы.

        Вход: [условие] -> [следующий шаг]
        Граф:
            [условие] --Да--> [следующий шаг]
                      --Нет--> [Конец процесса]
        """
        triplets = [
            Triplet(
                actor="менеджер",
                action="подписать",
                obj="договор",
                condition_text="документ согласован",
            ),
            Triplet(actor="директор", action="утвердить", obj="решение"),
        ]
        graph = visualizer._build_graph(triplets)

        # 2 узла триплетов + "Конец процесса"
        assert len(graph.nodes) == 3
        assert "Конец процесса" in graph.nodes

        # Проверяем рёбра
        edges = list(graph.edges(data=True))
        edge_labels = [d.get("label") for _, _, d in edges]

        assert "Да" in edge_labels
        assert "Нет" in edge_labels

    def test_only_condition_triplet(self, visualizer: GraphVisualizer) -> None:
        """
        Только один триплет с условием.

        Граф:
            [условие] --Да--> [Конец процесса]
                      --Нет--> [Конец процесса]
        """
        triplets = [
            Triplet(
                actor="менеджер",
                action="подписать",
                obj="договор",
                condition_text="документ согласован",
            ),
        ]
        graph = visualizer._build_graph(triplets)

        # 1 узел триплета + "Конец процесса"
        assert len(graph.nodes) == 2
        assert "Конец процесса" in graph.nodes

        # Оба ребра ведут к "Конец процесса"
        edges = list(graph.edges)
        assert len(edges) == 2


class TestHelperMethods:
    """Тесты вспомогательных методов."""

    def test_needs_end_node_with_alternative(
        self, visualizer: GraphVisualizer
    ) -> None:
        """Если есть альтернатива - "Конец процесса" не нужен."""
        triplets = [
            Triplet(actor="a", action="b", obj="c", condition_text="cond"),
            Triplet(actor="d", action="e", obj="f", is_alternative=True),
        ]
        assert visualizer._needs_end_node(triplets) is False

    def test_needs_end_node_without_alternative(
        self, visualizer: GraphVisualizer
    ) -> None:
        """Если альтернативы нет - "Конец процесса" нужен."""
        triplets = [
            Triplet(actor="a", action="b", obj="c", condition_text="cond"),
            Triplet(actor="d", action="e", obj="f"),
        ]
        assert visualizer._needs_end_node(triplets) is True

    def test_find_next_regular(self, visualizer: GraphVisualizer) -> None:
        """Поиск следующего не-альтернативного триплета."""
        triplets = [
            Triplet(actor="a", action="b", obj="c", condition_text="cond"),
            Triplet(actor="d", action="e", obj="f", is_alternative=True),
            Triplet(actor="g", action="h", obj="i"),
        ]
        assert visualizer._find_next_regular(triplets, 0) == 2
        assert visualizer._find_next_regular(triplets, 1) == 2
        assert visualizer._find_next_regular(triplets, 2) is None

    def test_find_next_alternative(self, visualizer: GraphVisualizer) -> None:
        """Поиск следующего альтернативного триплета."""
        triplets = [
            Triplet(actor="a", action="b", obj="c", condition_text="cond"),
            Triplet(actor="d", action="e", obj="f", is_alternative=True),
            Triplet(actor="g", action="h", obj="i"),
        ]
        assert visualizer._find_next_alternative(triplets, 0) == 1
        assert visualizer._find_next_alternative(triplets, 1) is None
        assert visualizer._find_next_alternative(triplets, 2) is None

    def test_find_merge_point(self, visualizer: GraphVisualizer) -> None:
        """Поиск точки слияния."""
        triplets = [
            Triplet(actor="a", action="b", obj="c", condition_text="cond"),
            Triplet(actor="d", action="e", obj="f", is_alternative=True),
            Triplet(actor="g", action="h", obj="i"),
        ]
        assert visualizer._find_merge_point(triplets, 1) == 2
        assert visualizer._find_merge_point(triplets, 2) is None
