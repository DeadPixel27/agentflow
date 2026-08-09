#!/usr/bin/env python3
"""Extract line-numbered content from BACKEND-LAUNCH-PROMPT screenshots via OCR."""

import json
import re
import subprocess
import sys
from pathlib import Path

IMAGE_DIR = Path(__file__).resolve().parent.parent / "backend-launch-prompt"
OUTPUT_JSON = Path(__file__).resolve().parent.parent / "docs" / "BACKEND-LAUNCH-PROMPT-lines.json"


def ocr_image(path: Path) -> str:
    result = subprocess.run(
        ["tesseract", str(path), "stdout", "--psm", "6"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout


def parse_lines(text: str) -> dict[int, str]:
    """Parse OCR text looking for line-number + content patterns."""
    lines_map: dict[int, str] = {}
    # Pattern: line number at start of line (1-4 digits) followed by content
    for raw in text.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        # Skip UI noise
        if any(
            skip in raw.lower()
            for skip in [
                "whatsapp",
                "windsurf",
                "markdown",
                "utf-8",
                "spaces:",
                "update downloaded",
                "enterprise",
                "project-agentflow",
                "test-email",
                "business-strategy",
                "frontend-v4",
                "backend-v4",
                "backend-v3",
            ]
        ):
            continue

        # Match: "1234  content" or "1234| content" or "1234 content"
        m = re.match(r"^(\d{1,4})\s*[|\s]\s*(.*)$", raw)
        if m:
            num = int(m.group(1))
            content = m.group(2).strip()
            if num > 0 and num <= 2500:
                # Prefer longer/more complete content for same line
                if num not in lines_map or len(content) > len(lines_map[num]):
                    lines_map[num] = content
        else:
            # Sometimes line number and content are separate in OCR
            m2 = re.match(r"^(\d{1,4})$", raw)
            if m2:
                continue  # orphan line number

    return lines_map


def main() -> None:
    images = sorted(IMAGE_DIR.glob("*.jpeg"))
    if not images:
        print(f"No images in {IMAGE_DIR}", file=sys.stderr)
        sys.exit(1)

    merged: dict[int, str] = {}
    per_image: dict[str, dict[int, str]] = {}

    for img in images:
        text = ocr_image(img)
        parsed = parse_lines(text)
        per_image[img.name] = {str(k): v for k, v in parsed.items()}
        for num, content in parsed.items():
            if num not in merged or len(content) > len(merged[num]):
                merged[num] = content

    # Sort keys
    sorted_lines = {str(k): merged[k] for k in sorted(merged.keys())}

    output = {
        "total_images": len(images),
        "total_lines": len(sorted_lines),
        "line_numbers": sorted(int(k) for k in sorted_lines.keys()),
        "lines": sorted_lines,
        "per_image": per_image,
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(f"Extracted {len(sorted_lines)} unique line numbers from {len(images)} images")
    print(f"Line range: {min(merged.keys()) if merged else 0} - {max(merged.keys()) if merged else 0}")
    print(f"Written to {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
