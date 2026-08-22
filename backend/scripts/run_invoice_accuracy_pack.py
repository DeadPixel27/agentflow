#!/usr/bin/env python3
"""
Invoice accuracy pack — run invoice template on priority fixtures and score key fields.

Usage (from backend/):
  python scripts/run_invoice_accuracy_pack.py
  python scripts/run_invoice_accuracy_pack.py --subset benchmark
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Optional

BACKEND = Path(__file__).resolve().parents[1]
FIX = BACKEND / "tests" / "fixtures" / "documents"
GT_DIR = FIX / "invoices" / "invoicebenchmark_ground_truth"
BENCH_DIR = FIX / "invoices" / "invoicebenchmark"

sys.path.insert(0, str(BACKEND))

from app.services.documents.text_extractor import extract_text  # noqa: E402
from app.services.extraction.field_extractor import DocumentInput, extract_fields  # noqa: E402
from app.templates.invoice import INVOICE_TEMPLATE  # noqa: E402

KEY_FIELDS = ("vendor_name", "invoice_date", "total_amount")

GST_EXPECTED: dict[str, dict[str, Any]] = {
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


@dataclass
class FieldScore:
    field: str
    expected: Any
    actual: Any
    ok: bool
    note: str = ""


@dataclass
class DocResult:
    path: Path
    text_method: str
    text_len: int
    scores: list[FieldScore] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def passed(self) -> bool:
        return self.error is None and all(s.ok for s in self.scores)


def _norm_vendor(s: Any) -> str:
    if s is None:
        return ""
    t = str(s).lower().strip()
    t = re.sub(r"[^\w\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _vendor_match(expected: Any, actual: Any, threshold: float = 0.72) -> tuple[bool, str]:
    e, a = _norm_vendor(expected), _norm_vendor(actual)
    if not e and not a:
        return True, ""
    if not e or not a:
        return False, f"expected {expected!r}, got {actual!r}"
    if e in a or a in e:
        return True, ""
    ratio = SequenceMatcher(None, e, a).ratio()
    ok = ratio >= threshold
    note = f"similarity={ratio:.2f}" if not ok else ""
    return ok, note


def _parse_amount(v: Any) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    s = re.sub(r"[^\d.\-]", "", s.replace(",", ""))
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _amount_match(expected: Any, actual: Any, rel_tol: float = 0.005) -> tuple[bool, str]:
    e, a = _parse_amount(expected), _parse_amount(actual)
    if e is None and a is None:
        return True, ""
    if e is None or a is None:
        return False, f"expected {expected!r}, got {actual!r}"
    if e == 0:
        ok = abs(a) < 0.01
    else:
        ok = abs(a - e) <= max(0.01, abs(e) * rel_tol)
    return ok, "" if ok else f"expected {e}, got {a}"


def _parse_date(v: Any) -> Optional[str]:
    if v is None:
        return None
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s[:10], fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return s[:10] if len(s) >= 10 else s


def _date_match(expected: Any, actual: Any) -> tuple[bool, str]:
    e, a = _parse_date(expected), _parse_date(actual)
    if not e and not a:
        return True, ""
    ok = e == a
    return ok, "" if ok else f"expected {expected!r}, got {actual!r}"


def _ground_truth_to_expected(gt: dict[str, Any]) -> dict[str, Any]:
    return {
        "vendor_name": gt.get("vendor"),
        "invoice_date": gt.get("date"),
        "total_amount": gt.get("total"),
    }


def _score_fields(expected: dict[str, Any], actual: dict[str, Any]) -> list[FieldScore]:
    scores: list[FieldScore] = []
    matchers = {
        "vendor_name": _vendor_match,
        "invoice_date": _date_match,
        "total_amount": _amount_match,
    }
    for fname in KEY_FIELDS:
        exp = expected.get(fname)
        act = actual.get(fname)
        ok, note = matchers[fname](exp, act)
        scores.append(FieldScore(field=fname, expected=exp, actual=act, ok=ok, note=note))
    return scores


def _collect_paths(subset: str) -> list[tuple[Path, Optional[dict[str, Any]]]]:
    items: list[tuple[Path, Optional[dict[str, Any]]]] = []

    if subset in ("all", "benchmark"):
        for pdf in sorted(BENCH_DIR.glob("*.pdf")):
            items.append((pdf, None))

    if subset in ("all", "gst"):
        for name, exp in GST_EXPECTED.items():
            if name.endswith(".pdf"):
                p = FIX / "invoices" / "gst" / name
            else:
                p = FIX / "invoices" / "ocr" / name
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


def _expected_for_path(path: Path, override: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    if override is not None:
        return override
    stem = path.stem
    if stem.startswith("INV-"):
        gt_path = GT_DIR / f"{stem}.json"
        if gt_path.exists():
            with open(gt_path) as f:
                return _ground_truth_to_expected(json.load(f))
    return None


async def _process_one(path: Path, expected: Optional[dict[str, Any]]) -> DocResult:
    try:
        text_result = await extract_text(path)
        if text_result.error_message or len(text_result.text.strip()) < 20:
            return DocResult(
                path=path,
                text_method=text_result.method,
                text_len=len(text_result.text),
                error=text_result.error_message or "insufficient text extracted",
            )

        docs = await extract_fields(
            [DocumentInput(document_id=path.stem, text=text_result.text, filename=path.name)],
            fields=INVOICE_TEMPLATE.fields,
            instructions=INVOICE_TEMPLATE.extraction_instructions,
        )
        fields = docs[0].fields if docs else {}

        if expected is None:
            scores = []
            for fname in KEY_FIELDS:
                val = fields.get(fname)
                ok = val is not None and str(val).strip() != ""
                scores.append(
                    FieldScore(field=fname, expected="(present)", actual=val, ok=ok, note="no GT")
                )
            return DocResult(path=path, text_method=text_result.method, text_len=len(text_result.text), scores=scores)

        return DocResult(
            path=path,
            text_method=text_result.method,
            text_len=len(text_result.text),
            scores=_score_fields(expected, fields),
        )
    except Exception as exc:
        return DocResult(path=path, text_method="error", text_len=0, error=str(exc))


def _print_report(results: list[DocResult]) -> None:
    scored = [r for r in results if r.scores and r.scores[0].note != "no GT"]
    informational = [r for r in results if r.scores and r.scores[0].note == "no GT"]
    failed = [r for r in results if not r.passed]

    print("\n=== Invoice accuracy pack ===\n")
    for r in results:
        rel = r.path.relative_to(FIX)
        status = "PASS" if r.passed else "FAIL"
        print(f"[{status}] {rel}  (text: {r.text_method}, {r.text_len} chars)")
        if r.error:
            print(f"       ERROR: {r.error}")
        for s in r.scores:
            mark = "ok" if s.ok else "MISS"
            extra = f" — {s.note}" if s.note else ""
            print(f"       {mark:4} {s.field}: expected={s.expected!r} actual={s.actual!r}{extra}")
        print()

    if scored:
        total_checks = sum(len(r.scores) for r in scored)
        ok_checks = sum(1 for r in scored for s in r.scores if s.ok)
        docs_ok = sum(1 for r in scored if r.passed)
        print(
            f"Scored: {docs_ok}/{len(scored)} docs fully correct, "
            f"{ok_checks}/{total_checks} field checks ({100 * ok_checks / total_checks:.1f}%)"
        )

    if informational:
        print(f"\nNo ground truth ({len(informational)} docs) — key fields present:")
        for r in informational:
            rel = r.path.relative_to(FIX)
            present = sum(1 for s in r.scores if s.ok)
            print(f"  {rel}: {present}/{len(KEY_FIELDS)} fields")

    if failed:
        print("\n--- Failures summary ---")
        by_field: dict[str, int] = {}
        for r in failed:
            for s in r.scores:
                if not s.ok:
                    by_field[s.field] = by_field.get(s.field, 0) + 1
        for fname, count in sorted(by_field.items(), key=lambda x: -x[1]):
            print(f"  {fname}: {count} miss(es)")


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--subset",
        choices=("all", "benchmark", "gst"),
        default="all",
        help="Which fixture groups to run",
    )
    args = parser.parse_args()

    paths = _collect_paths(args.subset)
    if not paths:
        print("No fixtures found.", file=sys.stderr)
        return 1

    print(f"Running {len(paths)} invoice fixtures (subset={args.subset})...")
    results: list[DocResult] = []
    for path, override in paths:
        expected = _expected_for_path(path, override)
        rel = path.relative_to(FIX)
        print(f"  → {rel}", flush=True)
        results.append(await _process_one(path, expected))

    _print_report(results)
    return 0 if all(r.passed for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
