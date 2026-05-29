# BERT-based Sentence Classification with Metadata Extraction

## Обзор

Данный документ описывает подход к использованию BERT-моделей для классификации предложений регламентов с извлечением структурированных метаданных. Подход комбинирует sequence classification с targeted extraction.

## Мотивация

Текущий rule-based экстрактор имеет ограничения:
- Жёсткая зависимость от синтаксических паттернов
- Сложность обработки неоднозначных конструкций
- Необходимость ручного создания правил для каждого нового паттерна

BERT-подход позволит:
- Обучить модель на размеченных примерах
- Автоматически обобщать паттерны
- Обрабатывать вариативность естественного языка

## Архитектура

### Уровень 1: Классификация типа предложения

Первый уровень определяет тип предложения:

| Класс | Описание | Пример |
|-------|----------|--------|
| `simple_action` | Простое действие без условий | "Менеджер проверяет заявку." |
| `conditional_sentence` | Предложение с условием | "Если документ согласован, менеджер подписывает." |
| `alternative_sentence` | Альтернативная ветка | "Иначе секретарь возвращает документ." |
| `compound_action` | Несколько действий | "Менеджер проверяет и подписывает." |
| `passive_sentence` | Пассивный залог | "Заявка подписывается директором." |
| `loop_sentence` | Цикл/повторение | "Пока не согласовано, вносятся правки." |

### Уровень 2: Извлечение метаданных

После классификации, вторая модель (или head) извлекает структурированные поля в зависимости от типа:

#### Для `simple_action`:
```json
{
  "type": "simple_action",
  "actor": "менеджер",
  "action": "проверять",
  "object": "заявка"
}
```

#### Для `conditional_sentence`:
```json
{
  "type": "conditional_sentence",
  "condition": "документ согласован",
  "if_true": {
    "actor": "менеджер",
    "action": "подписывать",
    "object": "договор"
  },
  "if_false": null
}
```

#### Для `alternative_sentence`:
```json
{
  "type": "alternative_sentence",
  "actor": "секретарь",
  "action": "возвращать",
  "object": "документ",
  "linked_condition": "prev_condition_id"
}
```

## Пример полного разбора

**Входной текст:**
```
При выполнении квартального плана, бухгалтер выплачивает премию всем сотрудникам отдела.
```

**Шаг 1: Классификация** → `conditional_sentence`

**Шаг 2: Извлечение метаданных:**
```json
{
  "type": "conditional_sentence",
  "condition": "выполнение квартального плана",
  "if_true": {
    "actor": "бухгалтер",
    "action": "выплачивать",
    "object": "премия",
    "recipient": "сотрудники отдела"
  },
  "if_false": null
}
```

## Варианты реализации

### Вариант A: Multi-task Learning

Одна BERT-модель с несколькими головами:
- Classification head → тип предложения
- Extraction head → BIO-разметка для извлечения сущностей
- Relation head → связи между сущностями

**Плюсы:** Единая модель, shared representations
**Минусы:** Сложность обучения, балансировка задач

### Вариант B: Pipeline подход

Последовательность специализированных моделей:
1. Classifier BERT → тип предложения
2. NER BERT → извлечение сущностей (Actor, Action, Object, Condition)
3. Rule-based → построение структуры на основе типа и сущностей

**Плюсы:** Модульность, проще отлаживать
**Минусы:** Error propagation, latency

### Вариант C: Seq2Seq (Generative)

BERT-encoder + decoder, генерирующий JSON:

```
Input:  "Если документ согласован, менеджер подписывает договор."
Output: {"type": "conditional", "condition": "документ согласован", ...}
```

**Плюсы:** Гибкость формата, end-to-end
**Минусы:** Сложнее контролировать выход, требует больше данных

## Формат разметки для обучения

### Расширенный JSONL формат:

```jsonl
{
  "id": "train_001",
  "text": "При выполнении квартального плана, бухгалтер выплачивает премию.",
  "sentence_type": "conditional_sentence",
  "metadata": {
    "condition": {
      "text": "выполнение квартального плана",
      "span": [4, 32]
    },
    "if_true": {
      "actor": {"text": "бухгалтер", "span": [34, 43]},
      "action": {"text": "выплачивает", "span": [44, 55]},
      "object": {"text": "премия", "span": [56, 62]}
    },
    "if_false": null
  }
}
```

### BIO-разметка для NER:

```
При        O
выполнении B-CONDITION
квартального I-CONDITION
плана      I-CONDITION
,          O
бухгалтер  B-ACTOR
выплачивает B-ACTION
премию     B-OBJECT
.          O
```

## Выбор базовой модели

### Рекомендуемые модели для русского языка:

| Модель | Размер | Плюсы | Минусы |
|--------|--------|-------|--------|
| `DeepPavlov/rubert-base-cased` | 180M | Проверенная, хорошие результаты | Устарела |
| `sberbank-ai/ruBert-base` | 180M | Оптимизирована под русский | Требует дообучения |
| `ai-forever/ruBert-large` | 350M | Высокое качество | Медленнее, требует GPU |
| `ai-forever/ruRoBERTa-large` | 350M | Современная архитектура | Больше памяти |
| `IlyaGusev/rured_conversational_sentence_bert` | 180M | Обучена на диалогах | Может не подойти для формальных текстов |

**Рекомендация:** Начать с `sberbank-ai/ruBert-base`, при необходимости перейти на `ruRoBERTa-large`.

## План реализации

### Этап 1: Подготовка данных
1. Расширить текущий датасет до 100+ примеров
2. Добавить поле `sentence_type` к существующим примерам
3. Добавить span-разметку для сущностей
4. Разделить на train/val/test (70/15/15)

### Этап 2: Classifier
1. Fine-tune BERT для sentence classification
2. Метрика: Accuracy, Macro-F1
3. Целевое качество: F1 > 0.9 на тестовой выборке

### Этап 3: NER Extractor
1. Fine-tune BERT для token classification (BIO)
2. Теги: ACTOR, ACTION, OBJECT, CONDITION, RECIPIENT
3. Метрика: Entity-level F1
4. Целевое качество: F1 > 0.85

### Этап 4: Интеграция
1. Создать `BertBasedExtractor` класс
2. Реализовать Protocol для совместимости с существующим API
3. A/B сравнение с `RuleBasedExtractor`
4. Гибридный режим: BERT + fallback на rules

## Сравнение с текущим подходом

| Аспект | Rule-based | BERT-based |
|--------|------------|------------|
| Качество на простых | Отлично | Отлично |
| Качество на сложных | Среднее | Высокое (ожидается) |
| Скорость inference | Быстро (~10ms) | Медленнее (~100ms) |
| Требования к ресурсам | CPU | GPU рекомендуется |
| Расширяемость | Ручная | Через данные |
| Интерпретируемость | Высокая | Средняя |

## Открытые вопросы

1. **Достаточно ли данных?**
   - Минимум 100 примеров для classifier
   - Минимум 500 для NER с хорошим качеством
   - Возможно, потребуется data augmentation

2. **Как обрабатывать редкие типы?**
   - `loop_sentence` может иметь мало примеров
   - Возможно, объединить с `conditional_sentence`

3. **Как связывать предложения?**
   - `alternative_sentence` должна ссылаться на предыдущее условие
   - Нужен механизм cross-sentence references

4. **Гибридный подход vs. полный BERT?**
   - Гибрид: BERT для классификации + rules для extraction
   - Полный BERT: требует больше данных, но более гибкий

## Ресурсы

- Hugging Face Transformers: https://huggingface.co/docs/transformers/
- RuBERT models: https://huggingface.co/sberbank-ai
- Token Classification Guide: https://huggingface.co/docs/transformers/tasks/token_classification
- Sequence Classification: https://huggingface.co/docs/transformers/tasks/sequence_classification
