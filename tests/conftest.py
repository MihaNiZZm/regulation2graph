"""
Pytest fixtures - общие настройки для тестов.

Аналог @BeforeEach / @TestConfiguration в Spring.
"""

import pytest

from regulation2graph.core import RuleBasedExtractor


@pytest.fixture(scope="session")
def extractor() -> RuleBasedExtractor:
    """
    Фикстура для RuleBasedExtractor.

    scope="session" означает, что экстрактор создаётся один раз
    на всю сессию тестов (экономит время на загрузке моделей).
    """
    return RuleBasedExtractor()
