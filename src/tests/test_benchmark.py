import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from src.core.extractor import RuleBasedExtractor

# --- НАСТРОЙКА ДАННЫХ ---

TEST_DATA = [
    # SIMPLE
    {"text": "Менеджер создает заявку.", "cat": "Simple", "exp_actor": "менеджер", "exp_action": "создавать"},
    {"text": "Клиент оплачивает счет.", "cat": "Simple", "exp_actor": "клиент", "exp_action": "оплачивать"},
    {"text": "Система отправляет уведомление.", "cat": "Simple", "exp_actor": "система", "exp_action": "отправлять"},
    {"text": "Директор подписывает приказ.", "cat": "Simple", "exp_actor": "директор", "exp_action": "подписывать"},
    {"text": "Сотрудник архивирует документ.", "cat": "Simple", "exp_actor": "сотрудник", "exp_action": "архивировать"},

    # MEDIUM (Conditions)
    {"text": "Если документ согласован, секретарь печатает договор.", "cat": "Medium", "exp_actor": "секретарь",
     "exp_action": "печатать"},
    {"text": "В случае ошибки оператор отменяет транзакцию.", "cat": "Medium", "exp_actor": "оператор",
     "exp_action": "отменять"},
    {"text": "Когда товар готов, курьер забирает посылку.", "cat": "Medium", "exp_actor": "курьер",
     "exp_action": "забирать"},
    {"text": "При условии оплаты банк выдает кредит.", "cat": "Medium", "exp_actor": "банк", "exp_action": "выдавать"},
    {"text": "Если данные корректны, система сохраняет отчет.", "cat": "Medium", "exp_actor": "система",
     "exp_action": "сохранять"},

    # HARD (Passive Voice / Complex) - тут ожидаем провал
    {"text": "Заявка подписывается директором.", "cat": "Hard", "exp_actor": "директор", "exp_action": "подписывать"},
    {"text": "Необходимо согласовать бюджет.", "cat": "Hard", "exp_actor": "Unknown", "exp_action": "согласовать"},
    # Наташа скорее всего не найдет актора
    {"text": "Документ отправлен на визирование.", "cat": "Hard", "exp_actor": "Unknown", "exp_action": "отправлять"},
    {"text": "После проверки отчета он передается в архив.", "cat": "Hard", "exp_actor": "отчет",
     "exp_action": "передаваться"},
    {"text": "Оплата производится клиентом.", "cat": "Hard", "exp_actor": "клиент", "exp_action": "производить"},
]


def run_benchmark():
    extractor = RuleBasedExtractor()
    results = []

    print(f"{'CATEGORY':<10} | {'STATUS':<10} | {'TEXT'}")
    print("-" * 60)

    for item in TEST_DATA:
        # Запускаем наш алгоритм
        extracted = extractor.parse_text(item["text"])

        # Логика оценки (Evaluation Logic)
        is_success = False

        if extracted:
            # Берем первый найденный триплет (упрощение для теста)
            ev = extracted[0]

            # Сравниваем Актора и Действие (леммы)
            # Приводим к нижнему регистру для надежности
            act_match = ev['actor'].lower() == item['exp_actor'].lower()
            action_match = item['exp_action'].lower() in ev[
                'action'].lower()  # contains, т.к. лемматизация может гулять

            if act_match and action_match:
                is_success = True

            # Для Хард-кейсов: если мы ждали Unknown и получили Unknown - это успех
            if item['cat'] == 'Hard' and item['exp_actor'] == 'Unknown' and ev['actor'] == 'Unknown':
                is_success = True

        status = "OK" if is_success else "FAIL"
        print(f"{item['cat']:<10} | {status:<10} | {item['text']}")

        results.append({
            "category": item["cat"],
            "success": 1 if is_success else 0
        })

    return pd.DataFrame(results)


def plot_results(df):
    # Группируем по категориям и считаем среднее (Accuracy)
    stats = df.groupby("category")["success"].mean() * 100
    # Сортируем порядок: Simple -> Medium -> Hard
    stats = stats.reindex(["Simple", "Medium", "Hard"])

    # Рисуем график
    plt.figure(figsize=(8, 5))
    colors = ['#4CAF50', '#FFC107', '#F44336']  # Зеленый, Желтый, Красный

    bars = plt.bar(stats.index, stats.values, color=colors)

    # Добавляем подписи процентов
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width() / 2, yval + 1, f"{int(yval)}%", ha='center', fontweight='bold')

    plt.title("Точность алгоритма (Rule-Based) по категориям сложности")
    plt.ylabel("Accuracy (%)")
    plt.ylim(0, 110)
    plt.grid(axis='y', linestyle='--', alpha=0.7)

    # Сохраняем в файл
    plt.savefig("benchmark_results.png")
    print("\n[INFO] График сохранен как benchmark_results.png")


if __name__ == "__main__":
    df_res = run_benchmark()
    plot_results(df_res)
