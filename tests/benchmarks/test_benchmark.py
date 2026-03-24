"""
Бенчмарк для оценки качества извлечения триплетов.

Запуск:
    pytest tests/benchmarks/test_benchmark.py -v -s

Или как скрипт:
    python -m tests.benchmarks.test_benchmark
"""

from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from regulation2graph.core import RuleBasedExtractor


@dataclass
class TestCase:
    """Тестовый пример для бенчмарка."""

    text: str
    category: str  # Simple, Medium, Hard
    expected_actor: str
    expected_action: str
    expected_object: str


# Тестовые данные
TEST_DATA = [
    # SIMPLE - простые предложения
    TestCase("Менеджер создает заявку.", "Simple", "менеджер", "создавать", "заявка"),
    TestCase("Клиент оплачивает счет.", "Simple", "клиент", "оплачивать", "счет"),
    TestCase(
        "Система отправляет уведомление.",
        "Simple",
        "система",
        "отправлять",
        "уведомление",
    ),
    TestCase(
        "Директор подписывает приказ.", "Simple", "директор", "подписывать", "приказ"
    ),
    TestCase(
        "Сотрудник архивирует документ.",
        "Simple",
        "сотрудник",
        "архивировать",
        "документ",
    ),
    # MEDIUM - с условиями
    TestCase(
        "Если документ согласован, секретарь печатает договор.",
        "Medium",
        "секретарь",
        "печатать",
        "договор",
    ),
    TestCase(
        "В случае ошибки оператор отменяет транзакцию.",
        "Medium",
        "оператор",
        "отменять",
        "транзакция",
    ),
    TestCase(
        "Когда товар готов, курьер забирает посылку.",
        "Medium",
        "курьер",
        "забирать",
        "посылка",
    ),
    TestCase(
        "При условии оплаты банк выдает кредит.",
        "Medium",
        "банк",
        "выдавать",
        "кредит",
    ),
    TestCase(
        "Если данные корректны, система сохраняет отчет.",
        "Medium",
        "система",
        "сохранять",
        "отчет",
    ),
    # HARD - пассивный залог, безличные конструкции (ожидаем провалы)
    TestCase(
        "Заявка подписывается директором.",
        "Hard",
        "директор",
        "подписывать",
        "заявка",
    ),
    TestCase(
        "Необходимо согласовать бюджет.",
        "Hard",
        "Unknown",
        "согласовать",
        "бюджет",
    ),
    TestCase(
        "Документ отправлен на визирование.",
        "Hard",
        "Unknown",
        "отправлять",
        "документ",
    ),
    TestCase(
        "После проверки отчета он передается в архив.",
        "Hard",
        "Unknown",
        "передаваться",
        "отчет",
    ),
    TestCase(
        "Оплата производится клиентом.",
        "Hard",
        "клиент",
        "производить",
        "оплата",
    ),
]


def run_benchmark(verbose: bool = True) -> pd.DataFrame:
    """
    Запускает бенчмарк и возвращает результаты.

    Args:
        verbose: Выводить ли подробную информацию.

    Returns:
        DataFrame с результатами.
    """
    extractor = RuleBasedExtractor()
    results = []

    if verbose:
        print(f"\n{'CATEGORY':<10} | {'STATUS':<6} | {'TEXT'}")
        print("-" * 70)

    for case in TEST_DATA:
        triplets = extractor.parse_text(case.text)
        is_success = False

        if triplets:
            t = triplets[0]

            # Проверяем совпадение (с учётом леммы)
            actor_match = t.actor.lower() == case.expected_actor.lower()
            action_match = case.expected_action.lower() in t.action.lower()
            obj_match = case.expected_object.lower() in t.obj.lower()

            if actor_match and action_match and obj_match:
                is_success = True

            # Для Hard-кейсов с Unknown
            if case.category == "Hard" and case.expected_actor == "Unknown":
                if t.actor == "Unknown" and action_match and obj_match:
                    is_success = True

        status = "OK" if is_success else "FAIL"
        if verbose:
            print(f"{case.category:<10} | {status:<6} | {case.text}")

        results.append({"category": case.category, "success": 1 if is_success else 0})

    return pd.DataFrame(results)


CATEGORY_LABELS = {
    "Simple": "Simple\n(Актор + Действие + Объект)",
    "Medium": "Medium\n(+ Условия: если, когда...)",
    "Hard": "Hard\n(Пассивный залог,\nбезличные конструкции)",
}


def plot_results(df: pd.DataFrame, output_path: str | None = None) -> None:
    """
    Строит график результатов бенчмарка.

    Args:
        df: DataFrame с результатами.
        output_path: Путь для сохранения графика.
    """
    # Группируем по категориям
    stats = df.groupby("category")["success"].mean() * 100
    stats = stats.reindex(["Simple", "Medium", "Hard"])

    # Рисуем график
    fig, ax = plt.subplots(figsize=(10, 6))
    colors = ["#4CAF50", "#FFC107", "#F44336"]  # Зелёный, Жёлтый, Красный

    labels = [CATEGORY_LABELS[cat] for cat in stats.index]
    bars = ax.bar(labels, stats.values, color=colors)

    # Подписи процентов
    for bar in bars:
        yval = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            yval + 2,
            f"{int(yval)}%",
            ha="center",
            fontweight="bold",
            fontsize=12,
        )

    ax.set_title(
        "Точность Rule-Based алгоритма по категориям сложности",
        fontsize=14,
        fontweight="bold",
    )
    ax.set_ylabel("Accuracy (%)", fontsize=11)
    ax.set_ylim(0, 115)
    ax.grid(axis="y", linestyle="--", alpha=0.7)

    plt.tight_layout()

    if output_path is None:
        output_path = "benchmark_results.png"

    plt.savefig(output_path, dpi=150)
    print(f"\n[INFO] График сохранён: {output_path}")
    plt.close()


# Pytest тесты
def test_benchmark_simple_category() -> None:
    """Simple категория должна иметь высокую точность."""
    df = run_benchmark(verbose=False)
    simple_accuracy = df[df["category"] == "Simple"]["success"].mean()
    assert simple_accuracy >= 0.8, f"Simple accuracy too low: {simple_accuracy}"


def test_benchmark_medium_category() -> None:
    """Medium категория должна иметь приемлемую точность."""
    df = run_benchmark(verbose=False)
    medium_accuracy = df[df["category"] == "Medium"]["success"].mean()
    assert medium_accuracy >= 0.4, f"Medium accuracy too low: {medium_accuracy}"


# Запуск как скрипт
if __name__ == "__main__":
    print("=" * 70)
    print("Regulation2Graph - Benchmark")
    print("=" * 70)

    df_results = run_benchmark(verbose=True)

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    for cat in ["Simple", "Medium", "Hard"]:
        acc = df_results[df_results["category"] == cat]["success"].mean() * 100
        print(f"  {cat:<10}: {acc:.0f}%")

    plot_results(df_results)
