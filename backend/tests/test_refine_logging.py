"""Refine logging must not dump payloads at INFO by default."""

import json
import logging

from app.services.pipeline.refine_logging import (
    log_field_snapshot,
    log_preview_diff,
    log_prompt,
)


def test_log_prompt_omits_tail_by_default(caplog, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "log_payloads", False)
    logger = logging.getLogger("test_refine_log")
    with caplog.at_level(logging.INFO, logger="test_refine_log"):
        log_prompt(
            logger,
            "apply",
            run_id="run-1",
            label="user_message_to_refiner",
            prompt="SECRET invoice total 4812.50",
        )
    assert "SECRET" not in caplog.text
    assert "4812.50" not in caplog.text
    payload = json.loads(caplog.records[0].message.replace("[refine] ", "", 1))
    assert payload["prompt_len"] == len("SECRET invoice total 4812.50")
    assert "prompt_tail" not in payload


def test_log_field_snapshot_omits_values(caplog, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "log_payloads", False)
    logger = logging.getLogger("test_refine_fields")
    with caplog.at_level(logging.INFO, logger="test_refine_fields"):
        log_field_snapshot(
            logger,
            "execute-extract-result",
            run_id="run-1",
            document_id="doc-1",
            fields={"vendor": "Acme Corp", "total": 99.5},
        )
    assert "Acme Corp" not in caplog.text
    payload = json.loads(caplog.records[0].message.replace("[refine] ", "", 1))
    assert "vendor" in payload["field_names"]
    assert "fields" not in payload


def test_log_preview_diff_omits_values(caplog, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "log_payloads", False)
    logger = logging.getLogger("test_refine_diff")
    with caplog.at_level(logging.INFO, logger="test_refine_diff"):
        log_preview_diff(
            logger,
            run_id="run-1",
            document_id="doc-1",
            field="total",
            before=1,
            after=2,
        )
    payload = json.loads(caplog.records[0].message.replace("[refine] ", "", 1))
    assert payload["changed"] is True
    assert "before" not in payload
