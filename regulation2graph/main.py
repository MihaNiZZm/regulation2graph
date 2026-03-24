"""
Точка входа приложения.

Запуск:
    python -m regulation2graph.main
    # или после установки пакета:
    reg2graph
"""

from regulation2graph.core import RuleBasedExtractor
from regulation2graph.graph import GraphVisualizer


def main() -> None:
    """Главная функция - демонстрация работы системы."""
    # Пример текста регламента
    text = """
    Менеджер получает заявку от клиента.
    Если заявка корректна, менеджер отправляет её директору.
    Директор подписывает приказ.
    Бухгалтер начисляет премию.
    """

    print("=" * 60)
    print("Regulation2Graph - Анализатор бизнес-процессов")
    print("=" * 60)
    print(f"\nВходной текст:\n{text}")
    print("-" * 60)

    # Извлечение триплетов
    extractor = RuleBasedExtractor()
    triplets = extractor.parse_text(text)

    # Вывод результатов
    print(f"\nИзвлечено {len(triplets)} шагов процесса:\n")
    for i, t in enumerate(triplets, 1):
        condition_info = f" [Условие: {t.condition_text}]" if t.has_condition else ""
        alt_info = " [Альтернатива]" if t.is_alternative else ""
        print(f"  {i}. {t.actor} → {t.action} → {t.obj}{condition_info}{alt_info}")

    # Визуализация
    print("\n" + "-" * 60)
    viz = GraphVisualizer()
    viz.build_and_show(triplets)


if __name__ == "__main__":
    main()
