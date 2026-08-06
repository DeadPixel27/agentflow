"""Tests for upload content validation."""

import pytest

from app.models.domain.document import InvalidUploadError
from app.persistence.documents.validation import validate_file_content


def test_validate_pdf_magic_bytes():
    validate_file_content(b"%PDF-1.4 sample", ".pdf")


def test_validate_png_magic_bytes():
    png_header = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
    validate_file_content(png_header, ".png")


def test_rejects_oversized_file():
    oversized = b"x" * (10 * 1024 * 1024 + 1)
    with pytest.raises(InvalidUploadError, match="too large"):
        validate_file_content(oversized, ".pdf")


def test_rejects_mismatched_extension():
    with pytest.raises(InvalidUploadError, match="does not match"):
        validate_file_content(b"not a real pdf", ".pdf")
