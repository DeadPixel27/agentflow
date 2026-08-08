#!/usr/bin/env bash
# Live test for Frontend V3 Plan Mode — exercises /refine/plan then optional /refine Apply.
set -euo pipefail

API="${API_URL:-http://127.0.0.1:8000}"
SAMPLE="${SAMPLE_PDF:-../backend/samples/test_invoice.pdf}"

echo "=== Plan Mode Live Test ==="
echo "API: $API"
echo ""

if [[ ! -f "$SAMPLE" ]]; then
  echo "✗ Sample PDF not found: $SAMPLE"
  exit 1
fi

python3 <<'PY'
import json
import os
import sys
import time
import urllib.request

API = os.environ.get("API_URL", "http://127.0.0.1:8000")
SAMPLE = os.environ.get("SAMPLE_PDF", "../backend/samples/test_invoice.pdf")


def req(method: str, path: str, body=None):
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(f"{API}{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=120) as resp:
        return resp.status, json.loads(resp.read())


def upload_file(path: str) -> str:
    import mimetypes
    from urllib.request import Request, urlopen

    boundary = "----planmode"
    with open(path, "rb") as f:
        content = f.read()
    filename = os.path.basename(path)
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="files"; filename="{filename}"\r\n'
        f"Content-Type: {mimetypes.guess_type(path)[0] or 'application/octet-stream'}\r\n\r\n"
    ).encode() + content + f"\r\n--{boundary}--\r\n".encode()
    request = Request(
        f"{API}/api/upload",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urlopen(request, timeout=120) as resp:
        payload = json.loads(resp.read())
    return payload["upload_id"]


upload_id = upload_file(SAMPLE)
_, run = req(
    "POST",
    "/api/runs/adhoc",
    {
        "upload_id": upload_id,
        "task_description": "Extract vendor, invoice number, amount, and date.",
    },
)
run_id = run["run_id"]
print(f"Run started: {run_id}")

status = "running"
for _ in range(60):
    _, data = req("GET", f"/api/runs/{run_id}")
    status = data["status"]
    if status in ("completed", "failed"):
        break
    time.sleep(2)

if status != "completed":
    print(f"✗ Run ended with status={status}")
    sys.exit(1)
print("✓ Run completed")

print("\n[1] POST /refine/plan — Send #1")
code, plan1 = req(
    "POST",
    f"/api/runs/{run_id}/refine/plan",
    {"message": "fix the dates", "chat_history": []},
)
print(json.dumps(plan1, indent=2))
if code != 200:
    print(f"✗ Expected 200, got {code}")
    sys.exit(1)
if "message" not in plan1:
    print("✗ Missing message in plan response")
    sys.exit(1)
print("✓ Plan #1 returned 200")

history = [
    {"role": "user", "content": "fix the dates"},
    {"role": "assistant", "content": plan1["message"]},
]

print("\n[2] POST /refine/plan — Send #2 (confirm)")
_, plan2 = req(
    "POST",
    f"/api/runs/{run_id}/refine/plan",
    {
        "message": "yes, normalize all dates to YYYY-MM-DD",
        "chat_history": history,
    },
)
print(json.dumps(plan2, indent=2))
print(f"ready={plan2.get('ready')} planned_changes={plan2.get('planned_changes')}")

if os.environ.get("RUN_APPLY") == "1" and plan2.get("ready") and plan2.get("accumulated_instruction"):
    print("\n[3] POST /refine — Apply")
    _, refine = req(
        "POST",
        f"/api/runs/{run_id}/refine",
        {"message": plan2["accumulated_instruction"]},
    )
    child_id = refine["run"]["run_id"]
    print(f"✓ Apply started child run: {child_id}")
    print(f"  summary: {refine.get('refine_summary', '')[:120]}")
else:
    print("\n~ Skipping Apply (set RUN_APPLY=1 to test expensive /refine)")

print("\n=== Plan Mode test passed ===")
PY
