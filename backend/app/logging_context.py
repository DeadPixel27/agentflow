"""Request-scoped ids for stdout logs (not a substitute for DB audit)."""

from __future__ import annotations

import logging
from contextvars import ContextVar
from typing import Optional
from uuid import uuid4

_request_id: ContextVar[str] = ContextVar("request_id", default="-")
_user_id: ContextVar[str] = ContextVar("user_id", default="-")
_run_id: ContextVar[str] = ContextVar("run_id", default="-")


def new_request_id() -> str:
    return uuid4().hex[:12]


def get_request_id() -> str:
    return _request_id.get()


def get_user_id() -> str:
    return _user_id.get()


def get_run_id() -> str:
    return _run_id.get()


def set_request_id(value: Optional[str]) -> None:
    _request_id.set(value or "-")


def set_user_id(value: Optional[str]) -> None:
    _user_id.set(value or "-")


def set_run_id(value: Optional[str]) -> None:
    _run_id.set(value or "-")


def reset_log_context() -> None:
    _request_id.set("-")
    _user_id.set("-")
    _run_id.set("-")


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        record.user_id = get_user_id()
        return True
