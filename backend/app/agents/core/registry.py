"""
Unified agent registry — catalog metadata + handler in one registration.

Register once per agent_type; planner reads catalog, runner gets handler.
"""

from dataclasses import dataclass
from typing import Any

from app.agents.core.base import StepHandler


@dataclass(frozen=True)
class AgentDefinition:
    name: str
    description: str
    example_config: dict[str, Any]
    handler: StepHandler


_AGENTS: dict[str, AgentDefinition] = {}


def register_agent(
    agent_type: str,
    *,
    name: str,
    description: str,
    example_config: dict[str, Any],
    handler: StepHandler,
) -> None:
    if agent_type in _AGENTS:
        raise ValueError(f"Agent already registered: {agent_type}")
    _AGENTS[agent_type] = AgentDefinition(
        name=name,
        description=description,
        example_config=example_config,
        handler=handler,
    )


def get_handler(agent_type: str) -> StepHandler:
    try:
        return _AGENTS[agent_type].handler
    except KeyError as e:
        raise RuntimeError(f"No handler registered for agent_type: {agent_type}") from e


def get_agent_catalog() -> dict[str, dict[str, Any]]:
    """Planner-facing view — descriptions without handler instances."""
    return {
        agent_type: {
            "name": definition.name,
            "description": definition.description,
            "example_config": definition.example_config,
        }
        for agent_type, definition in _AGENTS.items()
    }


def list_agent_types() -> list[str]:
    return list(_AGENTS.keys())


def is_valid_agent_type(agent_type: str) -> bool:
    return agent_type in _AGENTS
