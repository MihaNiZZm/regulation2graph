# Импорты из нашего пакета src
from src.core.extractor import RuleBasedExtractor
from src.graph.visualizer import GraphVisualizer


def main():
    # 1. Подготовка данных (потом будем читать из файла)
    text = """
    Если клиент прислал анкету, менеджер проверяет данные. 
    Затем директор подписывает приказ. 
    Бухгалтер начисляет премию.
    """

    print(">>> Запуск анализатора...")

    # 2. Инициализация и запуск экстрактора
    extractor = RuleBasedExtractor()
    triplets = extractor.parse_text(text)

    # 3. Вывод в консоль
    print(f"Извлечено {len(triplets)} шагов:")
    for t in triplets:
        print(f" - {t}")

    # 4. Визуализация
    viz = GraphVisualizer()
    viz.build_and_show(triplets)


if __name__ == "__main__":
    main()
