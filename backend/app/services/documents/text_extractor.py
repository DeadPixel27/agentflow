"""
Document Text Extraction — pulls text from PDFs and images.

STRATEGIES (tried in order for PDFs):

1. Docling — layout-preserving markdown (tables, headers) when enabled
2. PyMuPDF (fitz) — for DIGITAL PDFs with selectable text
3. OCR (RapidOCR or Tesseract) — for images and scanned PDFs

HOW WE DECIDE:
   Try Docling (if enabled), then PyMuPDF. If we get meaningful text → done.
   If text is empty/too short → fall back to OCR.
"""

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF
from PIL import Image

from app.services.documents.ocr_engines import get_ocr_engine

logger = logging.getLogger("ocr")

# Minimum characters to consider PyMuPDF extraction successful
MIN_TEXT_LENGTH = 50

# Resize large images before OCR — much faster, barely affects accuracy
MAX_OCR_DIMENSION = 1500

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}


@dataclass
class ExtractionResult:
    """Result of text extraction from a document."""

    text: str
    method: str  # "docling" | "pymupdf" | "rapidocr" | "tesseract" | "none" | "error"
    error_message: Optional[str] = None


async def extract_text(file_path: Path) -> ExtractionResult:
    """
    Public entry point — runs extraction in a background thread.

    WHY async + thread:
      OCR and PDF parsing are CPU-heavy and synchronous.
      Running them on the main thread would freeze the entire API.
      asyncio.to_thread() offloads the work so other requests can be handled.
    """
    try:
        text, method = await asyncio.to_thread(_extract_text_sync, file_path)
        return ExtractionResult(text=text, method=method)
    except RuntimeError as e:
        return ExtractionResult(text="", method="error", error_message=str(e))


def _extract_text_sync(file_path: Path) -> tuple[str, str]:
    """Synchronous extraction — called inside a thread pool."""
    ext = file_path.suffix.lower()

    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    if ext in IMAGE_EXTENSIONS:
        return extract_text_from_image(file_path)

    return "", "none"


def extract_text_from_pdf(file_path: Path) -> tuple[str, str]:
    """
    Extract text from a PDF using layout-preserving extraction (Docling),
    falling back to PyMuPDF, then OCR.

    Returns: (extracted_text, method_used)
    """
    from app.services.documents.layout_extractor import extract_layout_text

    layout_text = extract_layout_text(file_path)
    if layout_text:
        return layout_text, "docling"

    doc = fitz.open(file_path)
    pages_text: list[str] = []

    for page in doc:
        pages_text.append(page.get_text())

    doc.close()
    text = "\n".join(pages_text).strip()

    if len(text) >= MIN_TEXT_LENGTH:
        return text, "pymupdf"

    # Scanned PDF — try OCR on each page
    return _ocr_pdf(file_path)


def _ocr_pdf(file_path: Path) -> tuple[str, str]:
    """Render each PDF page as an image, then OCR it."""
    engine = get_ocr_engine()

    doc = fitz.open(file_path)
    pages_text: list[str] = []

    for page in doc:
        # Render page at 2x resolution for better OCR accuracy
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        pages_text.append(engine.ocr_image(img))

    doc.close()
    return "\n".join(pages_text).strip(), engine.name


def _prepare_image_for_ocr(img: Image.Image) -> Image.Image:
    """Shrink oversized images so OCR runs faster."""
    w, h = img.size
    longest = max(w, h)
    if longest <= MAX_OCR_DIMENSION:
        return img

    scale = MAX_OCR_DIMENSION / longest
    new_size = (int(w * scale), int(h * scale))
    logger.info("Resizing %dx%d → %dx%d for faster OCR", w, h, *new_size)
    return img.resize(new_size, Image.Resampling.LANCZOS)


def extract_text_from_image(file_path: Path) -> tuple[str, str]:
    """OCR a single image file."""
    engine = get_ocr_engine()

    img = Image.open(file_path)
    logger.info("OCR started: %s (%dx%d)", file_path.name, *img.size)
    img = _prepare_image_for_ocr(img)
    text = engine.ocr_image(img)
    return text.strip(), engine.name
