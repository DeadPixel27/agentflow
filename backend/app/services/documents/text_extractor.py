"""
Document Text Extraction — pulls text from PDFs and images.

TWO STRATEGIES (the planner will pick later; for now we auto-detect):

1. PyMuPDF (fitz) — for DIGITAL PDFs
   - PDFs created from Word/Excel/etc. have selectable text embedded
   - Fast, free, no OCR needed

2. Tesseract OCR — for IMAGES and SCANNED PDFs
   - Photos, screenshots, scanned documents = just pixels, no text layer
   - Tesseract reads the pixels and guesses the characters
   - Slower, but necessary when there's no embedded text

HOW WE DECIDE:
   Try PyMuPDF first. If we get meaningful text → done.
   If text is empty/too short → fall back to OCR.
"""

import asyncio
import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF
import pytesseract
from PIL import Image

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
    method: str  # "pymupdf" | "tesseract" | "none" | "error"
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


def _check_tesseract_installed() -> None:
    """Tesseract is a system program, not a Python package."""
    if shutil.which("tesseract") is None:
        raise RuntimeError(
            "Tesseract is not installed. Install it with:\n"
            "  macOS:   brew install tesseract\n"
            "  Ubuntu:  sudo apt install tesseract-ocr\n"
            "  Windows: https://github.com/UB-Mannheim/tesseract/wiki"
        )


def extract_text_from_pdf(file_path: Path) -> tuple[str, str]:
    """
    Extract text from a PDF using PyMuPDF.

    Returns: (extracted_text, method_used)
    """
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
    _check_tesseract_installed()

    doc = fitz.open(file_path)
    pages_text: list[str] = []

    for page in doc:
        # Render page at 2x resolution for better OCR accuracy
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        pages_text.append(pytesseract.image_to_string(img))

    doc.close()
    return "\n".join(pages_text).strip(), "tesseract"


def _prepare_image_for_ocr(img: Image.Image) -> Image.Image:
    """Shrink oversized images so Tesseract runs faster."""
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
    _check_tesseract_installed()

    img = Image.open(file_path)
    logger.info("OCR started: %s (%dx%d)", file_path.name, *img.size)
    img = _prepare_image_for_ocr(img)
    text = pytesseract.image_to_string(img)
    return text.strip(), "tesseract"
