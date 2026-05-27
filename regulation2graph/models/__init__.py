"""Data models for regulation2graph."""

# Legacy imports (для обратной совместимости)
from regulation2graph.models.triplet import GatewayType, Triplet

# Workflow Net models (новая архитектура)
from regulation2graph.models.workflow import (
    Arc,
    Place,
    PlaceType,
    Transition,
    TransitionType,
    WorkflowNet,
)

__all__ = [
    # Legacy
    "Triplet",
    "GatewayType",
    # Workflow Net
    "Place",
    "PlaceType",
    "Transition",
    "TransitionType",
    "Arc",
    "WorkflowNet",
]
