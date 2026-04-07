"""
Точка входа приложения.

Запуск:
    python -m regulation2graph.main
    # или после установки пакета:
    reg2graph

Переменные окружения:
    USE_NEO4J=false          — отключить сохранение в Neo4j
    NEO4J_URI=bolt://localhost:7687
    NEO4J_USER=neo4j
    NEO4J_PASSWORD=your_password
"""

from regulation2graph.config.settings import get_settings
from regulation2graph.services import (
    extract_process,
    print_results,
    save_to_neo4j,
    visualize_process,
)


def load_sample_text() -> str:
    """Возвращает пример текста регламента.

    В будущем можно загружать из файла или API.
    """
    return """
    Менеджер получает заявку от клиента.
    Если заявка корректна, менеджер отправляет её директору.
    Директор подписывает приказ.
    Бухгалтер начисляет премию.
    """


def main() -> None:
    """Главная функция — оркестратор."""
    settings = get_settings()
    text = load_sample_text()

    print("=" * 60)
    print("Regulation2Graph - Анализатор бизнес-процессов")
    print("=" * 60)
    print(f"\nВходной текст:\n{text}")
    print("-" * 60)

    # Пайплайн обработки
    triplets = extract_process(text)
    print_results(triplets)
    visualize_process(triplets)
    save_to_neo4j(triplets, settings)


if __name__ == "__main__":
    main()
