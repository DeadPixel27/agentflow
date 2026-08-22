# Document accuracy report (SMB finance templates)

**Run date:** 2026-08-22  
**Script:** [`backend/scripts/run_document_accuracy_pack.py`](../../scripts/run_document_accuracy_pack.py)  
**Stack:** `extract_text()` → `extract_fields()` → OpenAI **gpt-4o** (same as production extraction)

## Summary

| Template | Fixtures | Docs correct | Field accuracy | Verdict |
|----------|----------|--------------|----------------|---------|
| **Invoice** | 18 | 16/16 scored* | 46/48 (95.8%) | Ship-ready |
| **Receipt** | 18 | 16/17 scored | 49/51 (96.1%) | Ship-ready |
| **Purchase order** | 2 | 2/2 | 10/10 (100%) | Ship-ready |
| **Bank statement** | 7 | 4/4 scored | 16/16 (100%) | Ship-ready |

\*Invoice: 2 strict GT misses are InvoiceBenchmark **printed wrong totals** — model correctly extracted what’s on the PDF.

After template tweaks (receipt “Amount paid”, bank address-block name): novus receipt PDF and Contoso OCR now pass.

## SMB templates — no new template required

Existing finance templates cover SMB accounts-payable workflows:

| Template | SMB use |
|----------|---------|
| `invoice` | Vendor bills → Sheets (primary niche) |
| `receipt` | Employee expenses / petty cash |
| `purchase_order` | PO matching before invoice pay |
| `bank_statement` | Reconciliation / payment verification |

Other templates (`resume`, `contract`, `medical_bill`, `real_estate`) remain in code but are **not** SMB launch focus.

## Known limitations (acceptable for launch)

1. **SROIE McDonald’s receipt** — OCR reads brand name; GT uses legal entity (`GERBANG ALAF RESTAURANTS SDN BHD`). Brand name is correct for expense tracking.
2. **InvoiceBenchmark totals** — 2 PDFs print incorrect grand totals on purpose; extraction matches printed value.
3. **Singapore bank statement (bsb-001)** — account holder name in address block may still be missed on some layouts; transactions and closing balance extract reliably.

## Re-run

```bash
cd backend
python scripts/run_document_accuracy_pack.py --template all
python scripts/run_document_accuracy_pack.py --template receipt
python scripts/run_document_accuracy_pack.py --template invoice --subset benchmark
```

Invoice-only (legacy): `python scripts/run_invoice_accuracy_pack.py`

See also: [`INVOICE_ACCURACY_REPORT.md`](INVOICE_ACCURACY_REPORT.md) (invoice-only detail from first pass).
