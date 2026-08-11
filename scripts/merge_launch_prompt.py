#!/usr/bin/env python3
"""Merge OCR batch JSON files into BACKEND-LAUNCH-PROMPT.md."""

import json
from pathlib import Path
from typing import Optional, Set

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
OUT = DOCS / "BACKEND-LAUNCH-PROMPT.md"
MAX_LINE = 2239

# batch1 lines 1-762 are hallucinated (wrong document) — skip except known-good sparse lines
BATCH1_ALLOW = {1122, 1136, 1137, 1138, 1196, 1197, 1198, 1199}


def load_json(name: str) -> dict[str, str]:
    path = DOCS / name
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("lines", {})


def merge_lines(*sources: dict[str, str], skip_batch1_below: int = 763) -> dict[int, str]:
    merged: dict[int, str] = {}
    for i, src in enumerate(sources):
        for k, v in src.items():
            num = int(k)
            if i == 0 and "batch1" in str(sources):  # handled per-file below
                pass
            if num not in merged or len(v) > len(merged.get(num, "")):
                merged[num] = v
    return merged


def main() -> None:
    merged: dict[int, str] = {}

    def add(src: dict, *, min_line: int = 0, allow_below: Optional[Set[int]] = None) -> None:
        for k, v in src.items():
            num = int(k)
            if num < min_line and (allow_below is None or num not in allow_below):
                continue
            if num not in merged or len(v) > len(merged[num]):
                merged[num] = v

    # Load all batch files
    batch1 = load_json("BACKEND-LAUNCH-PROMPT-ocr-batch1.json")
    batch3 = load_json("BACKEND-LAUNCH-PROMPT-ocr-batch3.json")
    batch2 = load_json("BACKEND-LAUNCH-PROMPT-ocr-batch2.json")
    batch4 = load_json("BACKEND-LAUNCH-PROMPT-ocr-batch4.json")
    gap = load_json("BACKEND-LAUNCH-PROMPT-gap-fills.json")

    add(batch3)
    add(batch4)
    add(batch2)
    add(batch1, min_line=763, allow_below=BATCH1_ALLOW)
    add(gap)

    # Header note (prepended, not part of original line numbers)
    header = [
        "> Transcribed from `backend-launch-prompt/` screenshots (Aug 9, 2026).",
        "",
    ]

    lines_out: list[str] = []
    missing: list[int] = []
    for n in range(1, MAX_LINE + 1):
        if n in merged:
            lines_out.append(merged[n])
        else:
            lines_out.append("")
            missing.append(n)

    # Prepend transcription note after title line
    if lines_out and lines_out[0].startswith("# Backend Launch"):
        final = [lines_out[0], ""] + header + lines_out[1:]
    else:
        final = header + lines_out

    OUT.write_text("\n".join(final) + "\n", encoding="utf-8")

    covered = MAX_LINE - len(missing)
    print(f"Written {OUT}")
    print(f"Covered: {covered}/{MAX_LINE} lines ({100*covered/MAX_LINE:.1f}%)")
    print(f"Missing: {len(missing)} lines")
    if missing:
        # Show gap ranges
        ranges: list[tuple[int, int]] = []
        start = missing[0]
        prev = missing[0]
        for m in missing[1:]:
            if m == prev + 1:
                prev = m
            else:
                ranges.append((start, prev))
                start = prev = m
        ranges.append((start, prev))
        print("Gap ranges:")
        for a, b in ranges[:30]:
            print(f"  {a}-{b}" if a != b else f"  {a}")
        if len(ranges) > 30:
            print(f"  ... and {len(ranges)-30} more ranges")


if __name__ == "__main__":
    main()
