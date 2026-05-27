"""
Модуль для работы с Neo4j.

Загрузка и сохранение Workflow Net в графовую базу данных Neo4j.

Схема данных:
    (:Place {id, name, type})
    (:Transition {id, actor, action, object, guard})
    (:Place)-[:FLOW {label}]->(:Transition)
    (:Transition)-[:FLOW]->(:Place)
"""

from neo4j import GraphDatabase

from regulation2graph.models import WorkflowNet


class Neo4jLoader:
    """
    Загрузчик Workflow Net в Neo4j.

    Создаёт узлы Place и Transition, связанные через FLOW.
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

    def save_workflow(self, workflow: WorkflowNet) -> None:
        """
        Сохраняет WorkflowNet в Neo4j.

        Args:
            workflow: WorkflowNet с Places, Transitions и Arcs.
        """
        with self.driver.session() as session:
            # 1. Создаём все Places
            for place in workflow.places:
                session.run(
                    """
                    CREATE (:Place {
                        id: $id,
                        name: $name,
                        type: $type
                    })
                    """,
                    id=place.id,
                    name=place.name,
                    type=place.place_type.value,
                )

            # 2. Создаём все Transitions
            for transition in workflow.transitions:
                session.run(
                    """
                    CREATE (:Transition {
                        id: $id,
                        actor: $actor,
                        action: $action,
                        object: $object,
                        guard: $guard,
                        full_text: $full_text
                    })
                    """,
                    id=transition.id,
                    actor=transition.actor,
                    action=transition.action,
                    object=transition.obj,
                    guard=transition.guard,
                    full_text=transition.full_text,
                )

            # 3. Создаём все Arcs (FLOW)
            for arc in workflow.arcs:
                session.run(
                    """
                    MATCH (source {id: $source_id})
                    MATCH (target {id: $target_id})
                    CREATE (source)-[:FLOW {label: $label}]->(target)
                    """,
                    source_id=arc.source_id,
                    target_id=arc.target_id,
                    label=arc.label,
                )

            print(
                f"[Neo4j] Сохранено: "
                f"{len(workflow.places)} Places, "
                f"{len(workflow.transitions)} Transitions, "
                f"{len(workflow.arcs)} Arcs."
            )

    def save_process(self, events: list) -> None:
        """
        DEPRECATED: Используйте save_workflow() вместо этого метода.

        Оставлен для обратной совместимости.
        Конвертирует старый формат events в WorkflowNet и сохраняет.
        """
        from regulation2graph.models import Arc, Place, PlaceType, Transition

        places = [Place("p_start", "Начало", PlaceType.START)]
        transitions = []
        arcs = []

        current_place_id = "p_start"

        for i, event in enumerate(events):
            t_id = f"t{i}"

            transition = Transition(
                id=t_id,
                actor=event.get("actor", "Unknown"),
                action=event.get("action", ""),
                obj=event.get("object", "-"),
                guard=event.get("condition"),
                full_text=event.get("full_text", ""),
            )
            transitions.append(transition)

            p_after = Place(f"p{i + 1}", f"После: {event.get('action', '')}", PlaceType.INTERMEDIATE)
            places.append(p_after)

            arcs.append(Arc(current_place_id, t_id))
            arcs.append(Arc(t_id, p_after.id))
            current_place_id = p_after.id

        places.append(Place("p_end", "Конец", PlaceType.END))
        arcs.append(Arc(current_place_id, "p_end"))

        workflow = WorkflowNet(places=places, transitions=transitions, arcs=arcs)
        self.save_workflow(workflow)
