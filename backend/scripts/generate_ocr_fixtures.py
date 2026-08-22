"""Build OCR/image fixtures from PDFs + optional HuggingFace PNG invoices.

Run from backend/: python scripts/generate_ocr_fixtures.py

- Rasterizes representative PDFs → JPG (simulates phone upload / scan path)
- Downloads InvoiceBenchmark PNG twins (same ground truth as existing JSON)
- Does NOT pull full SROIE-scale datasets (use receipts/sroie/ for that)
"""

from __future__ import annotations

import io
import shutil
from pathlib import Path

import fitz  # pymupdf
from PIL import Image, ImageEnhance, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "documents"
HF_HOME = ROOT / ".hf_cache"

# PDF relative to FIX → output JPG folder/name
RASTERIZE: list[tuple[str, str]] = [
    ("invoices/microsoft-sample-invoice.pdf", "invoices/ocr/microsoft-sample-invoice.jpg"),
    ("invoices/pdfcrowd-acme-invoice.pdf", "invoices/ocr/pdfcrowd-acme-invoice.jpg"),
    ("invoices/gst/gst-intra-cgst-sgst.pdf", "invoices/ocr/gst-intra-cgst-sgst.jpg"),
    ("invoices/gst/gst-inter-igst.pdf", "invoices/ocr/gst-inter-igst.jpg"),
    ("purchase_orders/novus-purchase-order.pdf", "purchase_orders/ocr/novus-purchase-order.jpg"),
    ("bank_statements/sample-inr-statement.pdf", "bank_statements/ocr/sample-inr-statement.jpg"),
    ("bank_statements/sample-usd-statement.pdf", "bank_statements/ocr/sample-usd-statement.jpg"),
    ("receipts/novus-receipt.pdf", "receipts/ocr/novus-receipt.jpg"),
]


def _degrade_for_ocr(img: Image.Image) -> Image.Image:
    """Light phone-scan stress: slight blur + contrast (not destroyed)."""
    img = img.convert("RGB")
    w, h = img.size
    img = img.resize((int(w * 0.85), int(h * 0.85)), Image.Resampling.LANCZOS)
    img = img.rotate(1.2, expand=True, fillcolor=(255, 255, 255))
    img = img.filter(ImageFilter.GaussianBlur(radius=0.6))
    img = ImageEnhance.Contrast(img).enhance(1.15)
    return img


def pdf_to_jpg(pdf_path: Path, jpg_path: Path, *, dpi: int = 150, degrade: bool = True) -> None:
    jpg_path.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf_path)
    page = doc[0]
    pix = page.get_pixmap(dpi=dpi, alpha=False)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    doc.close()
    if degrade:
        img = _degrade_for_ocr(img)
    img.save(jpg_path, "JPEG", quality=82)
    print("raster", jpg_path.relative_to(FIX))


def download_invoicebenchmark_pngs(limit: int = 10) -> None:
    import os

    os.environ.setdefault("HF_HOME", str(HF_HOME))
    from huggingface_hub import hf_hub_download, list_repo_files

    repo = "jngb-labs/InvoiceBenchmark"
    dest = FIX / "invoices" / "ocr" / "invoicebenchmark"
    dest.mkdir(parents=True, exist_ok=True)
    pngs = sorted(f for f in list_repo_files(repo, repo_type="dataset") if f.startswith("output/png/"))[:limit]
    for f in pngs:
        local = hf_hub_download(repo, f, repo_type="dataset")
        name = Path(f).name
        shutil.copy2(local, dest / name)
        print("png", dest / name)


def main() -> None:
    for rel_pdf, rel_jpg in RASTERIZE:
        pdf_path = FIX / rel_pdf
        if not pdf_path.is_file():
            print("skip missing", rel_pdf)
            continue
        pdf_to_jpg(pdf_path, FIX / rel_jpg)

    download_invoicebenchmark_pngs()
    print("Done — OCR fixtures under", FIX)


if __name__ == "__main__":
    main()
