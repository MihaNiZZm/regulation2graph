"""
Конфигурация приложения.

Аналог application.yml в Spring Boot:
- Все настройки в одном месте
- Можно переопределять через переменные окружения
- Singleton паттерн через get_settings()
"""

import os
from dataclasses import dataclass, field
from functools import lru_cache


@dataclass
class NLPSettings:
    """Настройки NLP-обработки."""

    # Маркеры начала условия (если предложение начинается с этих слов)
    condition_markers: tuple[str, ...] = (
        "если",
        "когда",
        "в случае",
        "при условии",
        "при наличии",
    )

    # Маркеры альтернативной ветки
    alternative_markers: tuple[str, ...] = (
        "иначе",
        "в противном случае",
        "если нет",
        "в ином случае",
    )

    # Синтаксические отношения для поиска условий
    condition_relations: tuple[str, ...] = ("advcl",)  # adverbial clause

    # Синтаксические отношения для поиска субъекта
    subject_relations: tuple[str, ...] = ("nsubj", "nsubj:pass")

    # Синтаксические отношения для поиска объекта
    object_relations: tuple[str, ...] = ("obj", "obl", "iobj")


@dataclass
class Neo4jSettings:
    """Настройки подключения к Neo4j."""

    uri: str = field(default_factory=lambda: os.getenv("NEO4J_URI", "bolt://localhost:7687"))
    user: str = field(default_factory=lambda: os.getenv("NEO4J_USER", "neo4j"))
    password: str = field(default_factory=lambda: os.getenv("NEO4J_PASSWORD", "password"))
    database: str = field(default_factory=lambda: os.getenv("NEO4J_DATABASE", "neo4j"))


@dataclass
class VisualizationSettings:
    """Настройки визуализации графа."""

    output_dir: str = "output"
    default_filename: str = "process_graph.png"
    figure_size: tuple[int, int] = (12, 8)
    node_size: int = 4000
    font_size: int = 8
    node_color: str = "lightblue"
    condition_node_color: str = "lightyellow"
    end_node_color: str = "lightcoral"


@dataclass
class Settings:
    """
    Главный класс настроек (как @ConfigurationProperties в Spring).

    Собирает все настройки в одном месте.
    """

    nlp: NLPSettings = field(default_factory=NLPSettings)
    neo4j: Neo4jSettings = field(default_factory=Neo4jSettings)
    visualization: VisualizationSettings = field(default_factory=VisualizationSettings)

    # Debug mode
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Получить singleton экземпляр настроек.

    Аналог @Autowired Settings settings в Spring.
    Кэшируется при первом вызове.

    Returns:
        Settings: Экземпляр настроек приложения.
    """
    return Settings()
