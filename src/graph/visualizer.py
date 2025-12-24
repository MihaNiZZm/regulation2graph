import matplotlib
# Принудительно ставим бэкенд "Agg" (Anti-Grain Geometry).
# Он умеет ТОЛЬКО сохранять в файлы, никакого UI.
matplotlib.use('Agg')

import networkx as nx
import matplotlib.pyplot as plt


class GraphVisualizer:
    def build_and_show(self, triplets: list):
        graph = nx.DiGraph()
        edge_labels = {}

        # Создаем узлы и связи
        prev_node = None
        for i, t in enumerate(triplets):
            # Формируем красивое название узла
            node_name = f"{i + 1}. {t['actor'].upper()}\n{t['action']}\n{t['object']}"

            graph.add_node(node_name)

            if prev_node:
                # Если было условие, подписываем ребро
                label = "Если..." if t['condition'] else ""
                graph.add_edge(prev_node, node_name, label=label)
                if label:
                    edge_labels[(prev_node, node_name)] = label

            prev_node = node_name

        self._plot(graph, edge_labels)

    def _plot(self, G, edge_labels):
        plt.figure(figsize=(10, 6))
        pos = nx.spring_layout(G, seed=42)

        nx.draw(
            G, pos,
            with_labels=True,
            node_color='lightblue',
            node_size=4000,
            font_size=8
        )

        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels)
        plt.title("Граф бизнес-процесса")

        output_path = "process_graph.png"
        plt.savefig(output_path)
        print(f"\n[SUCCESS] Граф успешно сохранен в файл: {output_path}")
        plt.close()
