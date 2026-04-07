"""
Rule-based извлечение триплетов из текста.
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
from regulation2graph.models import GatewayType, Triplet


class RuleBasedExtractor:
    """
    Извлекает триплеты (Субъект-Действие-Объект) из текста на русском языке.

    Использует библиотеку Natasha для:
    - Сегментации текста на предложения
    - Морфологического анализа
    - Синтаксического разбора

    Example:
        >>> extractor = RuleBasedExtractor()
        >>> triplets = extractor.parse_text("Менеджер проверяет заявку.")
        >>> print(triplets[0].actor)
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

    def parse_text(self, text: str) -> list[Triplet]:
        """
        Разбирает текст и извлекает список триплетов.

        Args:
            text: Текст регламента на русском языке.

        Returns:
            Список извлечённых триплетов.
        """
        doc = Doc(text)
        doc.segment(self._segmenter)
        doc.tag_morph(self._morph_tagger)
        doc.parse_syntax(self._syntax_parser)

        results: list[Triplet] = []

        for sent in doc.sents:
            # Лемматизация всех токенов
            for token in sent.tokens:
                token.lemmatize(self._morph_vocab)

            triplet = self._extract_from_sentence(sent)
            if triplet:
                results.append(triplet)

        return results

    def _extract_from_sentence(self, sent) -> Triplet | None:
        """
        Извлекает триплет из одного предложения.

        Args:
            sent: Предложение из Natasha Doc.

        Returns:
            Triplet или None если не удалось извлечь.
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

        # 4. Проверяем условие (простая проверка по первому слову)
        condition_text = self._extract_condition(sent, action_token)

        # 5. Проверяем маркер альтернативы
        is_alternative = self._is_alternative_branch(sent)

        # 6. Определяем тип шлюза
        gateway_type = None
        if condition_text:
            gateway_type = GatewayType.EXCLUSIVE

        return Triplet(
            actor=actor,
            action=action_token.lemma,
            obj=obj,
            condition_text=condition_text,
            is_alternative=is_alternative,
            full_text=sent.text.strip(),
            gateway_type=gateway_type,
        )

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
