"""Tests for transform.pipeline_refiner agent registration."""

import app.agents.handlers  # noqa: F401
from app.agents.core.registry import get_agent_catalog, get_handler, is_valid_agent_type


def test_pipeline_refiner_registered_in_catalog():
    assert is_valid_agent_type("transform.pipeline_refiner")
    catalog = get_agent_catalog()
    assert "transform.pipeline_refiner" in catalog
    assert catalog["transform.pipeline_refiner"]["name"] == "Pipeline Refiner"


def test_pipeline_refiner_handler_is_callable():
    handler = get_handler("transform.pipeline_refiner")
    assert handler is not None
