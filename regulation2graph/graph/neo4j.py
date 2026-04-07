"""
Модуль для работы с Neo4j.

Загрузка и сохранение бизнес-процессов в графовую базу данных Neo4j.
Модель с Decision-узлами (шлюзами):
    (Event)-[:LEADS_TO]->(Gateway)
    (Gateway)-[:IF_TRUE]->(NextEvent)
    (Gateway)-[:IF_FALSE]->(AlternativeEvent | End)
"""

from neo4j import GraphDatabase


class Neo4jLoader:
    """Загрузчик данных в Neo4j.

    Создаёт узлы Actor, Event и Gateway (шлюзы).
    Связи: PERFORMS, NEXT, LEADS_TO, IF_TRUE, IF_FALSE.
    """

    def __init__(self, uri: str, user: str, password: str) -> None:
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        """Закрывает соединение с Neo4j."""
        self.driver.close()

    def clear_database(self) -> None:
        """Очищает базу перед новой загрузкой."""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            print("[Neo4j] База данных очищена.")

    def save_process(self, events: list) -> None:
        """
        Сохраняет цепочку событий с Decision-узлами.

        Логика:
        - Обычное событие: (prev)-[:NEXT]->(curr)
        - Условное событие: (curr)-[:LEADS_TO]->(Gateway)
          затем (Gateway)-[:IF_TRUE]->(next_regular)
          и       (Gateway)-[:IF_FALSE]->(next_alternative | End)

        Args:
            events: Список событий с полями actor, action, object,
                    full_text, condition, is_alternative, gateway_type.
        """

        # Создание узла события
        CYPHER_CREATE_EVENT = """
        MERGE (a:Actor {name: $actor_name})
        CREATE (e:Event {
            uid: $uid,
            action: $action,
            object: $obj,
            full_text: $text,
            is_alternative: $is_alternative
        })
        CREATE (a)-[:PERFORMS]->(e)
        RETURN elementId(e) as node_id
        """

        # Создание Decision-узла (шлюза)
        CYPHER_CREATE_GATEWAY = """
        CREATE (g:Gateway {
            uid: $gateway_uid,
            type: $gateway_type,
            condition: $condition
        })
        RETURN elementId(g) as gateway_id
        """

        # Связывание события со шлюзом
        CYPHER_LINK_EVENT_TO_GATEWAY = """
        MATCH (e), (g)
        WHERE elementId(e) = $event_id AND elementId(g) = $gateway_id
        CREATE (e)-[:LEADS_TO]->(g)
        """

        # Связывание шлюза с следующим событием (IF_TRUE / IF_FALSE)
        CYPHER_LINK_GATEWAY_IF_TRUE = """
        MATCH (g), (e)
        WHERE elementId(g) = $gateway_id AND elementId(e) = $event_id
        CREATE (g)-[:IF_TRUE]->(e)
        """

        CYPHER_LINK_GATEWAY_IF_FALSE = """
        MATCH (g), (e)
        WHERE elementId(g) = $gateway_id AND elementId(e) = $event_id
        CREATE (g)-[:IF_FALSE]->(e)
        """

        # Обычная связь NEXT между событиями
        CYPHER_LINK_EVENTS = """
        MATCH (prev), (curr)
        WHERE elementId(prev) = $prev_id AND elementId(curr) = $curr_id
        CREATE (prev)-[:NEXT]->(curr)
        """

        with self.driver.session() as session:

            prev_event_id = None
            gateway_id_for_prev = None  # Шлюз, ждущий подключения IF_TRUE/IF_FALSE

            for i, event in enumerate(events):
                is_alternative = event.get("is_alternative", False)
                has_condition = event.get("condition") is not None

                # 1. Создаём событие
                params = {
                    "actor_name": event["actor"].capitalize(),
                    "uid": i,
                    "action": event["action"],
                    "obj": event["object"],
                    "text": event.get("full_text", ""),
                    "is_alternative": is_alternative,
                }
                result = session.run(CYPHER_CREATE_EVENT, **params)
                record = result.single()
                if not record:
                    print(f"[WARN] Не удалось создать узел {i}")
                    continue

                current_event_id = record["node_id"]

                # 2. Связываем с предыдущим
                if prev_event_id is not None:
                    # Если есть шлюз, ждущий подключения
                    if gateway_id_for_prev is not None:
                        # Альтернативная ветка → IF_FALSE, обычная → IF_TRUE
                        rel_query = (
                            CYPHER_LINK_GATEWAY_IF_FALSE
                            if is_alternative
                            else CYPHER_LINK_GATEWAY_IF_TRUE
                        )
                        session.run(
                            rel_query,
                            gateway_id=gateway_id_for_prev,
                            event_id=current_event_id,
                        )
                        gateway_id_for_prev = None
                    else:
                        session.run(
                            CYPHER_LINK_EVENTS,
                            prev_id=prev_event_id,
                            curr_id=current_event_id,
                        )

                # 3. Если у события есть условие — создаём шлюз
                if has_condition:
                    gateway_uid = f"gw_{i}"
                    gateway_type = event.get("gateway_type", "exclusive")

                    gw_result = session.run(
                        CYPHER_CREATE_GATEWAY,
                        gateway_uid=gateway_uid,
                        gateway_type=gateway_type,
                        condition=event["condition"],
                    )
                    gw_record = gw_result.single()
                    if gw_record:
                        current_gateway_id = gw_record["gateway_id"]

                        # Связываем событие со шлюзом
                        session.run(
                            CYPHER_LINK_EVENT_TO_GATEWAY,
                            event_id=current_event_id,
                            gateway_id=current_gateway_id,
                        )

                        # Запоминаем шлюз для подключения к следующему событию
                        gateway_id_for_prev = current_gateway_id

                prev_event_id = current_event_id

            print(f"[Neo4j] Успешно загружено {len(events)} событий.")
