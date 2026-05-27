# План миграции на Workflow Net

## Обзор

Переход от текущей модели (Triplet + Gateway) к формальной модели Workflow Net.

**Ключевые изменения:**
1. Добавление `Place` (состояния между действиями)
2. Переименование `Triplet` → `Transition`
3. Исправление порядка: условие (Place) → действие (Transition)
4. Унификация схемы Neo4j
5. **Удаление visualizer** — визуализация через Neo4j Browser

---

## Фаза 1: Новые модели данных

### 1.1. Создать `regulation2graph/models/workflow.py`

```python
# Новые модели для Workflow Net
class PlaceType(Enum)       # START, END, INTERMEDIATE
class TransitionType(Enum)  # ACTIVITY, SILENT
class Place(dataclass)      # id, name, place_type
class Transition(dataclass) # id, actor, action, obj, guard
class Arc(dataclass)        # source_id, target_id, label
class WorkflowNet(dataclass) # places, transitions, arcs
```

**Файлы:**
- [ ] `regulation2graph/models/workflow.py` — новый файл
- [ ] `regulation2graph/models/__init__.py` — добавить экспорты

### 1.2. Сохранить обратную совместимость

`Triplet` остаётся как алиас или deprecated wrapper для `Transition`.

```python
# В triplet.py добавить:
Triplet = Transition  # Deprecated alias
```

---

## Фаза 2: Рефакторинг Extractor

### 2.1. Изменить выход `RuleBasedExtractor`

**Было:** `list[Triplet]`
**Стало:** `WorkflowNet` (или `tuple[list[Place], list[Transition], list[Arc]]`)

### 2.2. Логика построения

```python
def parse_text(self, text: str) -> WorkflowNet:
    places = [Place("p_start", "Начало", PlaceType.START)]
    transitions = []
    arcs = []

    for i, sent in enumerate(sentences):
        triplet = self._extract_from_sentence(sent)

        # Создаём Transition
        t = Transition(f"t{i}", triplet.actor, triplet.action, triplet.obj, triplet.condition_text)
        transitions.append(t)

        # Создаём промежуточный Place
        p = Place(f"p{i+1}", f"После: {triplet.action}", PlaceType.INTERMEDIATE)
        places.append(p)

        # Создаём Arc'и
        arcs.append(Arc(places[-2].id, t.id))  # Place → Transition
        arcs.append(Arc(t.id, p.id))           # Transition → Place

    places.append(Place("p_end", "Конец", PlaceType.END))
    return WorkflowNet(places, transitions, arcs)
```

**Файлы:**
- [ ] `regulation2graph/core/extractor.py` — изменить `parse_text()`
- [ ] Учесть условия: guard на Transition, а не отдельный Gateway

### 2.3. Обработка условий (XOR-split)

```
Текст: "Если документ согласован, менеджер подписывает. Иначе секретарь возвращает."

Результат:
Places:  [p_start] → [p1: решение] → [p2: после подписания] → [p_end]
                                   ↘ [p3: после возврата] ↗

Transitions: [t1: подписать (guard="согласован")]
             [t2: вернуть (guard="НЕ согласован")]

Arcs: p_start → ... → p1 → t1 → p2 → ... → p_end
                     p1 → t2 → p3 → ... → p_end
```

---

## Фаза 3: Удаление Visualizer

### 3.1. Обоснование

Neo4j Browser предоставляет:
- Интерактивную визуализацию графа
- Cypher-запросы для фильтрации и анализа
- Drag-and-drop редактирование
- Экспорт в PNG/SVG при необходимости

Отдельный matplotlib-визуализатор становится избыточным.

### 3.2. Что удалить

**Файлы:**
- [ ] `regulation2graph/graph/visualizer.py` — **УДАЛИТЬ**
- [ ] `regulation2graph/services/visualization_service.py` — **УДАЛИТЬ**
- [ ] `tests/test_visualizer.py` — **УДАЛИТЬ**
- [ ] Убрать импорты и вызовы из `main.py`

### 3.3. Альтернатива (опционально)

Если понадобится статический экспорт для статей:
- pm4py умеет визуализировать Petri Nets
- Neo4j Browser → Export as PNG

---

## Фаза 4: Рефакторинг Neo4j

### 4.1. Новая схема данных

```cypher
// Удалить Gateway, добавить Place
(:Place {id, name, type})
(:Transition {id, actor, action, object, guard})

// Единый тип связи
(:Place)-[:FLOW]->(:Transition)
(:Transition)-[:FLOW]->(:Place)

// Guard хранится на Transition, не на связи
```

### 4.2. Упрощение кода

Текущий `Neo4jLoader.save_process()` слишком сложный из-за Gateway.
После рефакторинга:

```python
def save_workflow(self, workflow: WorkflowNet) -> None:
    # 1. Создать все Places
    for place in workflow.places:
        session.run("CREATE (:Place {id: $id, name: $name, type: $type})", ...)

    # 2. Создать все Transitions
    for t in workflow.transitions:
        session.run("CREATE (:Transition {...})", ...)

    # 3. Создать все Arcs
    for arc in workflow.arcs:
        session.run("""
            MATCH (a {id: $source}), (b {id: $target})
            CREATE (a)-[:FLOW {label: $label}]->(b)
        """, ...)
```

**Файлы:**
- [ ] `regulation2graph/graph/neo4j.py` — переписать `save_process()` → `save_workflow()`

---

## Фаза 5: Обновление тестов

### 5.1. Новые тесты для моделей

```python
# tests/test_workflow_models.py
def test_place_creation()
def test_transition_creation()
def test_workflow_net_validation()
```

### 5.2. Обновление тестов extractor

```python
# tests/test_extractor.py
def test_parse_returns_workflow_net()
def test_condition_creates_guard_not_gateway()
def test_alternative_creates_xor_split()
```

### 5.3. Тесты Neo4j

```python
# tests/test_neo4j.py
def test_save_workflow_creates_places()
def test_save_workflow_creates_transitions()
def test_flow_edges_correct()
```

**Файлы:**
- [ ] `tests/test_workflow_models.py` — новый файл
- [ ] `tests/test_extractor.py` — обновить
- [ ] `tests/test_neo4j.py` — новый файл (интеграционные тесты)
- [ ] `tests/benchmarks/test_benchmark.py` — адаптировать
- [ ] `tests/test_visualizer.py` — **УДАЛИТЬ**

---

## Фаза 6: Сервисы и Main

### 6.1. Обновить сервисы

```python
# extraction_service.py
def extract(text: str) -> WorkflowNet

# neo4j_service.py
def save(workflow: WorkflowNet)
def clear()
```

### 6.2. Обновить main.py

```python
def main():
    text = load_text()
    workflow = extraction_service.extract(text)
    neo4j_service.save(workflow)
    print("Откройте Neo4j Browser для визуализации: http://localhost:7474")
```

**Файлы:**
- [ ] `regulation2graph/services/extraction_service.py` — обновить
- [ ] `regulation2graph/services/neo4j_service.py` — обновить
- [ ] `regulation2graph/services/visualization_service.py` — **УДАЛИТЬ**
- [ ] `regulation2graph/main.py` — упростить

---

## Фаза 7 (опционально): Абстракция NLP Provider

### 7.1. Цель

Подготовить архитектуру для лёгкой миграции с Natasha на DeepPavlov (или другие библиотеки).

### 7.2. Интерфейс

```python
# regulation2graph/nlp/provider.py
from typing import Protocol

class NLPProvider(Protocol):
    """Абстракция над NLP-библиотекой."""
    def parse(self, text: str) -> list[ParsedSentence]: ...

@dataclass
class ParsedSentence:
    text: str
    tokens: list[ParsedToken]

@dataclass
class ParsedToken:
    text: str
    lemma: str
    pos: str           # часть речи
    rel: str           # dependency relation (nsubj, obj, root, advcl)
    head_idx: int      # индекс головы в списке токенов
```

### 7.3. Реализации

```python
# regulation2graph/nlp/natasha_provider.py
class NatashaProvider(NLPProvider):
    def parse(self, text: str) -> list[ParsedSentence]:
        doc = Doc(text)
        doc.segment(self._segmenter)
        doc.tag_morph(self._morph_tagger)
        doc.parse_syntax(self._syntax_parser)
        return self._convert(doc)

# regulation2graph/nlp/deeppavlov_provider.py (будущее)
class DeepPavlovProvider(NLPProvider):
    def parse(self, text: str) -> list[ParsedSentence]:
        # DeepPavlov API
        result = self._model([text])
        return self._convert(result)
```

### 7.4. Использование в Extractor

```python
class RuleBasedExtractor:
    def __init__(self, provider: NLPProvider = None):
        self._provider = provider or NatashaProvider()

    def parse_text(self, text: str) -> WorkflowNet:
        sentences = self._provider.parse(text)
        # ... остальная логика
```

### 7.5. Миграция на DeepPavlov

```python
# Одна строка меняется:
extractor = RuleBasedExtractor(provider=DeepPavlovProvider())
```

**Файлы:**
- [ ] `regulation2graph/nlp/__init__.py`
- [ ] `regulation2graph/nlp/provider.py` — интерфейс и dataclasses
- [ ] `regulation2graph/nlp/natasha_provider.py` — текущая реализация
- [ ] `regulation2graph/nlp/deeppavlov_provider.py` — будущая реализация

---

## Фаза 8 (опционально): Интеграция pm4py

### 8.1. Экспорт в PNML

```python
# regulation2graph/export/pnml.py
def to_pnml(workflow: WorkflowNet) -> str
```

### 7.2. Верификация soundness

```python
import pm4py
from pm4py.objects.petri_net.utils import check_soundness

def verify_workflow(workflow: WorkflowNet) -> bool:
    pn = convert_to_pm4py(workflow)
    return check_soundness.check_wfnet(pn)
```

---

## Порядок выполнения

```
Фаза 1 (модели)
    ↓
Фаза 2 (extractor) ←── Фаза 5.1-5.2 (тесты моделей и extractor)
    ↓
Фаза 3 (удаление visualizer)
    ↓
Фаза 4 (neo4j) ←── Фаза 5.3 (тесты neo4j)
    ↓
Фаза 6 (сервисы + main)
    ↓
Фаза 7 (pm4py) — опционально
```

---

## Оценка объёма работ

| Фаза | Действие | Сложность |
|------|----------|-----------|
| 1. Модели | +2 файла | Низкая |
| 2. Extractor | Изменить 1 файл | Средняя |
| 3. Visualizer | **−3 файла** | Низкая (удаление) |
| 4. Neo4j | Изменить 1 файл | Средняя |
| 5. Тесты | +2, изменить 2, −1 | Средняя |
| 6. Сервисы | Изменить 2, −1 | Низкая |
| 7. pm4py | +2 файла | Низкая |

**Итого:** Код станет **проще** (−4 файла, удаление visualizer).

---

## Критерии завершения

- [ ] Все тесты проходят
- [ ] `WorkflowNet` содержит Places между Transitions
- [ ] Условия — это guards на Transitions, не отдельные узлы
- [ ] Neo4j содержит корректную структуру `(:Place)-[:FLOW]->(:Transition)`
- [ ] Neo4j Browser корректно отображает граф процесса
- [ ] Бенчмарк работает на новой модели
