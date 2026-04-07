"""Сервис сохранения бизнес-процесса в Neo4j."""

import os

from regulation2graph.config.settings import Settings
from regulation2graph.graph import Neo4jLoader
from regulation2graph.models import Triplet


def save_to_neo4j(triplets: list[Triplet], settings: Settings) -> None:
    """Сохраняет извлечённые триплеты в Neo4j.

    Args:
        triplets: Список триплетов для сохранения.
        settings: Настройки приложения.

    Проверяет переменную окружения USE_NEO4J.
    Если USE_NEO4J=false, операция пропускается.
    """
    use_neo4j = os.getenv("USE_NEO4J", "true").lower() == "true"
    if not use_neo4j:
        return

    # Преобразуем триплеты в формат событий
    events = []
    for i, t in enumerate(triplets):
        events.append({
            "actor": t.actor,
            "action": t.action,
            "object": t.obj,
            "full_text": f"{t.actor} {t.action} {t.obj}",
            "condition": t.condition_text,
            "is_alternative": t.is_alternative,
            "gateway_type": t.gateway_type.value if t.gateway_type else None,
        })

    # Подключаемся и сохраняем
    neo4j = Neo4jLoader(
        uri=settings.neo4j.uri,
        user=settings.neo4j.user,
        password=settings.neo4j.password,
    )

    try:
        print("\n" + "-" * 60)
        print("Сохранение в Neo4j...")
        neo4j.clear_database()
        neo4j.save_process(events)
        print("[OK] Данные успешно сохранены в Neo4j")
    except Exception as e:
        print(f"[ERROR] Ошибка при сохранении в Neo4j: {e}")
    finally:
        neo4j.close()
