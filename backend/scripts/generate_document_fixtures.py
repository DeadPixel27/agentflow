"""Generate synthetic GST invoice and bank statement PDFs for template/OCR fixtures.

Run from backend/: python scripts/generate_document_fixtures.py
Uses PyMuPDF (already in requirements) — no browser, no HuggingFace cache.
"""

from __future__ import annotations

from pathlib import Path

import fitz  # pymupdf

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "tests" / "fixtures" / "documents"


def _write_pdf(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4
    y = 50
    for line in lines:
        page.insert_text((50, y), line, fontsize=10, fontname="helv")
        y += 14
        if y > 800:
            page = doc.new_page(width=595, height=842)
            y = 50
    doc.save(path)
    doc.close()


def gst_intra_state() -> None:
    lines = [
        "TAX INVOICE",
        "SAMPLE — FOR TESTING ONLY",
        "",
        "Supplier: Acme Supplies Pvt Ltd",
        "Address: 12 MG Road, Bengaluru, Karnataka 560001",
        "GSTIN: 29AABCA1234A1Z5",
        "Invoice No: GST/2026/0042    Date: 15/01/2026",
        "",
        "Bill To: Widget Industries Pvt Ltd",
        "Address: 45 Industrial Area, Bengaluru, Karnataka 560058",
        "GSTIN: 29AABFW5678B2Z9",
        "Place of Supply: Karnataka (29)",
        "",
        "#  Description          HSN    Qty  Rate     Taxable   CGST  SGST   Total",
        "1  Office Chair         9401   2    4500.00  9000.00   810   810   10620.00",
        "2  Desk Lamp            9405   5    1200.00  6000.00   540   540    7080.00",
        "",
        "Taxable Value: 15000.00",
        "CGST @ 9%: 1350.00",
        "SGST @ 9%: 1350.00",
        "Grand Total: 17700.00",
        "Amount in words: Seventeen Thousand Seven Hundred Rupees Only",
        "",
        "Bank: HDFC Bank  A/C: 50200012345678  IFSC: HDFC0001234",
    ]
    _write_pdf(FIX / "invoices" / "gst" / "gst-intra-cgst-sgst.pdf", lines)


def gst_inter_state() -> None:
    lines = [
        "TAX INVOICE",
        "SAMPLE — FOR TESTING ONLY",
        "",
        "Supplier: Acme Supplies Pvt Ltd",
        "Address: 12 MG Road, Bengaluru, Karnataka 560001",
        "GSTIN: 29AABCA1234A1Z5",
        "Invoice No: GST/2026/0088    Date: 20/01/2026",
        "",
        "Bill To: Delhi Trading Co",
        "Address: 88 Connaught Place, New Delhi 110001",
        "GSTIN: 07AABCD9999C1Z2",
        "Place of Supply: Delhi (07)",
        "",
        "#  Description          HSN    Qty  Rate     Taxable   IGST 18%   Total",
        "1  Laptop Stand         8473   10   850.00   8500.00   1530.00  10030.00",
        "2  USB-C Hub            8544   20   450.00   9000.00   1620.00  10620.00",
        "",
        "Taxable Value: 17500.00",
        "IGST @ 18%: 3150.00",
        "Grand Total: 20650.00",
        "Amount in words: Twenty Thousand Six Hundred Fifty Rupees Only",
        "",
        "PO Reference: PO-DL-2026-119",
    ]
    _write_pdf(FIX / "invoices" / "gst" / "gst-inter-igst.pdf", lines)


def gst_simple_b2c() -> None:
    lines = [
        "TAX INVOICE",
        "SAMPLE — FOR TESTING ONLY",
        "",
        "Supplier: Quick Retail LLP",
        "GSTIN: 27AABFQ1111F1Z8",
        "Invoice No: QR/26/0156    Date: 05/02/2026",
        "",
        "Customer: Walk-in (B2C)",
        "",
        "Item                  HSN    Qty   Rate    GST%   Amount",
        "Thermal Paper Roll    4809   10    120.00  12%    1344.00",
        "",
        "Subtotal: 1200.00",
        "CGST: 72.00  SGST: 72.00",
        "Total: 1344.00",
    ]
    _write_pdf(FIX / "invoices" / "gst" / "gst-b2c-retail.pdf", lines)


def bank_statement() -> None:
    lines = [
        "SAMPLE BANK STATEMENT — NOT AN OFFICIAL DOCUMENT",
        "",
        "First National Bank",
        "Account Holder: Widget Industries Pvt Ltd",
        "Account Number: ****4567",
        "Statement Period: 01/01/2026 — 31/01/2026",
        "Currency: INR",
        "",
        "Opening Balance: 125000.00",
        "",
        "Date       Description                    Debit      Credit     Balance",
        "02/01/2026 NEFT IN - CLIENT PAYMENT                  45000.00   170000.00",
        "05/01/2026 UPI/ACME SUPPLIES              17700.00              152300.00",
        "12/01/2026 SALARY BATCH                   82000.00               70300.00",
        "18/01/2026 IMPS RENT                      35000.00               35300.00",
        "25/01/2026 NEFT IN - INVOICE #8842                   20650.00   55950.00",
        "28/01/2026 BANK CHARGES                     590.00               55360.00",
        "",
        "Closing Balance: 55360.00",
        "Total Credits: 65650.00    Total Debits: 135290.00",
    ]
    _write_pdf(FIX / "bank_statements" / "sample-inr-statement.pdf", lines)


def bank_statement_usd() -> None:
    lines = [
        "SAMPLE BANK STATEMENT — NOT AN OFFICIAL DOCUMENT",
        "",
        "Global Commerce Bank",
        "Account Holder: Acme Corporation",
        "Account Number: 1234567890",
        "Statement Period: Jan 1, 2026 — Jan 31, 2026",
        "Currency: USD",
        "",
        "Opening Balance: 42,150.00",
        "",
        "Date       Description                    Debit       Credit      Balance",
        "01/05/2026 WIRE IN - GLOBALTECH INC                    31,703.70   73,853.70",
        "01/12/2026 ACH PAYROLL                      28,400.00               45,453.70",
        "01/18/2026 CHECK #1042                       2,500.00               42,953.70",
        "01/22/2026 WIRE OUT - VENDOR                           15,000.00   27,953.70",
        "01/30/2026 SERVICE FEE                          25.00               27,928.70",
        "",
        "Closing Balance: 27,928.70",
    ]
    _write_pdf(FIX / "bank_statements" / "sample-usd-statement.pdf", lines)


def main() -> None:
    gst_intra_state()
    gst_inter_state()
    gst_simple_b2c()
    bank_statement()
    bank_statement_usd()
    print(f"Wrote fixtures under {FIX}")


if __name__ == "__main__":
    main()
