"""
Logging setup — stdout metadata only (ids, timings). Not document text.
"""

import logging
import sys

from app.logging_context import RequestContextFilter


def setup_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            "%(levelname)-5s [%(name)s] rid=%(request_id)s uid=%(user_id)s %(message)s"
        )
    )
    handler.addFilter(RequestContextFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
