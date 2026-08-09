"""
OCR engine abstraction - pluggable OCR backend.

Supports:
- tesseract: System Tesseract via pytesseract (default fallback)
- rapidocr: PaddleOCR models via ONNX Runtime (recommended, faster + more accurate)

Config: OCR_ENGINE env var or settings.ocr_engine
"""

from __future__ import annotations

import logging
import shutil
from typing import Protocol

from PIL import Image

from app.config import settings

logger = logging.getLogger("ocr")


class OCREngine(Protocol):
    """Interface for OCR engines."""

    def ocr_image(self, image: Image.Image) -> str: ...

    @property
    def name(self) -> str: ...


class TesseractEngine:
    """OCR using system Tesseract via pytesseract."""

    @property
    def name(self) -> str:
        return "tesseract"

    def ocr_image(self, image: Image.Image) -> str:
        import pytesseract

        if shutil.which("tesseract") is None:
            raise RuntimeError(
                "Tesseract is not installed. Install it with:\n"
                "  macOS:   brew install tesseract\n"
                "  Ubuntu:  sudo apt install tesseract-ocr\n"
                "  Windows: https://github.com/UB-Mannheim/tesseract/wiki"
            )
        return pytesseract.image_to_string(image)


class RapidOCREngine:
    """OCR using PaddleOCR models via ONNX Runtime, CPU-only, no GPU needed."""

    def __init__(self) -> None:
        try:
            from rapidocr_onnxruntime import RapidOCR
        except ImportError as exc:
            raise ImportError(
                "rapidocr-onnxruntime not installed. "
                "Install with: pip install rapidocr-onnxruntime"
            ) from exc
        self._engine = RapidOCR()

    @property
    def name(self) -> str:
        return "rapidocr"

    def ocr_image(self, image: Image.Image) -> str:
        import numpy as np

        img_array = np.array(image)
        result, _ = self._engine(img_array)
        if not result:
            return ""
        # result is list of [bbox, text, confidence]
        lines = [line[1] for line in result]
        return "\n".join(lines)


# Singleton engine instance
_engine: OCREngine | None = None


def get_ocr_engine() -> OCREngine:
    """Get the configured OCR engine (singleton)."""
    global _engine
    if _engine is None:
        engine_name = settings.ocr_engine.lower()
        if engine_name == "rapidocr":
            try:
                _engine = RapidOCREngine()
                logger.info("OCR engine: RapidOCR (ONNX)")
            except ImportError:
                logger.warning("RapidOCR not available, falling back to Tesseract")
                _engine = TesseractEngine()
        else:
            _engine = TesseractEngine()
            logger.info("OCR engine: Tesseract")
    return _engine


def reset_ocr_engine() -> None:
    """Clear the singleton (for tests)."""
    global _engine
    _engine = None
