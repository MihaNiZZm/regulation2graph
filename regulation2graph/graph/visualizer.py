"""
Визуализация графа бизнес-процесса.

Использует NetworkX для построения графа и Matplotlib для отрисовки.
"""

import matplotlib

matplotlib.use("Agg")  # Бэкенд без GUI, только сохранение в файлы

import os
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx

from regulation2graph.config import get_settings
from regulation2graph.models import Triplet


class GraphVisualizer:
    """
    Строит и визуализирует граф бизнес-процесса из списка триплетов.

    Example:
        >>> viz = GraphVisualizer()
        >>> viz.build_and_show(triplets, output_path="my_graph.png")
    """

    def __init__(self) -> None:
        self._settings = get_settings().visualization

    def build_and_show(
        self,
        triplets: list[Triplet],
        output_path: str | None = None,
    ) -> nx.MultiDiGraph:
        """
        Строит граф из триплетов и сохраняет визуализацию.

        Args:
            triplets: Список триплетов для визуализации.
            output_path: Путь для сохранения изображения.
                        Если None, используется настройка по умолчанию.

        Returns:
            Построенный граф NetworkX.
        """
        graph = self._build_graph(triplets)
        self._plot(graph, triplets, output_path)
        return graph

    def _build_graph(self, triplets: list[Triplet]) -> nx.MultiDiGraph:
        """
        Строит NetworkX MultiDiGraph из списка триплетов с поддержкой ветвления.

        Используем MultiDiGraph для поддержки параллельных рёбер
        (например, когда "Да" и "Нет" ведут к одному узлу).

        Логика ветвления:
        - Узел с условием имеет 2 исходящих ребра: "Да" и "Нет"
        - "Да" ведёт к следующему не-альтернативному узлу
        - "Нет" ведёт к альтернативе или к "Конец процесса"
        - Альтернативная ветка сливается с основной
        """
        graph = nx.MultiDiGraph()

        if not triplets:
            return graph

        # Константа для терминального узла
        end_node = "Конец процесса"

        # 1. Создаём имена узлов для всех триплетов
        node_names = [f"{i + 1}. {t.display_name}" for i, t in enumerate(triplets)]

        # 2. Добавляем все узлы триплетов
        for i, triplet in enumerate(triplets):
            graph.add_node(
                node_names[i],
                triplet=triplet,
                has_condition=triplet.has_condition,
                is_alternative=triplet.is_alternative,
            )

        # 3. Определяем, нужен ли терминальный узел
        needs_end_node = self._needs_end_node(triplets)
        if needs_end_node:
            graph.add_node(end_node, is_end=True)

        # 4. Строим рёбра с учётом ветвления
        i = 0
        while i < len(triplets):
            triplet = triplets[i]
            current_node = node_names[i]

            if triplet.has_condition:
                # Узел с условием - нужно ветвление
                next_regular_idx = self._find_next_regular(triplets, i)
                next_alternative_idx = self._find_next_alternative(triplets, i)

                # Ребро "Да" → следующий не-альтернативный узел
                if next_regular_idx is not None:
                    graph.add_edge(current_node, node_names[next_regular_idx], label="Да")
                else:
                    graph.add_edge(current_node, end_node, label="Да")

                # Ребро "Нет" → альтернатива или "Конец процесса"
                if next_alternative_idx is not None:
                    graph.add_edge(current_node, node_names[next_alternative_idx], label="Нет")
                else:
                    graph.add_edge(current_node, end_node, label="Нет")

            elif triplet.is_alternative:
                # Альтернативная ветка - соединяем с точкой слияния
                merge_point_idx = self._find_merge_point(triplets, i)
                if merge_point_idx is not None:
                    graph.add_edge(current_node, node_names[merge_point_idx], label="")
                else:
                    graph.add_edge(current_node, end_node, label="")

            else:
                # Обычный узел - соединяем со следующим
                if i + 1 < len(triplets):
                    next_triplet = triplets[i + 1]
                    # Пропускаем альтернативы (они уже подключены к условию)
                    if not next_triplet.is_alternative:
                        graph.add_edge(current_node, node_names[i + 1], label="")
                    else:
                        # Ищем следующий не-альтернативный
                        next_regular = self._find_next_regular(triplets, i)
                        if next_regular is not None:
                            graph.add_edge(current_node, node_names[next_regular], label="")

            i += 1

        return graph

    def _needs_end_node(self, triplets: list[Triplet]) -> bool:
        """Проверяет, нужен ли терминальный узел."""
        for i, triplet in enumerate(triplets):
            if triplet.has_condition:
                # Есть ли альтернатива для этого условия?
                next_alt = self._find_next_alternative(triplets, i)
                if next_alt is None:
                    return True
        return False

    def _find_next_regular(self, triplets: list[Triplet], current_idx: int) -> int | None:
        """Находит индекс следующего не-альтернативного триплета."""
        for j in range(current_idx + 1, len(triplets)):
            if not triplets[j].is_alternative:
                return j
        return None

    def _find_next_alternative(self, triplets: list[Triplet], current_idx: int) -> int | None:
        """Находит индекс следующего альтернативного триплета (сразу после условия)."""
        if current_idx + 1 < len(triplets) and triplets[current_idx + 1].is_alternative:
            return current_idx + 1
        return None

    def _find_merge_point(self, triplets: list[Triplet], alt_idx: int) -> int | None:
        """Находит точку слияния для альтернативной ветки."""
        # Точка слияния - первый не-альтернативный узел после альтернативы
        for j in range(alt_idx + 1, len(triplets)):
            if not triplets[j].is_alternative:
                return j
        return None

    def _plot(
        self,
        graph: nx.MultiDiGraph,
        triplets: list[Triplet],  # noqa: ARG002
        output_path: str | None,
    ) -> None:
        """Отрисовывает граф и сохраняет в файл."""
        if not graph.nodes:
            print("[WARNING] Граф пустой, нечего визуализировать")
            return

        fig, ax = plt.subplots(figsize=self._settings.figure_size)

        # Layout
        pos = nx.spring_layout(graph, seed=42, k=2)

        # Цвета узлов в зависимости от типа
        node_colors = []
        for node in graph.nodes:
            data = graph.nodes[node]
            if data.get("is_end"):
                node_colors.append(self._settings.end_node_color)
            elif data.get("is_alternative"):
                node_colors.append("lightgreen")  # Альтернативная ветка
            elif data.get("has_condition"):
                node_colors.append(self._settings.condition_node_color)
            else:
                node_colors.append(self._settings.node_color)

        # Рисуем узлы
        nx.draw_networkx_nodes(
            graph,
            pos,
            node_color=node_colors,
            node_size=self._settings.node_size,
            ax=ax,
        )

        # Рисуем рёбра
        nx.draw_networkx_edges(
            graph,
            pos,
            edge_color="gray",
            arrows=True,
            arrowsize=20,
            ax=ax,
        )

        # Подписи узлов
        nx.draw_networkx_labels(
            graph,
            pos,
            font_size=self._settings.font_size,
            ax=ax,
        )

        # Подписи рёбер (для MultiDiGraph ключи имеют формат (u, v, key))
        edge_labels_raw = nx.get_edge_attributes(graph, "label")
        # Преобразуем в формат (u, v) -> label для отображения
        # Если есть параллельные рёбра, объединяем метки
        edge_labels: dict[tuple[str, str], str] = {}
        for (u, v, _), label in edge_labels_raw.items():
            if label:
                key = (u, v)
                if key in edge_labels:
                    edge_labels[key] = f"{edge_labels[key]}/{label}"
                else:
                    edge_labels[key] = label

        if edge_labels:
            nx.draw_networkx_edge_labels(
                graph,
                pos,
                edge_labels=edge_labels,
                font_size=self._settings.font_size,
                ax=ax,
            )

        ax.set_title("Граф бизнес-процесса", fontsize=14, fontweight="bold")
        ax.axis("off")

        # Сохранение
        if output_path is None:
            output_dir = Path(self._settings.output_dir)
            output_dir.mkdir(exist_ok=True)
            output_path = str(output_dir / self._settings.default_filename)

        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"\n[SUCCESS] Граф сохранён: {output_path}")
        plt.close()
