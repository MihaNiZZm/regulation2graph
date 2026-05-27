"""
Rule-based извлечение Workflow Net из текста.

Извлекает действия (Transitions) из текста и строит
полную модель Workflow Net с Places и Arcs.
"""

from natasha import (
    Doc,
    MorphVocab,
    NewsEmbedding,
    NewsMorphTagger,
    NewsSyntaxParser,
    Segmenter,
)

from regulation2graph.config import get_settings
from regulation2graph.models import (
    Arc,
    Place,
    PlaceType,
    Transition,
    WorkflowNet,
)
# Legacy import для обратной совместимости
from regulation2graph.models import GatewayType, Triplet


class RuleBasedExtractor:
    """
    Извлекает Workflow Net из текста на русском языке.

    Использует библиотеку Natasha для:
    - Сегментации текста на предложения
    - Морфологического анализа
    - Синтаксического разбора

    Example:
        >>> extractor = RuleBasedExtractor()
        >>> workflow = extractor.extract("Менеджер проверяет заявку.")
        >>> print(workflow.transitions[0].actor)
        'менеджер'
    """

    def __init__(self) -> None:
        """Инициализация NLP-моделей (тяжёлая операция, делается один раз)."""
        self._settings = get_settings()

        # Natasha components
        self._embedding = NewsEmbedding()
        self._segmenter = Segmenter()
        self._morph_vocab = MorphVocab()
        self._morph_tagger = NewsMorphTagger(self._embedding)
        self._syntax_parser = NewsSyntaxParser(self._embedding)

    def extract(self, text: str) -> WorkflowNet:
        """
        Извлекает Workflow Net из текста.

        Args:
            text: Текст регламента на русском языке.

        Returns:
            WorkflowNet с Places, Transitions и Arcs.
        """
        # Извлекаем сырые данные о действиях
        raw_actions = self._extract_raw_actions(text)

        # Строим Workflow Net
        return self._build_workflow_net(raw_actions)

    def parse_text(self, text: str) -> list[Triplet]:
        """
        DEPRECATED: Используйте extract() вместо этого метода.

        Оставлен для обратной совместимости.
        """
        workflow = self.extract(text)
        # Конвертируем Transitions обратно в Triplets для совместимости
        return [
            Triplet(
                actor=t.actor,
                action=t.action,
                obj=t.obj,
                condition_text=t.guard,
                is_alternative=getattr(t, '_is_alternative', False),
                full_text=t.full_text,
                gateway_type=GatewayType.EXCLUSIVE if t.has_guard else None,
            )
            for t in workflow.transitions
        ]

    def _extract_raw_actions(self, text: str) -> list[dict]:
        """
        Извлекает сырые данные о действиях из текста.

        Returns:
            Список словарей с данными о действиях.
        """
        doc = Doc(text)
        doc.segment(self._segmenter)
        doc.tag_morph(self._morph_tagger)
        doc.parse_syntax(self._syntax_parser)

        results = []

        for sent in doc.sents:
            for token in sent.tokens:
                token.lemmatize(self._morph_vocab)

            action_data = self._extract_action_from_sentence(sent)
            if action_data:
                results.append(action_data)

        return results

    def _extract_action_from_sentence(self, sent) -> dict | None:
        """
        Извлекает данные о действии из одного предложения.

        Args:
            sent: Предложение из Natasha Doc.

        Returns:
            Словарь с данными о действии или None.
        """
        nlp_settings = self._settings.nlp

        # 1. Ищем Root (главный глагол = Действие)
        roots = [t for t in sent.tokens if t.rel == "root"]
        if not roots:
            return None
        action_token = roots[0]

        # 2. Ищем Актора (субъект)
        actor = "Unknown"
        for token in sent.tokens:
            if token.head_id == action_token.id and token.rel in nlp_settings.subject_relations:
                actor = token.lemma
                break

        # 3. Ищем Объект
        obj = "-"
        for token in sent.tokens:
            if token.head_id == action_token.id and token.rel in nlp_settings.object_relations:
                obj = token.lemma
                break

        # 4. Извлекаем условие (guard для Transition)
        guard = self._extract_condition(sent, action_token)

        # 5. Проверяем маркер альтернативы
        is_alternative = self._is_alternative_branch(sent)

        return {
            "actor": actor,
            "action": action_token.lemma,
            "obj": obj,
            "guard": guard,
            "is_alternative": is_alternative,
            "full_text": sent.text.strip(),
        }

    def _build_workflow_net(self, raw_actions: list[dict]) -> WorkflowNet:
        """
        Строит WorkflowNet из списка сырых действий.

        Логика:
        1. Создаём начальный Place
        2. Для каждого действия создаём Transition и промежуточный Place
        3. Обрабатываем условия (XOR-split) и альтернативы
        4. Создаём конечный Place
        5. Соединяем всё Arcs

        Args:
            raw_actions: Список словарей с данными о действиях.

        Returns:
            Построенный WorkflowNet.
        """
        if not raw_actions:
            return WorkflowNet(
                places=[
                    Place("p_start", "Начало", PlaceType.START),
                    Place("p_end", "Конец", PlaceType.END),
                ],
                transitions=[],
                arcs=[],
            )

        places: list[Place] = []
        transitions: list[Transition] = []
        arcs: list[Arc] = []

        # Начальный Place
        p_start = Place("p_start", "Начало", PlaceType.START)
        places.append(p_start)

        # Отслеживаем текущее место для построения цепочки
        current_place_id = p_start.id

        # Отслеживаем условие, ожидающее альтернативу
        pending_condition: dict | None = None
        pending_condition_place_id: str | None = None

        for i, action_data in enumerate(raw_actions):
            t_id = f"t{i}"
            is_alternative = action_data["is_alternative"]
            has_guard = action_data["guard"] is not None

            # Создаём Transition
            transition = Transition(
                id=t_id,
                actor=action_data["actor"],
                action=action_data["action"],
                obj=action_data["obj"],
                guard=action_data["guard"],
                full_text=action_data["full_text"],
            )
            # Сохраняем флаг альтернативы для обратной совместимости
            object.__setattr__(transition, '_is_alternative', is_alternative)
            transitions.append(transition)

            # Создаём Place после этого действия
            p_after = Place(
                f"p{i + 1}",
                f"После: {action_data['action']}",
                PlaceType.INTERMEDIATE,
            )
            places.append(p_after)

            if is_alternative and pending_condition_place_id:
                # Это альтернативная ветка — подключаем к месту условия
                arcs.append(Arc(pending_condition_place_id, t_id, label="Нет"))
                arcs.append(Arc(t_id, p_after.id))

                # Альтернатива сливается с основным потоком
                # (следующее действие будет подключено к p_after)
                current_place_id = p_after.id
                pending_condition = None
                pending_condition_place_id = None

            elif has_guard:
                # Действие с условием — это XOR-split
                # Сначала подключаем к текущему месту
                arcs.append(Arc(current_place_id, t_id, label="Да"))
                arcs.append(Arc(t_id, p_after.id))

                # Запоминаем место для альтернативы
                pending_condition = action_data
                pending_condition_place_id = current_place_id

                # Двигаемся дальше по основной ветке
                current_place_id = p_after.id

            else:
                # Обычное действие — линейная связь
                arcs.append(Arc(current_place_id, t_id))
                arcs.append(Arc(t_id, p_after.id))
                current_place_id = p_after.id

        # Конечный Place
        p_end = Place("p_end", "Конец", PlaceType.END)
        places.append(p_end)

        # Подключаем последнее место к концу
        arcs.append(Arc(current_place_id, p_end.id))

        # Если осталось незакрытое условие без альтернативы,
        # подключаем его напрямую к концу
        if pending_condition_place_id:
            arcs.append(Arc(pending_condition_place_id, p_end.id, label="Нет"))

        return WorkflowNet(places=places, transitions=transitions, arcs=arcs)

    def _extract_condition(self, sent, action_token) -> str | None:
        """
        Извлекает текст условия из предложения.

        Стратегия:
        1. Ищем advcl (adverbial clause) - подчинённое условное предложение
        2. Если нет, проверяем маркеры в начале предложения

        Args:
            sent: Предложение.
            action_token: Токен главного глагола.

        Returns:
            Текст условия или None.
        """
        nlp_settings = self._settings.nlp

        # Стратегия 1: Поиск через advcl
        for token in sent.tokens:
            if token.head_id == action_token.id and token.rel in nlp_settings.condition_relations:
                # Нашли условную часть, собираем её текст
                condition_tokens = self._collect_subtree(sent, token)
                if condition_tokens:
                    # Убираем маркер условия из текста (если, когда)
                    condition_text = " ".join(t.text for t in condition_tokens)
                    return self._clean_condition_text(condition_text)

        # Стратегия 2: Проверка маркеров в начале
        first_lemma = sent.tokens[0].lemma.lower()
        if first_lemma in nlp_settings.condition_markers:
            # Простой fallback - помечаем что условие есть
            return "CONDITION_DETECTED"

        # Стратегия 3: Проверка "в случае" (два слова)
        if len(sent.tokens) >= 2:
            two_words = f"{sent.tokens[0].text.lower()} {sent.tokens[1].text.lower()}"
            for marker in nlp_settings.condition_markers:
                if two_words.startswith(marker):
                    return "CONDITION_DETECTED"

        return None

    def _collect_subtree(self, sent, root_token) -> list:
        """
        Собирает все токены поддерева (все зависимые от root_token).

        Args:
            sent: Предложение.
            root_token: Корень поддерева.

        Returns:
            Список токенов в порядке их появления в тексте.
        """
        subtree_ids = {root_token.id}
        changed = True

        # Итеративно собираем все зависимые токены
        while changed:
            changed = False
            for token in sent.tokens:
                if token.head_id in subtree_ids and token.id not in subtree_ids:
                    subtree_ids.add(token.id)
                    changed = True

        # Возвращаем токены в порядке их появления
        return [t for t in sent.tokens if t.id in subtree_ids]

    def _clean_condition_text(self, text: str) -> str:
        """Очищает текст условия от маркеров и лишних символов."""
        nlp_settings = self._settings.nlp

        text = text.strip().rstrip(",").strip()

        # Убираем маркер условия в начале
        text_lower = text.lower()
        for marker in nlp_settings.condition_markers:
            if text_lower.startswith(marker):
                text = text[len(marker) :].strip()
                break

        return text

    def _is_alternative_branch(self, sent) -> bool:
        """Проверяет, начинается ли предложение с маркера альтернативы."""
        nlp_settings = self._settings.nlp

        first_lemma = sent.tokens[0].lemma.lower()
        if first_lemma in nlp_settings.alternative_markers:
            return True

        # Проверка двухсловных маркеров
        if len(sent.tokens) >= 3:
            three_words = (
                f"{sent.tokens[0].text.lower()} "
                f"{sent.tokens[1].text.lower()} "
                f"{sent.tokens[2].text.lower()}"
            )
            for marker in nlp_settings.alternative_markers:
                if three_words.startswith(marker):
                    return True

        return False
