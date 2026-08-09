#!/usr/bin/env python3
"""Merge FRONTEND-LAUNCH-PROMPT OCR batch JSON files into markdown."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
OUT = DOCS / "FRONTEND-LAUNCH-PROMPT.md"
MAX_LINE = 1237


def load_json(name: str) -> dict[str, str]:
    path = DOCS / name
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("lines", {})


def main() -> None:
    merged: dict[int, str] = {}

    for name in (
        "FRONTEND-LAUNCH-PROMPT-ocr-batch1.json",
        "FRONTEND-LAUNCH-PROMPT-ocr-batch2.json",
        "FRONTEND-LAUNCH-PROMPT-ocr-batch3.json",
        "FRONTEND-LAUNCH-PROMPT-gap-fills.json",
    ):
        for k, v in load_json(name).items():
            merged[int(k)] = v

    # Photo/OCR verified overrides
    merged[1] = (
        "# Frontend Launch — Bug Fixes + JWT Auth + Usage + Waitlist + "
        "Pricing + Extraction UI"
    )
    merged[11] = (
        "You are fixing refine-chat bugs and adding auth, usage, waitlist, "
        "and pricing features to the AgentFlow frontend. Codebase: "
        "`github.com/kabirrao2002/agentflow`, branch"
    )
    merged[12] = "`develop`, working in `frontend/`."

    missing = [i for i in range(1, MAX_LINE + 1) if i not in merged]
    lines_out = [merged.get(n, "") for n in range(1, MAX_LINE + 1)]

    header = [
        "",
        "> Transcribed from `frontend-launch-prompt/` screenshots (Aug 9, 2026).",
        "",
    ]
    if lines_out and lines_out[0].startswith("# Frontend Launch"):
        final = [lines_out[0]] + header + lines_out[1:]
    else:
        final = header + lines_out

    OUT.write_text("\n".join(final) + "\n", encoding="utf-8")

    covered = MAX_LINE - len(missing)
    print(f"Written {OUT}")
    print(f"Covered: {covered}/{MAX_LINE} lines ({100 * covered / MAX_LINE:.1f}%)")
    if missing:
        print(f"Missing: {missing[:50]}")


if __name__ == "__main__":
    main()
