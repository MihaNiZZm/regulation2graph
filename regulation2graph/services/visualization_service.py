"""Сервис визуализации бизнес-процесса."""

from regulation2graph.graph import GraphVisualizer
from regulation2graph.models import Triplet


def visualize_process(triplets: list[Triplet]) -> None:
    """Строит и сохраняет граф процесса.

    Args:
        triplets: Список триплетов для визуализации.
    """
    print("\n" + "-" * 60)
    viz = GraphVisualizer()
    viz.build_and_show(triplets)
