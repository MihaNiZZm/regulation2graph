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
from regulation2graph.models import GatewayType, Triplet


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
        Строит NetworkX MultiDiGraph из списка триплетов с Gateway-узлами.

        Логика:
        - Обычный триплет: узел события, связь NEXT к следующему
        - Триплет с условием: создаётся Gateway-узел
          (Event)-[:LEADS_TO]->(Gateway)-[:IF_TRUE]->(Next)
          (Gateway)-[:IF_FALSE]->(Alternative | End)
        """
        graph = nx.MultiDiGraph()

        if not triplets:
            return graph

        end_node = "Конец процесса"

        # Создаём имена узлов для событий
        event_names = [f"{i + 1}. {t.display_name}" for i, t in enumerate(triplets)]

        # Добавляем узлы событий
        for i, triplet in enumerate(triplets):
            graph.add_node(
                event_names[i],
                node_type="event",
                triplet=triplet,
                is_alternative=triplet.is_alternative,
            )

        # Определяем, нужен ли терминальный узел
        needs_end = any(t.has_condition for t in triplets)
        if needs_end:
            graph.add_node(end_node, node_type="end", is_end=True)

        # Строим рёбра
        pending_gateway_idx = None  # Индекс события со шлюзом, ждущим подключения

        for i, triplet in enumerate(triplets):
            current_event = event_names[i]

            # Если есть незавершённый шлюз — подключаем его
            if pending_gateway_idx is not None:
                gateway_condition = triplets[pending_gateway_idx].condition_text
                gateway_label = f"◇ {gateway_condition}"

                # Находим следующий не-альтернативный для IF_TRUE
                next_regular = self._find_next_regular(triplets, pending_gateway_idx)
                # Находим альтернативу для IF_FALSE
                next_alt = self._find_next_alternative(triplets, pending_gateway_idx)

                if next_regular is not None:
                    graph.add_edge(
                        gateway_label, event_names[next_regular],
                        label="Да", relation="IF_TRUE",
                    )
                else:
                    graph.add_edge(
                        gateway_label, end_node,
                        label="Да", relation="IF_TRUE",
                    )

                if next_alt is not None:
                    graph.add_edge(
                        gateway_label, event_names[next_alt],
                        label="Нет", relation="IF_FALSE",
                    )
                else:
                    graph.add_edge(
                        gateway_label, end_node,
                        label="Нет", relation="IF_FALSE",
                    )

                pending_gateway_idx = None

            # Если текущий триплет имеет условие — создаём Gateway
            if triplet.has_condition:
                gateway_condition = triplet.condition_text
                gateway_label = f"◇ {gateway_condition}"

                graph.add_node(
                    gateway_label,
                    node_type="gateway",
                    condition=gateway_condition,
                    gateway_type=triplet.gateway_type,
                )

                # Связь Event → Gateway
                graph.add_edge(current_event, gateway_label, label="", relation="LEADS_TO")

                # Запоминаем, что шлюз ждёт подключения
                pending_gateway_idx = i

            elif triplet.is_alternative:
                # Альтернативная ветка — будет подключена к шлюзу выше
                merge_point = self._find_merge_point(triplets, i)
                if merge_point is not None:
                    graph.add_edge(current_event, event_names[merge_point], label="")
                else:
                    graph.add_edge(current_event, end_node, label="")

            else:
                # Обычный триплет — связываем со следующим
                if i + 1 < len(triplets):
                    next_t = triplets[i + 1]
                    if next_t.is_alternative:
                        # Пропускаем альтернативу, ищем regular
                        next_regular = self._find_next_regular(triplets, i)
                        if next_regular is not None:
                            graph.add_edge(current_event, event_names[next_regular], label="")
                    else:
                        graph.add_edge(current_event, event_names[i + 1], label="")

        return graph

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
        node_shapes = []  # Для будущих улучшений
        for node in graph.nodes:
            data = graph.nodes[node]
            node_type = data.get("node_type", "event")
            if node_type == "end":
                node_colors.append(self._settings.end_node_color)
            elif node_type == "gateway":
                node_colors.append("orange")  # Gateway — ромб
            elif data.get("is_alternative"):
                node_colors.append("lightgreen")  # Альтернативная ветка
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
