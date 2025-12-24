from natasha import (
    Segmenter, MorphVocab, NewsEmbedding,
    NewsMorphTagger, NewsSyntaxParser, Doc
)


class RuleBasedExtractor:
    def __init__(self):
        # Инициализация тяжелых моделей один раз при создании класса
        self.embedding = NewsEmbedding()
        self.segmenter = Segmenter()
        self.morph_vocab = MorphVocab()
        self.morph_tagger = NewsMorphTagger(self.embedding)
        self.syntax_parser = NewsSyntaxParser(self.embedding)

        # Наши маркеры (можно потом вынести в конфиг)
        self.condition_markers = ["если", "когда", "в случае", "при условии"]

    def parse_text(self, text: str) -> list:
        """
        Принимает сырой текст, возвращает список словарей-триплетов.
        """
        doc = Doc(text)
        doc.segment(self.segmenter)
        doc.tag_morph(self.morph_tagger)
        doc.parse_syntax(self.syntax_parser)

        results = []

        for sent in doc.sents:
            # Лемматизация (приведение к нормальной форме)
            for token in sent.tokens:
                token.lemmatize(self.morph_vocab)

            triplet = self._extract_sentence_logic(sent)
            if triplet:
                results.append(triplet)

        return results

    def _extract_sentence_logic(self, sent) -> dict:
        """Внутренняя логика разбора одного предложения"""
        # 1. Ищем Root (Действие)
        roots = [t for t in sent.tokens if t.rel == 'root']
        if not roots:
            return None
        action_token = roots[0]

        # 2. Ищем Актора
        actor = "Unknown"
        for token in sent.tokens:
            if token.head_id == action_token.id and token.rel == 'nsubj':
                actor = token.lemma
                break

        # 3. Ищем Объект
        obj = "-"
        for token in sent.tokens:
            if token.head_id == action_token.id and (token.rel == 'obj' or token.rel == 'obl'):
                obj = token.lemma
                break

        # 4. Проверяем условие
        condition = None
        if sent.tokens[0].lemma.lower() in self.condition_markers:
            condition = "CONDITION_DETECTED"  # Различные условия, такие как работа с датами и числительными, будут добавлены в следующих версиях.

        return {
            "actor": actor,
            "action": action_token.lemma,
            "object": obj,
            "condition": condition,
            "full_text": sent.text
        }
