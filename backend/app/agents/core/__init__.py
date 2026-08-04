"""Agent framework — StepHandler interface, context, and registry."""

from app.agents.core.base import StepHandler, StepResult
from app.agents.core.context import WorkflowContext, documents_to_dicts
from app.agents.core.registry import (
    get_agent_catalog,
    get_handler,
    is_valid_agent_type,
    list_agent_types,
    register_agent,
)

__all__ = [
    "StepHandler",
    "StepResult",
    "WorkflowContext",
    "documents_to_dicts",
    "register_agent",
    "get_handler",
    "get_agent_catalog",
    "list_agent_types",
    "is_valid_agent_type",
]
