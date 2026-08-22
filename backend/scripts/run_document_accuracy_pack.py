#!/usr/bin/env python3
"""
Document accuracy pack — run SMB finance templates against fixture corpus.

Uses the same backend modules as production:
  extract_text() -> extract_fields() with template fields + instructions
  LLM: OpenAI gpt-4o via LLMTask.EXTRACTION

Usage (from backend/):
  python scripts/run_document_accuracy_pack.py --template all
  python scripts/run_document_accuracy_pack.py --template receipt
  python scripts/run_document_accuracy_pack.py --template invoice --subset benchmark
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Callable, Optional

BACKEND = Path(__file__).resolve().parents[1]
FIX = BACKEND / "tests" / "fixtures" / "documents"

sys.path.insert(0, str(BACKEND))

from app.services.documents.text_extractor import extract_text  # noqa: E402
from app.services.extraction.field_extractor import DocumentInput, extract_fields  # noqa: E402
from app.templates.registry import get_template_by_id  # noqa: E402

from accuracy_scoring import (  # noqa: E402
    DocResult,
    FieldScore,
    amount_match,
    date_match,
    min_count_match,
    print_report,
    score_fields,
    score_presence,
    vendor_match,
)

# --- Invoice fixtures (same as run_invoice_accuracy_pack.py) ---

INVOICE_GT = FIX / "invoices" / "invoicebenchmark_ground_truth"
INVOICE_BENCH = FIX / "invoices" / "invoicebenchmark"

INVOICE_GST: dict[str, dict[str, Any]] = {
    "gst-intra-cgst-sgst.pdf": {
        "vendor_name": "Acme Supplies Pvt Ltd",
        "invoice_date": "2026-01-15",
        "total_amount": 17700.0,
    },
    "gst-inter-igst.pdf": {
        "vendor_name": "Acme Supplies Pvt Ltd",
        "invoice_date": "2026-01-20",
        "total_amount": 20650.0,
    },
    "gst-b2c-retail.pdf": {
        "vendor_name": "Quick Retail LLP",
        "invoice_date": "2026-02-05",
        "total_amount": 1344.0,
    },
    "gst-intra-cgst-sgst.jpg": {
        "vendor_name": "Acme Supplies Pvt Ltd",
        "invoice_date": "2026-01-15",
        "total_amount": 17700.0,
    },
    "gst-inter-igst.jpg": {
        "vendor_name": "Acme Supplies Pvt Ltd",
        "invoice_date": "2026-01-20",
        "total_amount": 20650.0,
    },
}

INVOICE_MATCHERS = {
    "vendor_name": vendor_match,
    "invoice_date": date_match,
    "total_amount": amount_match,
}

# --- Receipt fixtures ---

RECEIPT_MATCHERS = {
    "merchant_name": vendor_match,
    "receipt_date": date_match,
    "total_amount": amount_match,
}

NOVUS_RECEIPT = {
    "merchant_name": "Meridian Supply Co.",
    "receipt_date": "2026-01-20",
    "total_amount": 773.61,
}

# --- Purchase order fixtures ---

PO_MATCHERS = {
    "po_number": lambda e, a: (str(e).upper() in str(a).upper(), "" if str(e).upper() in str(a).upper() else f"expected {e!r}, got {a!r}"),
    "vendor_name": vendor_match,
    "buyer_name": vendor_match,
    "po_date": date_match,
    "total_amount": amount_match,
}

NOVUS_PO = {
    "po_number": "PO-4471",
    "vendor_name": "Meridian Supply Co.",
    "buyer_name": "Brightside Cafe Group",
    "po_date": "2026-01-14",
    "total_amount": 773.61,
}

# --- Bank statement fixtures ---

BANK_MATCHERS = {
    "account_holder": vendor_match,
    "opening_balance": amount_match,
    "closing_balance": amount_match,
}

BANK_SYNTHETIC: dict[str, dict[str, Any]] = {
    "sample-inr-statement.pdf": {
        "account_holder": "Widget Industries Pvt Ltd",
        "opening_balance": 125000.0,
        "closing_balance": 55360.0,
        "transactions": 6,
    },
    "sample-usd-statement.pdf": {
        "account_holder": "Acme Corporation",
        "opening_balance": 42150.0,
        "closing_balance": 27928.70,
        "transactions": 5,
    },
    "sample-inr-statement.jpg": {
        "account_holder": "Widget Industries Pvt Ltd",
        "opening_balance": 125000.0,
        "closing_balance": 55360.0,
        "transactions": 4,  # OCR may miss rows
    },
    "sample-usd-statement.jpg": {
        "account_holder": "Acme Corporation",
        "opening_balance": 42150.0,
        "closing_balance": 27928.70,
        "transactions": 3,
    },
}

BANK_PRESENCE_FIELDS = ("account_holder", "closing_balance", "transactions")


def _invoice_paths(subset: str) -> list[tuple[Path, Optional[dict[str, Any]]]]:
    items: list[tuple[Path, Optional[dict[str, Any]]]] = []
    if subset in ("all", "benchmark"):
        for pdf in sorted(INVOICE_BENCH.glob("*.pdf")):
            items.append((pdf, None))
    if subset in ("all", "gst"):
        for name, exp in INVOICE_GST.items():
            p = (
                FIX / "invoices" / "gst" / name
                if name.endswith(".pdf")
                else FIX / "invoices" / "ocr" / name
            )
            if p.exists():
                items.append((p, exp))
    if subset == "all":
        for rel in (
            "invoices/ocr/microsoft-sample-invoice.jpg",
            "invoices/ocr/pdfcrowd-acme-invoice.jpg",
            "invoices/ocr/invoicebenchmark/INV-2026-0001.png",
        ):
            p = FIX / rel
            if p.exists():
                items.append((p, None))
    return items


def _invoice_expected(path: Path, override: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    if override is not None:
        return override
    if path.stem.startswith("INV-"):
        gt_path = INVOICE_GT / f"{path.stem}.json"
        if gt_path.exists():
            with open(gt_path) as f:
                gt = json.load(f)
            return {
                "vendor_name": gt.get("vendor"),
                "invoice_date": gt.get("date"),
                "total_amount": gt.get("total"),
            }
    return None


def _receipt_paths(limit: int) -> list[tuple[Path, Optional[dict[str, Any]]]]:
    items: list[tuple[Path, Optional[dict[str, Any]]]] = []
    sroie_dir = FIX / "receipts" / "sroie"
    gt_dir = FIX / "receipts" / "sroie_ground_truth"
    for jpg in sorted(sroie_dir.glob("sroie-*.jpg"))[:limit]:
        gt_path = gt_dir / f"{jpg.stem}.json"
        if gt_path.exists():
            with open(gt_path) as f:
                gt = json.load(f)
            ent = gt.get("entities", {})
            items.append(
                (
                    jpg,
                    {
                        "merchant_name": ent.get("company"),
                        "receipt_date": ent.get("date"),
                        "total_amount": ent.get("total"),
                    },
                )
            )
    for rel, exp in (
        ("receipts/novus-receipt.pdf", NOVUS_RECEIPT),
        ("receipts/ocr/novus-receipt.jpg", NOVUS_RECEIPT),
        ("receipts/azure-contoso-receipt.jpg", None),
    ):
        p = FIX / rel
        if p.exists():
            items.append((p, exp))
    return items


def _po_paths() -> list[tuple[Path, Optional[dict[str, Any]]]]:
    items: list[tuple[Path, Optional[dict[str, Any]]]] = []
    for rel in (
        "purchase_orders/novus-purchase-order.pdf",
        "purchase_orders/ocr/novus-purchase-order.jpg",
    ):
        p = FIX / rel
        if p.exists():
            items.append((p, NOVUS_PO))
    return items


def _bank_paths() -> list[tuple[Path, Optional[dict[str, Any]]]]:
    items: list[tuple[Path, Optional[dict[str, Any]]]] = []
    for name, exp in BANK_SYNTHETIC.items():
        if name.endswith(".pdf"):
            p = FIX / "bank_statements" / name
        else:
            p = FIX / "bank_statements" / "ocr" / name
        if p.exists():
            items.append((p, exp))
    # Representative real-layout / scanned samples (presence + min transactions)
    for rel in (
        "bank_statements/bankstatemently/bsb-001-statement.pdf",
        "bank_statements/indian_synthetic/train__India_Bank_Statement_Scanned_Type1__00001.pdf",
        "bank_statements/indian_synthetic/train__India_Bank_Statement_Digital_Type1__00001.pdf",
    ):
        p = FIX / rel
        if p.exists():
            items.append((p, {"transactions": 1}))  # min 1 txn + presence fields added at score time
    return items


async def _process_one(
    path: Path,
    template_id: str,
    expected: Optional[dict[str, Any]],
    matchers: dict[str, Callable],
    presence_fields: tuple[str, ...],
) -> DocResult:
    template = get_template_by_id(template_id)
    if template is None:
        return DocResult(path=path, template_id=template_id, text_method="error", text_len=0, error=f"unknown template {template_id}")

    try:
        text_result = await extract_text(path)
        if text_result.error_message or len(text_result.text.strip()) < 20:
            return DocResult(
                path=path,
                template_id=template_id,
                text_method=text_result.method,
                text_len=len(text_result.text),
                error=text_result.error_message or "insufficient text extracted",
            )

        docs = await extract_fields(
            [DocumentInput(document_id=path.stem, text=text_result.text, filename=path.name)],
            fields=template.fields,
            instructions=template.extraction_instructions,
        )
        fields = docs[0].fields if docs else {}

        if expected is None:
            return DocResult(
                path=path,
                template_id=template_id,
                text_method=text_result.method,
                text_len=len(text_result.text),
                scores=score_presence(presence_fields, fields),
            )

        # Bank real-layout docs: presence + minimum transaction rows
        if template_id == "bank_statement" and "account_holder" not in expected:
            txn_min = int(expected.get("transactions", 1))
            scores = score_presence(("account_holder", "closing_balance"), fields)
            ok, note = min_count_match(txn_min, fields.get("transactions"))
            scores.append(
                FieldScore(
                    field="transactions",
                    expected=f">={txn_min} rows",
                    actual=len(fields.get("transactions") or []),
                    ok=ok,
                    note=note,
                )
            )
            return DocResult(
                path=path,
                template_id=template_id,
                text_method=text_result.method,
                text_len=len(text_result.text),
                scores=scores,
            )

        active_matchers = matchers
        if template_id == "bank_statement":
            active_matchers = {
                **BANK_MATCHERS,
                "transactions": lambda e, a: min_count_match(e, a),
            }

        return DocResult(
            path=path,
            template_id=template_id,
            text_method=text_result.method,
            text_len=len(text_result.text),
            scores=score_fields(expected, fields, active_matchers),
        )
    except Exception as exc:
        return DocResult(path=path, template_id=template_id, text_method="error", text_len=0, error=str(exc))


async def run_pack(
    template_id: str,
    paths: list[tuple[Path, Optional[dict[str, Any]]]],
    matchers: dict,
    presence_fields: tuple[str, ...],
    expected_fn: Optional[Callable[[Path, Optional[dict]], Optional[dict]]] = None,
) -> list[DocResult]:
    results: list[DocResult] = []
    for path, override in paths:
        expected = expected_fn(path, override) if expected_fn else override
        print(f"  [{template_id}] → {path.relative_to(FIX)}", flush=True)
        results.append(await _process_one(path, template_id, expected, matchers, presence_fields))
    return results


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--template",
        choices=("all", "invoice", "receipt", "purchase_order", "bank_statement"),
        default="all",
    )
    parser.add_argument("--subset", choices=("all", "benchmark", "gst"), default="all", help="Invoice only")
    parser.add_argument("--receipt-limit", type=int, default=15, help="Max SROIE receipts to run")
    args = parser.parse_args()

    all_results: list[DocResult] = []
    exit_code = 0

    if args.template in ("all", "invoice"):
        paths = _invoice_paths(args.subset)
        print(f"\nInvoice pack: {len(paths)} fixtures")
        results = await run_pack(
            "invoice",
            paths,
            INVOICE_MATCHERS,
            ("vendor_name", "invoice_date", "total_amount"),
            _invoice_expected,
        )
        print_report(results, "Invoice accuracy")
        all_results.extend(results)

    if args.template in ("all", "receipt"):
        paths = _receipt_paths(args.receipt_limit)
        print(f"\nReceipt pack: {len(paths)} fixtures")
        results = await run_pack(
            "receipt",
            paths,
            RECEIPT_MATCHERS,
            ("merchant_name", "receipt_date", "total_amount"),
        )
        print_report(results, "Receipt accuracy")
        all_results.extend(results)

    if args.template in ("all", "purchase_order"):
        paths = _po_paths()
        print(f"\nPurchase order pack: {len(paths)} fixtures")
        results = await run_pack(
            "purchase_order",
            paths,
            PO_MATCHERS,
            ("po_number", "vendor_name", "total_amount"),
        )
        print_report(results, "Purchase order accuracy")
        all_results.extend(results)

    if args.template in ("all", "bank_statement"):
        paths = _bank_paths()
        print(f"\nBank statement pack: {len(paths)} fixtures")
        results = await run_pack(
            "bank_statement",
            paths,
            BANK_MATCHERS,
            BANK_PRESENCE_FIELDS,
        )
        print_report(results, "Bank statement accuracy")
        all_results.extend(results)

    if args.template == "all":
        passed = sum(1 for r in all_results if r.passed)
        print(f"\n=== Overall: {passed}/{len(all_results)} docs passed ===")

    if not all(r.passed for r in all_results):
        exit_code = 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
