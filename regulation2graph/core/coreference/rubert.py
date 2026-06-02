"""
Нейросетевой резолвер кореференции на основе RuBERT.

Использует контекстные эмбеддинги предобученной модели RuBERT
(`ai-forever/ruBert-base`) для ранжирования кандидатов-антецедентов
(mention-ranking).

В отличие от RuleBasedResolver, который опирается только на морфологическое
согласование (род/число), RuBertResolver дополнительно учитывает семантику
контекста: для каждого местоимения он сравнивает его контекстный эмбеддинг
с эмбеддингами кандидатов-существительных и выбирает наиболее близкий по
смыслу (с мягким фильтром по роду/числу и приоритетом близости).

Морфология (поиск упоминаний, склонение антецедента в нужный падеж)
переиспользуется из RuleBasedResolver, что обеспечивает консистентность
с rule-based режимом и корректную замену словоформ.

Требует тяжёлых зависимостей (torch, transformers):
    pip install -e ".[coref]"
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from regulation2graph.core.coreference.models import (
    CoreferenceCluster,
    CoreferenceResult,
    Mention,
)
from regulation2graph.core.coreference.rule_based import (
    EntityCandidate,
    PronounMatch,
    RuleBasedResolver,
)

if TYPE_CHECKING:
    import torch


DEFAULT_MODEL = "ai-forever/ruBert-base"
_MAX_TOKENS = 512


class RuBertResolverNotAvailableError(ImportError):
    """torch/transformers не установлены."""


class RuBertResolver:
    """
    RuBERT-based резолвер кореференции (нейросетевой mention-ranking).

    Стратегия:
    1. Находит упоминания (существительные + местоимения 3-го лица)
       тем же морфологическим анализатором, что и RuleBasedResolver.
    2. Один раз прогоняет текст через RuBERT и получает контекстные
       эмбеддинги всех токенов.
    3. Для каждого местоимения ранжирует кандидатов-антецедентов
       (стоящих перед ним) по близости эмбеддингов + приоритету близости,
       с мягким фильтром по роду/числу.
    4. Заменяет местоимение на выбранный антецедент, склоняя его
       в нужный падеж через pymorphy3.

    Example:
        >>> resolver = RuBertResolver()
        >>> result = resolver.resolve("Менеджер проверяет заявку. Он подписывает её.")
        >>> result.resolved_text
        'Менеджер проверяет заявку. Менеджер подписывает заявку.'
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        device: str | None = None,
        agreement_filter: bool = True,
        recency_weight: float = 0.15,
    ) -> None:
        """
        Инициализация резолвера.

        Args:
            model_name: Имя/путь модели RuBERT на HuggingFace Hub.
            device: Устройство вычислений ("mps", "cuda", "cpu").
                Если None — выбирается автоматически: mps → cuda → cpu.
            agreement_filter: Применять мягкий фильтр по роду/числу
                перед нейросетевым ранжированием.
            recency_weight: Вес приоритета близости антецедента к местоимению
                (0 — только семантика, 1 — только близость).

        Raises:
            RuBertResolverNotAvailableError: Если torch/transformers не установлены.
        """
        try:
            import torch
            from transformers import AutoModel, AutoTokenizer
        except ImportError as exc:  # pragma: no cover - зависит от окружения
            raise RuBertResolverNotAvailableError(
                "RuBertResolver требует 'torch' и 'transformers'. "
                'Установите их: pip install -e ".[coref]"'
            ) from exc

        self._torch = torch
        self._device = device or self._auto_device()
        self._agreement_filter = agreement_filter
        self._recency_weight = recency_weight

        self._tokenizer = AutoTokenizer.from_pretrained(model_name, use_fast=True)
        self._model = AutoModel.from_pretrained(model_name)
        self._model.eval()
        self._model.to(self._device)

        # Переиспользуем морфологию rule-based резолвера:
        # извлечение упоминаний и склонение антецедента.
        self._rule = RuleBasedResolver()

    def _auto_device(self) -> str:
        """Автовыбор устройства: mps → cuda → cpu."""
        torch = self._torch
        if torch.backends.mps.is_available():
            return "mps"
        if torch.cuda.is_available():
            return "cuda"
        return "cpu"

    def resolve(self, text: str) -> CoreferenceResult:
        """
        Разрешает кореференции в тексте.

        Args:
            text: Текст для обработки.

        Returns:
            CoreferenceResult с разрешёнными местоимениями.
        """
        entities = self._rule._extract_entities(text)
        pronouns = self._rule._extract_pronouns(text)

        if not pronouns:
            return CoreferenceResult(
                original_text=text,
                resolved_text=text,
                clusters=(),
            )

        # Контекстные эмбеддинги токенов и их посимвольные границы.
        hidden, offsets = self._encode(text)

        replacements: list[tuple[int, int, str]] = []  # (start, end, new)
        clusters: list[CoreferenceCluster] = []

        for pronoun in pronouns:
            antecedent = self._find_antecedent_neural(
                pronoun, entities, hidden, offsets
            )
            if antecedent is None:
                continue

            resolved_form = self._rule._inflect_to_case(
                antecedent.lemma, pronoun.case
            )
            replacements.append((pronoun.start, pronoun.end, resolved_form))
            clusters.append(
                CoreferenceCluster(
                    mentions=(
                        Mention(antecedent.text, antecedent.start, antecedent.end),
                        Mention(pronoun.text, pronoun.start, pronoun.end),
                    ),
                    head_index=0,
                )
            )

        resolved_text = text
        for start, end, new in sorted(replacements, key=lambda x: -x[0]):
            resolved_text = resolved_text[:start] + new + resolved_text[end:]

        return CoreferenceResult(
            original_text=text,
            resolved_text=resolved_text,
            clusters=tuple(clusters),
        )

    def _encode(self, text: str) -> tuple[torch.Tensor, list[tuple[int, int]]]:
        """
        Прогоняет текст через RuBERT и возвращает эмбеддинги токенов
        вместе с их посимвольными границами (offset mapping).

        Returns:
            (hidden, offsets), где hidden: (seq_len, hidden_dim),
            offsets: список (char_start, char_end) для каждого токена.
        """
        torch = self._torch
        encoded = self._tokenizer(
            text,
            return_offsets_mapping=True,
            return_tensors="pt",
            truncation=True,
            max_length=_MAX_TOKENS,
        )
        offsets = [tuple(o) for o in encoded["offset_mapping"][0].tolist()]
        input_ids = encoded["input_ids"].to(self._device)
        attention_mask = encoded["attention_mask"].to(self._device)

        with torch.no_grad():
            output = self._model(input_ids=input_ids, attention_mask=attention_mask)

        hidden = output.last_hidden_state[0]  # (seq_len, hidden_dim)
        return hidden, offsets

    def _span_embedding(
        self,
        hidden: torch.Tensor,
        offsets: list[tuple[int, int]],
        start: int,
        end: int,
    ) -> torch.Tensor | None:
        """
        Усреднённый эмбеддинг подтокенов, пересекающих посимвольный спан
        [start, end).

        Returns:
            Тензор эмбеддинга или None, если спан не покрыт токенами
            (например, обрезан при truncation).
        """
        indices = [
            i
            for i, (o_start, o_end) in enumerate(offsets)
            if o_end > o_start  # пропускаем спецтокены ([CLS], [SEP]) с (0, 0)
            and o_start < end
            and o_end > start
        ]
        if not indices:
            return None

        idx = self._torch.tensor(indices, device=hidden.device)
        return hidden.index_select(0, idx).mean(dim=0)

    def _find_antecedent_neural(
        self,
        pronoun: PronounMatch,
        entities: list[EntityCandidate],
        hidden: torch.Tensor,
        offsets: list[tuple[int, int]],
    ) -> EntityCandidate | None:
        """
        Находит антецедент местоимения нейросетевым ранжированием.

        Среди существительных, стоящих перед местоимением и (мягко)
        согласованных по роду/числу, выбирает кандидата с максимальной
        комбинированной оценкой: семантическая близость эмбеддингов +
        приоритет близости к местоимению.
        """
        candidates = [e for e in entities if e.end <= pronoun.start]
        if not candidates:
            return None

        if self._agreement_filter:
            # Жёсткий фильтр: ранжируем нейросетью только среди кандидатов,
            # согласованных по роду/числу. Если согласованных нет —
            # антецедент не выбираем (как в rule-based), чтобы не делать
            # ошибочную замену по слабому семантическому сигналу.
            candidates = self._filter_by_agreement(pronoun, candidates)
        if not candidates:
            return None

        # Если согласованный кандидат всего один — нейросеть не нужна.
        if len(candidates) == 1:
            return candidates[0]

        pronoun_emb = self._span_embedding(
            hidden, offsets, pronoun.start, pronoun.end
        )
        if pronoun_emb is None:
            # Местоимение вне покрытия токенов — fallback на ближайшего кандидата.
            return candidates[-1]

        torch = self._torch
        # Длина текста в символах = максимальная правая граница среди всех
        # токенов. Берём max по всем offset'ам, т.к. последний токен — [SEP]
        # со спаном (0, 0), и offsets[-1][1] дал бы 0.
        text_len = max((o_end for _, o_end in offsets), default=1) or 1

        best_candidate: EntityCandidate | None = None
        best_score = float("-inf")

        for candidate in candidates:
            cand_emb = self._span_embedding(
                hidden, offsets, candidate.start, candidate.end
            )
            if cand_emb is None:
                continue

            sim = torch.nn.functional.cosine_similarity(
                pronoun_emb, cand_emb, dim=0
            ).item()
            # Нормируем близость в [0, 1].
            sim_norm = (sim + 1.0) / 2.0
            # Приоритет близости: чем ближе кандидат к местоимению, тем выше.
            recency = candidate.start / text_len
            score = (1.0 - self._recency_weight) * sim_norm + (
                self._recency_weight * recency
            )

            if score > best_score:
                best_score = score
                best_candidate = candidate

        # Если ни один кандидат не покрыт токенами — берём ближайший.
        return best_candidate or candidates[-1]

    @staticmethod
    def _filter_by_agreement(
        pronoun: PronounMatch,
        candidates: list[EntityCandidate],
    ) -> list[EntityCandidate]:
        """
        Жёсткий фильтр кандидатов по согласованию рода/числа с местоимением.

        Возвращает только согласованных кандидатов (может быть пустым).
        Нейросетевое ранжирование применяется лишь когда таких кандидатов
        несколько — это исключает ошибочные срабатывания на слабом сигнале.
        """
        matching = []
        for entity in candidates:
            if pronoun.number and entity.number and pronoun.number != entity.number:
                continue
            if pronoun.number == "sing" and pronoun.gender:
                if entity.gender and pronoun.gender != entity.gender:
                    continue
            matching.append(entity)

        return matching
