# Document accuracy corpus

Public/sample documents for template tuning and OCR regression. **Do not commit real customer or employer docs.**

See **[REAL_WORLD.md](./REAL_WORLD.md)** for what’s legally available vs what you must collect yourself.

## Layout

| Folder | Files | Use with template |
|--------|-------|-------------------|
| `invoices/` | PDF/JPG + `invoicebenchmark/` | `invoice` |
| `invoices/invoicebenchmark_ground_truth/` | JSON | Score vs extract output |
| `receipts/` | JPG/PDF + `sroie/` + `ocr/` | `receipt` |
| `receipts/sroie_ground_truth/` | JSON (`company`, `date`, `total`) | Score vs extract output |
| `invoices/ocr/` | JPG (rasterized + InvoiceBenchmark PNGs) | `invoice` — OCR path |
| `purchase_orders/ocr/` | JPG | `purchase_order` — OCR path |
| `bank_statements/ocr/` | JPG | `bank_statement` — OCR path |
| `purchase_orders/` | PDF | `purchase_order` |
| `invoices/gst/` | PDF (synthetic India GST) | `invoice` |
| `bank_statements/` | PDF (synthetic) | `bank_statement` |
| `bank_statements/bankstatemently/` | 5 benchmark PDFs (SG/US/NL/HK/CA layouts) | `bank_statement` |
| `bank_statements/indian_synthetic/` | 3 scanned + 3 digital India PDFs (HF) | `bank_statement` — **real scan OCR** |
| `edge_cases/` | PDF | Layout stress tests |

## Sources

- **Microsoft Azure samples** — invoice PDF/JPG, Contoso receipt JPG
- **PDFCrowd** — Acme consulting invoice
- **Novus Examples** — deterministic invoice/receipt/PO PDFs (CC0-style fixtures)
- **SampleFile** — multi-column PDF
- **InvoiceBenchmark** (HF: `jngb-labs/InvoiceBenchmark`) — 10 PDFs + JSON ground truth
- **SROIE** (HF: `jsdnrs/ICDAR2019-SROIE`, CC-BY-4.0) — 15 scanned receipt JPGs + entity JSON
- **Repo copies** — `nexora-sample-invoice.pdf`, `backend-test-invoice.pdf`
- **Synthetic GST + bank statements** — `python scripts/generate_document_fixtures.py` (PyMuPDF, no external downloads)

## Regenerate synthetic fixtures

```bash
cd backend
source .venv/bin/activate
python scripts/generate_document_fixtures.py
```

Writes `invoices/gst/*.pdf` (CGST+SGST, IGST, B2C) and `bank_statements/*.pdf` (INR + USD).

## Regenerate OCR / image fixtures

Most templates ship as **native PDFs** (text extract path). Receipts also have **real scans** (SROIE). For invoices, POs, and bank statements, generate JPGs that exercise the **OCR pipeline**:

```bash
cd backend
source .venv/bin/activate
python scripts/generate_ocr_fixtures.py
```

This script:
- Rasterizes key PDFs → JPG with light phone-scan degradation (`*/ocr/` folders)
- Downloads InvoiceBenchmark PNG twins (same JSON ground truth as `invoicebenchmark/`)

Real-world receipt OCR stress remains in `receipts/sroie/` (ICDAR dataset).

## Still optional (browser generators)

For fancier layouts, generate manually and drop into the folders above:

- **India GST** — [gstinvoices.in](https://gstinvoices.in/gst-invoice-template-pdf)
- **Bank statements** — [DocsLoop generator](https://docsloop.com/free-tools/bank-statement-generator)

## Scoring (receipt example)

Compare extract to `sroie_ground_truth/sroie-NNN.json`:

- `merchant_name` ↔ `entities.company`
- `receipt_date` ↔ `entities.date` (normalize to YYYY-MM-DD)
- `total_amount` ↔ `entities.total`

## Full accuracy pack (all SMB finance templates)

```bash
cd backend
python scripts/run_document_accuracy_pack.py --template all
```

Reports: [`DOCUMENT_ACCURACY_REPORT.md`](DOCUMENT_ACCURACY_REPORT.md), [`INVOICE_ACCURACY_REPORT.md`](INVOICE_ACCURACY_REPORT.md)

## InvoiceBenchmark scoring

Compare to `invoicebenchmark_ground_truth/INV-*.json`: `vendor`, `subtotal`, `total`, etc.
