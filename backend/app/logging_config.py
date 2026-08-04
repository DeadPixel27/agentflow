"""
Logging setup — all log output goes to the terminal where you run uvicorn.

HOW TO READ LOGS:
  Run the server in a terminal (not hidden in background):
    cd backend && source .venv/bin/activate && uvicorn app.main:app --reload

  You'll see lines like:
    INFO  [upload] Saved test.pdf (45 KB)
    INFO  [ocr]    OCR started: photo.jpg (1600x1204)
    INFO  [ocr]    OCR done in 4.2s — 1736 chars extracted
"""

import logging
import sys


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)-5s [%(name)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )
