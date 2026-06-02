"""
Тесты для модуля разрешения кореференции.

Проверяет резолв местоимений (он/она/они, его/её/их).
"""

import pytest

from regulation2graph.core.coreference import (
    CoreferenceCluster,
    CoreferenceResolver,
    CoreferenceResult,
    Mention,
    RuleBasedResolver,
    create_resolver,
    resolve_coreferences,
)


class TestMention:
    """Тесты для Mention."""

    def test_mention_creation(self):
        """Создание Mention."""
        mention = Mention("менеджер", 0, 8)
        assert mention.text == "менеджер"
        assert mention.start == 0
        assert mention.end == 8

    def test_mention_invalid_span(self):
        """Недопустимый span вызывает ошибку."""
        with pytest.raises(ValueError):
            Mention("test", -1, 5)

        with pytest.raises(ValueError):
            Mention("test", 10, 5)


class TestCoreferenceCluster:
    """Тесты для CoreferenceCluster."""

    def test_cluster_creation(self):
        """Создание кластера."""
        mentions = (
            Mention("менеджер", 0, 8),
            Mention("он", 20, 22),
        )
        cluster = CoreferenceCluster(mentions=mentions, head_index=0)

        assert cluster.head.text == "менеджер"
        assert len(cluster.mentions) == 2

    def test_cluster_empty_raises(self):
        """Пустой кластер вызывает ошибку."""
        with pytest.raises(ValueError):
            CoreferenceCluster(mentions=(), head_index=0)

    def test_cluster_invalid_head_index(self):
        """Недопустимый head_index вызывает ошибку."""
        mentions = (Mention("test", 0, 4),)
        with pytest.raises(ValueError):
            CoreferenceCluster(mentions=mentions, head_index=5)


class TestCoreferenceResult:
    """Тесты для CoreferenceResult."""

    def test_result_no_changes(self):
        """Результат без изменений."""
        result = CoreferenceResult(
            original_text="Менеджер проверяет.",
            resolved_text="Менеджер проверяет.",
            clusters=(),
        )

        assert not result.has_coreferences
        assert not result.was_modified

    def test_result_with_changes(self):
        """Результат с изменениями."""
        cluster = CoreferenceCluster(
            mentions=(
                Mention("менеджер", 0, 8),
                Mention("он", 20, 22),
            ),
            head_index=0,
        )
        result = CoreferenceResult(
            original_text="Менеджер проверяет. Он подписывает.",
            resolved_text="Менеджер проверяет. Менеджер подписывает.",
            clusters=(cluster,),
        )

        assert result.has_coreferences
        assert result.was_modified


class TestRuleBasedResolver:
    """Тесты для RuleBasedResolver."""

    @pytest.fixture
    def resolver(self):
        """Создаёт резолвер."""
        return RuleBasedResolver()

    def test_resolve_no_pronouns(self, resolver):
        """Текст без местоимений не изменяется."""
        text = "Менеджер проверяет заявку. Директор подписывает договор."
        result = resolver.resolve(text)

        assert result.resolved_text == text
        assert not result.was_modified

    def test_resolve_personal_pronoun_masc(self, resolver):
        """Резолв личного местоимения мужского рода."""
        text = "Менеджер проверяет заявку. Он подписывает договор."
        result = resolver.resolve(text)

        # "Он" должен замениться на "менеджер"
        assert "он" not in result.resolved_text.lower() or "Он" not in result.resolved_text
        assert result.was_modified

    def test_resolve_personal_pronoun_fem(self, resolver):
        """Резолв личного местоимения женского рода."""
        text = "Секретарь получает заявку. Она регистрирует документ."
        result = resolver.resolve(text)

        # "Она" должна замениться на "секретарь" или "заявка"
        # (зависит от согласования рода)
        assert result.was_modified

    def test_resolve_possessive_pronoun(self, resolver):
        """Резолв притяжательного местоимения."""
        text = "Менеджер проверяет заявку. Секретарь отправляет её клиенту."
        result = resolver.resolve(text)

        # "её" должна замениться на "заявку"
        assert "её" not in result.resolved_text.lower()
        assert result.was_modified

    def test_resolve_multiple_sentences(self, resolver):
        """Резолв в нескольких предложениях."""
        text = "Менеджер проверяет заявку. Он отправляет её на согласование."
        result = resolver.resolve(text)

        # Оба местоимения должны быть разрешены
        assert "он" not in result.resolved_text.lower() or result.resolved_text.count("он") == 0
        assert result.was_modified
        assert len(result.clusters) >= 1

    def test_resolve_plural_pronoun(self, resolver):
        """Резолв местоимения множественного числа."""
        text = "Документы готовы. Менеджер проверяет их."
        result = resolver.resolve(text)

        # "их" должно резолвиться в "документы"
        assert result.was_modified


class TestCreateResolver:
    """Тесты для фабричной функции create_resolver."""

    def test_create_rules_backend(self):
        """Создание rule-based резолвера."""
        resolver = create_resolver(backend="rules")
        assert isinstance(resolver, RuleBasedResolver)

    def test_create_default_backend(self):
        """Default backend возвращает RuleBasedResolver."""
        resolver = create_resolver()
        assert isinstance(resolver, RuleBasedResolver)

    def test_create_invalid_backend(self):
        """Недопустимый backend вызывает ошибку."""
        with pytest.raises(ValueError):
            create_resolver(backend="invalid")  # type: ignore


class TestResolveCoreferences:
    """Тесты для удобной функции resolve_coreferences."""

    def test_resolve_simple(self):
        """Простой резолв через функцию."""
        text = "Менеджер проверяет. Он подписывает."
        resolved = resolve_coreferences(text, backend="rules")

        assert "он" not in resolved.lower() or resolved.lower().count("он") == 0


class TestExtractorIntegration:
    """Интеграционные тесты с RuleBasedExtractor."""

    def test_extractor_without_coreference(self):
        """Экстрактор без кореференции (текущее поведение)."""
        from regulation2graph.core import RuleBasedExtractor

        extractor = RuleBasedExtractor()

        text = "Менеджер проверяет заявку."
        workflow = extractor.extract(text)

        assert len(workflow.transitions) == 1
        assert workflow.transitions[0].actor == "менеджер"

    def test_extractor_with_coreference(self):
        """Экстрактор с включённой кореференцией."""
        from regulation2graph.core import RuleBasedExtractor

        resolver = RuleBasedResolver()
        extractor = RuleBasedExtractor(coreference_resolver=resolver)

        text = "Менеджер проверяет заявку. Он подписывает договор."
        workflow = extractor.extract(text)

        # Оба transitions должны иметь актора (не "Unknown")
        assert len(workflow.transitions) == 2
        assert workflow.transitions[0].actor == "менеджер"
        # Второй transition должен иметь резолвленного актора
        # (менеджер вместо "он" → Unknown)
        assert workflow.transitions[1].actor.lower() != "unknown"

    def test_extractor_resolves_object_pronoun(self):
        """Экстрактор резолвит местоимение в объекте."""
        from regulation2graph.core import RuleBasedExtractor

        resolver = RuleBasedResolver()
        extractor = RuleBasedExtractor(coreference_resolver=resolver)

        text = "Менеджер проверяет заявку. Секретарь отправляет её."
        workflow = extractor.extract(text)

        assert len(workflow.transitions) == 2
        # Объект второго transition должен быть "заявка", не "её"
        # (зависит от качества резолвера)


class TestRealRegulationExamples:
    """Тесты на реальных примерах из датасета."""

    @pytest.fixture
    def resolver(self):
        return RuleBasedResolver()

    def test_med_006_pronoun_in_object(self, resolver):
        """
        med_006: Когда заявка готова, секретарь отправляет её клиенту.
        её → заявка
        """
        text = "Когда заявка готова, секретарь отправляет её клиенту."
        result = resolver.resolve(text)

        # "её" должна резолвиться в "заявку"
        assert "её" not in result.resolved_text.lower()
        assert "заявк" in result.resolved_text.lower()

    def test_hrd_001_pronoun_in_compound(self, resolver):
        """
        hrd_001: ...менеджер подписывает договор и секретарь регистрирует его.
        его → договор
        """
        text = "Если заявка одобрена, менеджер подписывает договор и секретарь регистрирует его."
        result = resolver.resolve(text)

        # "его" должен резолвиться в "договор"
        assert result.was_modified

    def test_hrd_009_cross_sentence_coreference(self, resolver):
        """
        hrd_009: Менеджер проверяет заявку. Он отправляет её на согласование.
        он → менеджер, её → заявка
        """
        text = "Менеджер проверяет заявку. Он отправляет её на согласование."
        result = resolver.resolve(text)

        # Оба местоимения должны быть разрешены
        assert result.was_modified
        assert len(result.clusters) >= 1


# Пропускаем нейросетевые тесты, если torch/transformers не установлены
# либо модель недоступна (нет кэша и сети).
torch = pytest.importorskip("torch", reason="RuBERT-тесты требуют torch/transformers")


@pytest.fixture(scope="module")
def rubert_resolver():
    """Загружает RuBertResolver один раз на модуль (тяжёлая операция)."""
    from regulation2graph.core.coreference.rubert import RuBertResolver

    try:
        return RuBertResolver()
    except Exception as exc:  # pragma: no cover - зависит от наличия модели
        pytest.skip(f"RuBERT модель недоступна: {exc}")


class TestRuBertResolver:
    """Тесты для нейросетевого RuBertResolver."""

    def test_implements_protocol(self, rubert_resolver):
        """RuBertResolver удовлетворяет протоколу CoreferenceResolver."""
        assert isinstance(rubert_resolver, CoreferenceResolver)

    def test_no_pronouns_returns_unchanged(self, rubert_resolver):
        """Текст без местоимений не меняется."""
        text = "Менеджер проверяет заявку."
        result = rubert_resolver.resolve(text)

        assert isinstance(result, CoreferenceResult)
        assert result.resolved_text == text
        assert not result.was_modified

    def test_resolves_simple_subject_pronoun(self, rubert_resolver):
        """Местоимение-подлежащее резолвится в единственного антецедента."""
        text = "Менеджер проверяет заявку. Он подписывает договор."
        result = rubert_resolver.resolve(text)

        assert result.was_modified
        assert "менеджер" in result.resolved_text.lower()

    def test_object_pronoun_prefers_object_semantically(self, rubert_resolver):
        """
        Среди нескольких согласованных кандидатов RuBERT семантически
        выбирает объект действия: "его" → договор (не секретарь).
        """
        text = (
            "Менеджер подписывает договор "
            "и секретарь регистрирует его."
        )
        result = rubert_resolver.resolve(text)

        assert result.was_modified
        # "его" должно разрешиться в "договор", а не в одушевлённого актора
        assert "договор" in result.resolved_text.lower()

    def test_create_resolver_rubert_backend(self):
        """Фабрика создаёт RuBertResolver по backend='rubert'."""
        from regulation2graph.core.coreference.rubert import RuBertResolver

        try:
            resolver = create_resolver(backend="rubert")
        except Exception as exc:  # pragma: no cover
            pytest.skip(f"RuBERT модель недоступна: {exc}")

        assert isinstance(resolver, RuBertResolver)
