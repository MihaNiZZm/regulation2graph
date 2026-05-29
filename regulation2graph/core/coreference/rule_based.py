"""
Rule-based резолвер кореференции на основе pymorphy3.

Использует согласование по роду и числу для разрешения местоимений.
Подходит для простых случаев и как fallback без GPU.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import pymorphy3

from regulation2graph.core.coreference.models import (
    CoreferenceCluster,
    CoreferenceResult,
    Mention,
)


@dataclass
class EntityCandidate:
    """Кандидат на антецедент (существительное)."""

    text: str  # Текст сущности
    lemma: str  # Лемма (начальная форма)
    start: int  # Позиция в тексте
    end: int
    gender: str | None  # masc, femn, neut
    number: str | None  # sing, plur
    case: str | None  # nomn, gent, datv, accs, ablt, loct


@dataclass
class PronounMatch:
    """Найденное местоимение."""

    text: str
    start: int
    end: int
    gender: str | None  # masc, femn, neut
    number: str | None  # sing, plur
    case: str | None
    is_possessive: bool  # его/её/их vs он/она/они


class RuleBasedResolver:
    """
    Rule-based резолвер кореференции.

    Стратегия:
    1. Находит все существительные (потенциальные антецеденты)
    2. Находит все местоимения (он/она/они, его/её/их)
    3. Матчит местоимения с ближайшим подходящим антецедентом по роду/числу
    4. Заменяет местоимения на антецеденты

    Example:
        >>> resolver = RuleBasedResolver()
        >>> result = resolver.resolve("Менеджер проверяет заявку. Он подписывает её.")
        >>> result.resolved_text
        'Менеджер проверяет заявку. Менеджер подписывает заявку.'
    """

    # Личные местоимения 3-го лица
    PERSONAL_PRONOUNS = {
        # Мужской род, ед. число
        "он": ("masc", "sing", "nomn"),
        "его": ("masc", "sing", "gent"),  # также accs для одуш.
        "ему": ("masc", "sing", "datv"),
        "им": ("masc", "sing", "ablt"),
        "нём": ("masc", "sing", "loct"),
        # Женский род, ед. число
        "она": ("femn", "sing", "nomn"),
        "её": ("femn", "sing", "gent"),  # также accs
        "ей": ("femn", "sing", "datv"),
        "ею": ("femn", "sing", "ablt"),
        "ней": ("femn", "sing", "loct"),
        # Средний род, ед. число
        "оно": ("neut", "sing", "nomn"),
        # его, ему, им, нём — совпадают с мужским родом
        # Множественное число
        "они": (None, "plur", "nomn"),
        "их": (None, "plur", "gent"),
        "им": (None, "plur", "datv"),  # совпадает с ед.ч. м.р.
        "ими": (None, "plur", "ablt"),
        "них": (None, "plur", "loct"),
    }

    # Притяжательные местоимения (совпадают с родительным падежом личных)
    POSSESSIVE_FORMS = frozenset({"его", "её", "их"})

    def __init__(self) -> None:
        """Инициализация с pymorphy3."""
        self._morph = pymorphy3.MorphAnalyzer()

    def resolve(self, text: str) -> CoreferenceResult:
        """
        Разрешает кореференции в тексте.

        Args:
            text: Текст для обработки.

        Returns:
            CoreferenceResult с разрешёнными местоимениями.
        """
        # 1. Находим все существительные (потенциальные антецеденты)
        entities = self._extract_entities(text)

        # 2. Находим все местоимения
        pronouns = self._extract_pronouns(text)

        if not pronouns:
            # Нет местоимений — возвращаем исходный текст
            return CoreferenceResult(
                original_text=text,
                resolved_text=text,
                clusters=(),
            )

        # 3. Резолвим каждое местоимение
        replacements: list[tuple[int, int, str, str]] = []  # (start, end, old, new)
        clusters: list[CoreferenceCluster] = []

        for pronoun in pronouns:
            antecedent = self._find_antecedent(pronoun, entities)
            if antecedent:
                # Получаем форму антецедента в нужном падеже
                resolved_form = self._inflect_to_case(
                    antecedent.lemma, pronoun.case
                )
                replacements.append((
                    pronoun.start,
                    pronoun.end,
                    pronoun.text,
                    resolved_form,
                ))

                # Создаём кластер
                clusters.append(CoreferenceCluster(
                    mentions=(
                        Mention(antecedent.text, antecedent.start, antecedent.end),
                        Mention(pronoun.text, pronoun.start, pronoun.end),
                    ),
                    head_index=0,
                ))

        # 4. Применяем замены (от конца к началу, чтобы не сбить позиции)
        resolved_text = text
        for start, end, old, new in sorted(replacements, key=lambda x: -x[0]):
            resolved_text = resolved_text[:start] + new + resolved_text[end:]

        return CoreferenceResult(
            original_text=text,
            resolved_text=resolved_text,
            clusters=tuple(clusters),
        )

    def _extract_entities(self, text: str) -> list[EntityCandidate]:
        """
        Извлекает существительные из текста.

        Returns:
            Список EntityCandidate отсортированный по позиции.
        """
        entities: list[EntityCandidate] = []

        # Простой токенизатор по словам
        for match in re.finditer(r"\b[а-яёА-ЯЁ]+\b", text):
            word = match.group()
            start = match.start()
            end = match.end()

            # Анализируем морфологию
            parsed = self._morph.parse(word)
            if not parsed:
                continue

            # Берём наиболее вероятный разбор
            best = parsed[0]

            # Проверяем, что это существительное
            if "NOUN" not in best.tag:
                continue

            entities.append(EntityCandidate(
                text=word,
                lemma=best.normal_form,
                start=start,
                end=end,
                gender=best.tag.gender,
                number=best.tag.number,
                case=best.tag.case,
            ))

        return entities

    def _extract_pronouns(self, text: str) -> list[PronounMatch]:
        """
        Извлекает местоимения 3-го лица из текста.

        Returns:
            Список PronounMatch отсортированный по позиции.
        """
        pronouns: list[PronounMatch] = []

        # Ищем все слова и проверяем, являются ли они местоимениями
        for match in re.finditer(r"\b([а-яёА-ЯЁ]+)\b", text):
            word = match.group().lower()
            start = match.start()
            end = match.end()

            if word in self.PERSONAL_PRONOUNS:
                gender, number, case = self.PERSONAL_PRONOUNS[word]
                pronouns.append(PronounMatch(
                    text=match.group(),
                    start=start,
                    end=end,
                    gender=gender,
                    number=number,
                    case=case,
                    is_possessive=word in self.POSSESSIVE_FORMS,
                ))

        return pronouns

    def _find_antecedent(
        self,
        pronoun: PronounMatch,
        entities: list[EntityCandidate],
    ) -> EntityCandidate | None:
        """
        Находит антецедент для местоимения.

        Стратегия: ближайшее существительное с совпадающим родом/числом,
        расположенное ПЕРЕД местоимением.

        Args:
            pronoun: Местоимение для резолва.
            entities: Список кандидатов (существительных).

        Returns:
            Подходящий антецедент или None.
        """
        # Фильтруем кандидатов, которые находятся перед местоимением
        candidates = [e for e in entities if e.end <= pronoun.start]

        if not candidates:
            return None

        # Фильтруем по роду и числу
        matching = []
        for entity in candidates:
            # Проверяем число
            if pronoun.number and entity.number and pronoun.number != entity.number:
                continue

            # Проверяем род (для единственного числа)
            if pronoun.number == "sing" and pronoun.gender:
                if entity.gender and pronoun.gender != entity.gender:
                    continue

            matching.append(entity)

        if not matching:
            # Если нет точного совпадения, берём ближайшее
            # (для множественного числа род не важен)
            if pronoun.number == "plur":
                matching = candidates

        if not matching:
            return None

        # Возвращаем ближайший к местоимению (последний в списке)
        return matching[-1]

    def _inflect_to_case(self, lemma: str, target_case: str | None) -> str:
        """
        Склоняет слово в нужный падеж.

        Args:
            lemma: Начальная форма слова.
            target_case: Целевой падеж (nomn, gent, datv, accs, ablt, loct).

        Returns:
            Слово в нужном падеже.
        """
        if not target_case:
            return lemma

        parsed = self._morph.parse(lemma)
        if not parsed:
            return lemma

        best = parsed[0]

        # Склоняем
        inflected = best.inflect({target_case})
        if inflected:
            return inflected.word

        return lemma
