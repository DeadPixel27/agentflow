"""
Layout-preserving text extraction using Docling (IBM, open-source).

WHY: VAREX (CVPR 2026) showed that upgrading raw text to layout-preserving
text gives +3 to +18pp accuracy gain - more than switching to image input.
Docling converts PDFs to structured markdown with table detection.

WHEN TO USE:
- Digital PDFs (embedded text) -> Docling gives markdown with tables preserved
- Scanned PDFs -> Fall back to OCR (Docling needs embedded text layer)
- Images -> Fall back to OCR
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from app.config import settings

logger = logging.getLogger("layout")


def extract_layout_text(file_path: Path) -> Optional[str]:
    """
    Extract layout-preserving text from a PDF using Docling.

    Returns markdown string if successful, None if Docling is unavailable
    or the PDF is scanned (no embedded text).
    """
    if not settings.use_layout_preservation:
        return None

    if file_path.suffix.lower() != ".pdf":
        return None

    try:
        from docling.document_converter import DocumentConverter

        converter = DocumentConverter()
        result = converter.convert(str(file_path))

        # Export as markdown - preserves tables, headers, structure
        markdown = result.document.export_to_markdown()

        if not markdown or len(markdown.strip()) < 50:
            logger.info(
                "Docling produced sparse text for %s, falling back to OCR",
                file_path.name,
            )
            return None

        logger.info(
            "Layout extraction: %s -> %d chars markdown",
            file_path.name,
            len(markdown),
        )
        return markdown.strip()

    except ImportError:
        logger.warning("Docling not installed - pip install docling")
        return None
    except Exception as e:
        logger.warning("Docling extraction failed for %s: %s", file_path.name, e)
        return None
