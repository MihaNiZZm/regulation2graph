"""
Бенчмарк с метриками качества извлечения триплетов.

Сравнивает результаты системы с ground truth из размеченных данных.
Вычисляет Precision, Recall, F1 на уровне триплетов.

Запуск:
    python -m tests.benchmarks.benchmark_metrics
    python -m tests.benchmarks.benchmark_metrics --report  # генерирует markdown отчёт
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from regulation2graph.core.extractor import RuleBasedExtractor


def _normalize_text(text: str) -> str:
    """Нормализует текст для сравнения: lowercase, strip, ё -> е."""
    return text.lower().strip().replace("ё", "е")


@dataclass
class Triplet:
    """Триплет для сравнения."""

    actor: str
    action: str
    object: str
    condition: str | None = None
    is_alternative: bool = False

    def normalize(self) -> "Triplet":
        """Нормализует триплет для сравнения."""
        return Triplet(
            actor=_normalize_text(self.actor),
            action=_normalize_text(self.action),
            object=_normalize_text(self.object),
            condition=_normalize_text(self.condition) if self.condition else None,
            is_alternative=self.is_alternative,
        )

    def matches(self, other: "Triplet", strict: bool = False) -> bool:
        """
        Проверяет совпадение с другим триплетом.

        Args:
            other: Другой триплет для сравнения.
            strict: Если True, сравнивает также condition и is_alternative.
        """
        self_norm = self.normalize()
        other_norm = other.normalize()

        # Базовое сравнение: actor, action, object
        base_match = (
            self_norm.actor == other_norm.actor
            and self_norm.action == other_norm.action
            and self_norm.object == other_norm.object
        )

        if not strict:
            return base_match

        # Строгое сравнение: включает condition и is_alternative
        condition_match = (
            (self_norm.condition is None and other_norm.condition is None)
            or (
                self_norm.condition is not None
                and other_norm.condition is not None
                and self_norm.condition in other_norm.condition
            )
            or (
                self_norm.condition is not None
                and other_norm.condition is not None
                and other_norm.condition in self_norm.condition
            )
        )

        return base_match and condition_match


@dataclass
class TestCase:
    """Тестовый пример с ground truth."""

    id: str
    text: str
    expected: list[Triplet]
    complexity: str
    tags: list[str]
    notes: str | None = None
    source: str = "synthetic"


@dataclass
class TestResult:
    """Результат теста одного примера."""

    test_case: TestCase
    predicted: list[Triplet]
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0

    @property
    def precision(self) -> float:
        if self.true_positives + self.false_positives == 0:
            return 0.0
        return self.true_positives / (self.true_positives + self.false_positives)

    @property
    def recall(self) -> float:
        if self.true_positives + self.false_negatives == 0:
            return 0.0
        return self.true_positives / (self.true_positives + self.false_negatives)

    @property
    def f1(self) -> float:
        if self.precision + self.recall == 0:
            return 0.0
        return 2 * self.precision * self.recall / (self.precision + self.recall)

    @property
    def is_perfect(self) -> bool:
        return self.false_positives == 0 and self.false_negatives == 0


@dataclass
class BenchmarkReport:
    """Общий отчёт по бенчмарку."""

    results: list[TestResult]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    @property
    def total_cases(self) -> int:
        return len(self.results)

    @property
    def perfect_cases(self) -> int:
        return sum(1 for r in self.results if r.is_perfect)

    @property
    def total_tp(self) -> int:
        return sum(r.true_positives for r in self.results)

    @property
    def total_fp(self) -> int:
        return sum(r.false_positives for r in self.results)

    @property
    def total_fn(self) -> int:
        return sum(r.false_negatives for r in self.results)

    @property
    def micro_precision(self) -> float:
        if self.total_tp + self.total_fp == 0:
            return 0.0
        return self.total_tp / (self.total_tp + self.total_fp)

    @property
    def micro_recall(self) -> float:
        if self.total_tp + self.total_fn == 0:
            return 0.0
        return self.total_tp / (self.total_tp + self.total_fn)

    @property
    def micro_f1(self) -> float:
        if self.micro_precision + self.micro_recall == 0:
            return 0.0
        return (
            2
            * self.micro_precision
            * self.micro_recall
            / (self.micro_precision + self.micro_recall)
        )

    @property
    def macro_precision(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.precision for r in self.results) / len(self.results)

    @property
    def macro_recall(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.recall for r in self.results) / len(self.results)

    @property
    def macro_f1(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.f1 for r in self.results) / len(self.results)

    def by_complexity(self, complexity: str) -> list[TestResult]:
        return [r for r in self.results if r.test_case.complexity == complexity]

    def by_tag(self, tag: str) -> list[TestResult]:
        return [r for r in self.results if tag in r.test_case.tags]


def load_test_cases(path: Path) -> list[TestCase]:
    """Загружает тестовые примеры из JSONL файла."""
    cases = []
    with open(path) as f:
        for line in f:
            if not line.strip():
                continue
            data = json.loads(line)
            expected = [
                Triplet(
                    actor=t["actor"],
                    action=t["action"],
                    object=t["object"],
                    condition=t.get("condition"),
                    is_alternative=t.get("is_alternative", False),
                )
                for t in data["expected_triplets"]
            ]
            cases.append(
                TestCase(
                    id=data["id"],
                    text=data["text"],
                    expected=expected,
                    complexity=data.get("complexity", "medium"),
                    tags=data.get("tags", []),
                    notes=data.get("notes"),
                    source=data.get("source", "synthetic"),
                )
            )
    return cases


def evaluate_case(
    extractor: RuleBasedExtractor, case: TestCase, strict: bool = False
) -> TestResult:
    """Оценивает один тестовый пример."""
    workflow = extractor.extract(case.text)

    # Конвертируем результаты в Triplet
    predicted = [
        Triplet(
            actor=t.actor,
            action=t.action,
            object=t.obj,
            condition=t.guard,
            is_alternative=getattr(t, "_is_alternative", False),
        )
        for t in workflow.transitions
    ]

    # Считаем метрики
    expected_matched = [False] * len(case.expected)
    predicted_matched = [False] * len(predicted)

    for i, exp in enumerate(case.expected):
        for j, pred in enumerate(predicted):
            if not predicted_matched[j] and exp.matches(pred, strict=strict):
                expected_matched[i] = True
                predicted_matched[j] = True
                break

    tp = sum(expected_matched)
    fp = sum(1 for m in predicted_matched if not m)
    fn = sum(1 for m in expected_matched if not m)

    return TestResult(
        test_case=case,
        predicted=predicted,
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
    )


def run_benchmark(
    data_path: Path | None = None,
    strict: bool = False,
    use_coreference: bool = False,
) -> BenchmarkReport:
    """
    Запускает бенчмарк на всех тестовых примерах.

    Args:
        data_path: Путь к JSONL файлу с тестовыми примерами.
        strict: Строгое сравнение (включая условия).
        use_coreference: Использовать резолвер кореференции.
    """
    if data_path is None:
        data_path = Path(__file__).parent.parent.parent / "data/annotated/regulations.jsonl"

    cases = load_test_cases(data_path)

    # Создаём экстрактор с опциональной кореференцией
    coref_resolver = None
    if use_coreference:
        from regulation2graph.core.coreference import RuleBasedResolver
        coref_resolver = RuleBasedResolver()

    extractor = RuleBasedExtractor(coreference_resolver=coref_resolver)

    results = [evaluate_case(extractor, case, strict=strict) for case in cases]

    return BenchmarkReport(results=results)


def generate_markdown_report(report: BenchmarkReport) -> str:
    """Генерирует markdown отчёт."""
    lines = [
        "# Benchmark Report",
        "",
        f"**Generated:** {report.timestamp}",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total cases | {report.total_cases} |",
        f"| Perfect cases | {report.perfect_cases} ({report.perfect_cases/report.total_cases*100:.1f}%) |",
        f"| Micro Precision | {report.micro_precision:.3f} |",
        f"| Micro Recall | {report.micro_recall:.3f} |",
        f"| Micro F1 | {report.micro_f1:.3f} |",
        f"| Macro Precision | {report.macro_precision:.3f} |",
        f"| Macro Recall | {report.macro_recall:.3f} |",
        f"| Macro F1 | {report.macro_f1:.3f} |",
        "",
        "## By Complexity",
        "",
        "| Complexity | Cases | Perfect | Precision | Recall | F1 |",
        "|------------|-------|---------|-----------|--------|-----|",
    ]

    for complexity in ["simple", "medium", "hard"]:
        subset = report.by_complexity(complexity)
        if not subset:
            continue
        perfect = sum(1 for r in subset if r.is_perfect)
        tp = sum(r.true_positives for r in subset)
        fp = sum(r.false_positives for r in subset)
        fn = sum(r.false_negatives for r in subset)
        p = tp / (tp + fp) if tp + fp > 0 else 0
        r = tp / (tp + fn) if tp + fn > 0 else 0
        f1 = 2 * p * r / (p + r) if p + r > 0 else 0
        lines.append(
            f"| {complexity} | {len(subset)} | {perfect} ({perfect/len(subset)*100:.0f}%) | {p:.3f} | {r:.3f} | {f1:.3f} |"
        )

    lines.extend(
        [
            "",
            "## By Tag",
            "",
            "| Tag | Cases | Perfect | F1 |",
            "|-----|-------|---------|-----|",
        ]
    )

    # Собираем все теги
    all_tags = set()
    for r in report.results:
        all_tags.update(r.test_case.tags)

    for tag in sorted(all_tags):
        subset = report.by_tag(tag)
        if not subset:
            continue
        perfect = sum(1 for r in subset if r.is_perfect)
        tp = sum(r.true_positives for r in subset)
        fp = sum(r.false_positives for r in subset)
        fn = sum(r.false_negatives for r in subset)
        p = tp / (tp + fp) if tp + fp > 0 else 0
        r_val = tp / (tp + fn) if tp + fn > 0 else 0
        f1 = 2 * p * r_val / (p + r_val) if p + r_val > 0 else 0
        lines.append(f"| {tag} | {len(subset)} | {perfect} | {f1:.3f} |")

    # Детализация ошибок
    lines.extend(
        [
            "",
            "## Failed Cases",
            "",
        ]
    )

    for result in report.results:
        if result.is_perfect:
            continue

        lines.extend(
            [
                f"### {result.test_case.id} ({result.test_case.complexity})",
                "",
                f"**Text:** {result.test_case.text}",
                "",
                f"**Tags:** {', '.join(result.test_case.tags)}",
                "",
                "**Expected:**",
            ]
        )
        for t in result.test_case.expected:
            cond = f" [если: {t.condition}]" if t.condition else ""
            alt = " (ALT)" if t.is_alternative else ""
            lines.append(f"- ({t.actor}, {t.action}, {t.object}){cond}{alt}")

        lines.append("")
        lines.append("**Predicted:**")
        for t in result.predicted:
            cond = f" [если: {t.condition}]" if t.condition else ""
            alt = " (ALT)" if t.is_alternative else ""
            lines.append(f"- ({t.actor}, {t.action}, {t.object}){cond}{alt}")

        if result.test_case.notes:
            lines.append("")
            lines.append(f"**Notes:** {result.test_case.notes}")

        lines.append("")
        lines.append(
            f"**Metrics:** TP={result.true_positives}, FP={result.false_positives}, FN={result.false_negatives}"
        )
        lines.append("")

    return "\n".join(lines)


def print_summary(report: BenchmarkReport) -> None:
    """Выводит краткую сводку в консоль."""
    print("\n" + "=" * 60)
    print("BENCHMARK SUMMARY")
    print("=" * 60)
    print(f"Total cases:     {report.total_cases}")
    print(
        f"Perfect cases:   {report.perfect_cases} ({report.perfect_cases/report.total_cases*100:.1f}%)"
    )
    print(f"Micro Precision: {report.micro_precision:.3f}")
    print(f"Micro Recall:    {report.micro_recall:.3f}")
    print(f"Micro F1:        {report.micro_f1:.3f}")
    print("-" * 60)

    for complexity in ["simple", "medium", "hard"]:
        subset = report.by_complexity(complexity)
        if not subset:
            continue
        perfect = sum(1 for r in subset if r.is_perfect)
        tp = sum(r.true_positives for r in subset)
        fp = sum(r.false_positives for r in subset)
        fn = sum(r.false_negatives for r in subset)
        p = tp / (tp + fp) if tp + fp > 0 else 0
        r = tp / (tp + fn) if tp + fn > 0 else 0
        f1 = 2 * p * r / (p + r) if p + r > 0 else 0
        print(f"{complexity.upper():8} | {len(subset):2} cases | {perfect:2} perfect | F1={f1:.3f}")

    print("=" * 60)


if __name__ == "__main__":
    import sys

    # Парсим аргументы
    use_coref = "--coref" in sys.argv
    generate_report = "--report" in sys.argv

    if use_coref:
        print("Running benchmark WITH coreference resolution...")
    else:
        print("Running benchmark WITHOUT coreference resolution...")
        print("(use --coref to enable coreference)")

    report = run_benchmark(use_coreference=use_coref)
    print_summary(report)

    if generate_report:
        report_path = Path(__file__).parent.parent.parent / "data/reports"
        report_path.mkdir(exist_ok=True)

        suffix = "_coref" if use_coref else ""
        report_file = report_path / f"benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}{suffix}.md"
        with open(report_file, "w") as f:
            f.write(generate_markdown_report(report))
        print(f"\nReport saved to: {report_file}")

        # Также сохраняем как latest
        latest_file = report_path / f"benchmark_latest{suffix}.md"
        with open(latest_file, "w") as f:
            f.write(generate_markdown_report(report))
        print(f"Latest report:   {latest_file}")
