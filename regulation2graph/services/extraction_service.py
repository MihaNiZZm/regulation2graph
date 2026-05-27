"""Сервис извлечения WorkflowNet из текста регламента."""

from regulation2graph.core import RuleBasedExtractor
from regulation2graph.models import Triplet, WorkflowNet


def extract_workflow(text: str) -> WorkflowNet:
    """Извлекает WorkflowNet из текста.

    Args:
        text: Текст регламента.

    Returns:
        WorkflowNet с Places, Transitions и Arcs.
    """
    extractor = RuleBasedExtractor()
    return extractor.extract(text)


def extract_process(text: str) -> list[Triplet]:
    """DEPRECATED: Используйте extract_workflow() вместо этого.

    Оставлен для обратной совместимости.
    """
    extractor = RuleBasedExtractor()
    return extractor.parse_text(text)


def print_workflow(workflow: WorkflowNet) -> None:
    """Выводит информацию о WorkflowNet в консоль.

    Args:
        workflow: WorkflowNet для отображения.
    """
    print(f"\n{'=' * 50}")
    print("Извлечённый Workflow Net:")
    print(f"{'=' * 50}")
    print(f"  Places: {len(workflow.places)}")
    print(f"  Transitions: {len(workflow.transitions)}")
    print(f"  Arcs: {len(workflow.arcs)}")
    print()

    print("Transitions (действия):")
    for i, t in enumerate(workflow.transitions, 1):
        guard_info = f" [guard: {t.guard}]" if t.has_guard else ""
        print(f"  {i}. {t.actor} → {t.action} → {t.obj}{guard_info}")

    print()
    print("Places (состояния):")
    for p in workflow.places:
        type_marker = "●" if p.is_start else ("◯" if p.is_end else "○")
        print(f"  {type_marker} {p.id}: {p.name}")

    print()
    print("Arcs (связи):")
    for arc in workflow.arcs:
        label_info = f" [{arc.label}]" if arc.label else ""
        print(f"  {arc.source_id} → {arc.target_id}{label_info}")


def print_results(triplets: list[Triplet]) -> None:
    """DEPRECATED: Используйте print_workflow() вместо этого.

    Оставлен для обратной совместимости.
    """
    print(f"\nИзвлечено {len(triplets)} шагов процесса:\n")
    for i, t in enumerate(triplets, 1):
        condition_info = f" [Условие: {t.condition_text}]" if t.has_condition else ""
        alt_info = " [Альтернатива]" if t.is_alternative else ""
        print(f"  {i}. {t.actor} → {t.action} → {t.obj}{condition_info}{alt_info}")
