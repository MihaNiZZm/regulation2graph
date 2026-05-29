"""
Rule-based извлечение Workflow Net из текста.

Извлекает действия (Transitions) из текста и строит
полную модель Workflow Net с Places и Arcs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from natasha import (
    Doc,
    MorphVocab,
    NewsEmbedding,
    NewsMorphTagger,
    NewsSyntaxParser,
    Segmenter,
)

from regulation2graph.config import get_settings
from regulation2graph.core.morph_utils import generate_place_name
from regulation2graph.markers import (
    MarkerDetector,
    extract_alternative_marker,
    extract_condition_marker,
    strip_condition_marker,
)
from regulation2graph.models import (
    Arc,
    Place,
    PlaceType,
    Transition,
    WorkflowNet,
)
# Legacy import для обратной совместимости
from regulation2graph.models import GatewayType, Triplet

if TYPE_CHECKING:
    from regulation2graph.core.coreference import CoreferenceResolver


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

    def __init__(
        self,
        coreference_resolver: CoreferenceResolver | None = None,
    ) -> None:
        """
        Инициализация NLP-моделей.

        Args:
            coreference_resolver: Опциональный резолвер кореференции.
                Если указан, местоимения будут заменяться на антецеденты
                перед извлечением триплетов.

        Note:
            Инициализация NLP-моделей — тяжёлая операция,
            рекомендуется создавать экстрактор один раз.
        """
        self._settings = get_settings()

        # Natasha components
        self._embedding = NewsEmbedding()
        self._segmenter = Segmenter()
        self._morph_vocab = MorphVocab()
        self._morph_tagger = NewsMorphTagger(self._embedding)
        self._syntax_parser = NewsSyntaxParser(self._embedding)

        # Детектор маркеров (условия, альтернативы, циклы)
        self._marker_detector = MarkerDetector()

        # Опциональный резолвер кореференции
        self._coref_resolver = coreference_resolver

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

        Поддерживает многоосновные предложения — из одного предложения
        может быть извлечено несколько действий.

        Returns:
            Список словарей с данными о действиях.
        """
        # Шаг 0: Резолв кореференции (если резолвер настроен)
        if self._coref_resolver is not None:
            coref_result = self._coref_resolver.resolve(text)
            text = coref_result.resolved_text

        doc = Doc(text)
        doc.segment(self._segmenter)
        doc.tag_morph(self._morph_tagger)
        doc.parse_syntax(self._syntax_parser)

        results = []

        for sent in doc.sents:
            for token in sent.tokens:
                token.lemmatize(self._morph_vocab)

            # Извлекаем все действия из предложения (может быть несколько)
            actions = self._extract_actions_from_sentence(sent)
            results.extend(actions)

        return results

    def _extract_actions_from_sentence(self, sent) -> list[dict]:
        """
        Извлекает данные о действиях из одного предложения.

        Поддерживает многоосновные предложения:
        - "Менеджер проверяет заявку и директор подписывает договор" → 2 действия
        - "Менеджер проверяет и подписывает заявку" → 2 действия (общий субъект)

        Args:
            sent: Предложение из Natasha Doc.

        Returns:
            Список словарей с данными о действиях (может быть пустым).
        """
        nlp_settings = self._settings.nlp

        # 1. Собираем все глаголы-сказуемые:
        #    - root (может быть несколько — особенность парсера)
        #    - conj к любому root (сочинённые сказуемые)
        verb_tokens = []
        root_ids = set()

        # Сначала находим все root
        for token in sent.tokens:
            if token.rel == "root" and token.pos == "VERB":
                verb_tokens.append(token)
                root_ids.add(token.id)

        if not verb_tokens:
            return []

        # Затем находим все conj к любому из root
        for token in sent.tokens:
            if token.rel == "conj" and token.pos == "VERB":
                # conj может быть связан с любым root или с другим conj
                if token.head_id in root_ids or any(
                    t.id == token.head_id for t in verb_tokens
                ):
                    verb_tokens.append(token)

        # Первый root для наследования субъекта/объекта
        primary_root = verb_tokens[0]

        # 2. Проверяем маркер альтернативы (один раз для всего предложения)
        is_alternative = self._is_alternative_branch(sent)

        # 3. Для каждого глагола извлекаем триплет
        results = []
        for i, verb_token in enumerate(verb_tokens):
            # Ищем субъект для этого глагола
            actor = self._find_actor_for_verb(sent, verb_token, primary_root, nlp_settings)

            # Ищем объект для этого глагола (передаём все глаголы для наследования)
            obj = self._find_object_for_verb(
                sent, verb_token, primary_root, nlp_settings, all_verbs=verb_tokens
            )

            # Извлекаем условие (только для первого глагола)
            guard = None
            if i == 0:
                guard = self._extract_condition(sent, verb_token)

            # Альтернатива применяется только к первому действию
            action_is_alternative = is_alternative if i == 0 else False

            results.append({
                "actor": actor,
                "action": verb_token.lemma,
                "obj": obj,
                "guard": guard,
                "is_alternative": action_is_alternative,
                "full_text": sent.text.strip(),
            })

        return results

    def _find_actor_for_verb(self, sent, verb_token, root_token, nlp_settings) -> str:
        """
        Находит актора для конкретного глагола.

        Стратегия:
        1. Ищем прямой nsubj у этого глагола
        2. Если не найден и глагол != root, наследуем от root
        3. Собираем составные субъекты через conj (А и Б)

        Args:
            sent: Предложение.
            verb_token: Глагол, для которого ищем актора.
            root_token: Корневой глагол предложения.
            nlp_settings: Настройки NLP.

        Returns:
            Имя актора или "Unknown".
        """
        # Ищем прямой субъект
        actor_token = None
        for token in sent.tokens:
            if token.head_id == verb_token.id and token.rel in nlp_settings.subject_relations:
                actor_token = token
                break

        # Если не нашли и это не root — наследуем от root
        if actor_token is None and verb_token != root_token:
            for token in sent.tokens:
                if token.head_id == root_token.id and token.rel in nlp_settings.subject_relations:
                    actor_token = token
                    break

        if actor_token is None:
            return "Unknown"

        # Собираем составной субъект (А и Б)
        actor_parts = [actor_token.lemma]
        for token in sent.tokens:
            if token.head_id == actor_token.id and token.rel == "conj":
                actor_parts.append(token.lemma)

        return " и ".join(actor_parts)

    def _find_object_for_verb(
        self, sent, verb_token, root_token, nlp_settings, all_verbs: list | None = None
    ) -> str:
        """
        Находит объект для конкретного глагола.

        Стратегия:
        1. Ищем прямой obj/obl у этого глагола
        2. Если не найден — наследуем от root
        3. Если не найден — наследуем от других сочинённых глаголов (conj)

        Args:
            sent: Предложение.
            verb_token: Глагол, для которого ищем объект.
            root_token: Корневой глагол предложения.
            nlp_settings: Настройки NLP.
            all_verbs: Все глаголы предложения (для наследования от conj).

        Returns:
            Имя объекта или "-".
        """
        # Ищем прямой объект
        for token in sent.tokens:
            if token.head_id == verb_token.id and token.rel in nlp_settings.object_relations:
                return token.lemma

        # Если не нашли и это не root — наследуем от root
        if verb_token != root_token:
            for token in sent.tokens:
                if token.head_id == root_token.id and token.rel in nlp_settings.object_relations:
                    return token.lemma

        # Если это root и не нашли — пробуем наследовать от conj
        if verb_token == root_token and all_verbs:
            for other_verb in all_verbs:
                if other_verb != verb_token:
                    for token in sent.tokens:
                        if token.head_id == other_verb.id and token.rel in nlp_settings.object_relations:
                            return token.lemma

        return "-"

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
        # Place после положительной ветки (для продолжения основного потока)
        positive_branch_place_id: str | None = None
        # Place после альтернативной ветки (для подключения к концу)
        alternative_branch_place_id: str | None = None

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
            # Генерируем читаемое имя: "заявка отправлена", "договор подписан"
            place_name = generate_place_name(
                obj=action_data["obj"],
                action=action_data["action"],
            )
            p_after = Place(
                f"p{i + 1}",
                place_name,
                PlaceType.INTERMEDIATE,
            )
            places.append(p_after)

            if is_alternative and pending_condition_place_id:
                # Это альтернативная ветка — подключаем к месту условия
                arcs.append(Arc(pending_condition_place_id, t_id, label="Нет"))
                arcs.append(Arc(t_id, p_after.id))
                # Запоминаем место альтернативной ветки для подключения к концу
                alternative_branch_place_id = p_after.id

                # Продолжаем основной поток от положительной ветки
                if positive_branch_place_id:
                    current_place_id = positive_branch_place_id

                pending_condition = None
                pending_condition_place_id = None
                positive_branch_place_id = None

            elif has_guard:
                # Действие с условием — это XOR-split
                # Сначала подключаем к текущему месту
                arcs.append(Arc(current_place_id, t_id, label="Да"))
                arcs.append(Arc(t_id, p_after.id))

                # Запоминаем место для альтернативы
                pending_condition = action_data
                pending_condition_place_id = current_place_id
                # Запоминаем место положительной ветки
                positive_branch_place_id = p_after.id

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

        # Подключаем последнее место основного потока к концу
        arcs.append(Arc(current_place_id, p_end.id))

        # Подключаем альтернативную ветку к концу (если была)
        if alternative_branch_place_id:
            arcs.append(Arc(alternative_branch_place_id, p_end.id))

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
        2. Если нет, проверяем маркеры в начале предложения через MarkerDetector

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

        # Стратегия 2: Проверка маркеров в начале предложения через MarkerDetector
        match = self._marker_detector.detect_condition(sent.text)
        if match:
            # Маркер найден — возвращаем оставшийся текст как условие
            # или CONDITION_DETECTED если текст пустой
            return match.remaining_text.strip() or "CONDITION_DETECTED"

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
        text = text.strip().rstrip(",").strip()

        # Используем strip_condition_marker из модуля markers
        return strip_condition_marker(text)

    def _is_alternative_branch(self, sent) -> bool:
        """Проверяет, начинается ли предложение с маркера альтернативы."""
        # Используем MarkerDetector для проверки альтернативы
        return self._marker_detector.detect_alternative(sent.text) is not None
