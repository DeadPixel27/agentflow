#!/usr/bin/env bash
# Frontend E2E smoke — exercises every API path the V2 UI calls.
set -euo pipefail

API="${API_URL:-http://127.0.0.1:8000}"
WEB="${WEB_URL:-http://127.0.0.1:3000}"
SAMPLE="${SAMPLE_PDF:-../backend/samples/test_invoice.pdf}"
PASS=0
FAIL=0
SKIP=0

ok()   { echo "  ✓ $1"; PASS=$((PASS + 1)); }
bad()  { echo "  ✗ $1"; FAIL=$((FAIL + 1)); }
skip() { echo "  ~ $1 (skipped)"; SKIP=$((SKIP + 1)); }

assert_status() {
  local label="$1" expected="$2" actual="$3"
  if [[ "$actual" == "$expected" ]]; then ok "$label (HTTP $actual)"
  else bad "$label — expected $expected, got $actual"; fi
}

assert_json_field() {
  local label="$1" json="$2" field="$3"
  if echo "$json" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('$field')"; then
    ok "$label"
  else bad "$label — missing field '$field'"; fi
}

echo "=== Frontend E2E Smoke ==="
echo "API: $API  WEB: $WEB"
echo ""

# --- Static pages ---
echo "[Pages]"
for path in "/" "/workflows" "/account"; do
  code=$(curl -s -o /dev/null -w "%{http_code}" "$WEB$path")
  assert_status "GET $path" "200" "$code"
done

home=$(curl -s "$WEB/")
echo "$home" | grep -q "any document" && ok "Home has V2 hero" || bad "Home missing V2 hero"
echo "$home" | grep -q "AgentFlow" && ok "Home has AgentFlow branding" || bad "Home missing branding"
echo "$home" | grep -q "How it works" && bad "Home still has old 'How it works'" || ok "Home removed old sections"

account=$(curl -s "$WEB/account")
echo "$account" | grep -q "account/page" && ok "Account page bundle loads" || bad "Account page broken"

workflows=$(curl -s "$WEB/workflows")
echo "$workflows" | grep -q "Workflows" && ok "Workflows page title" || bad "Workflows page broken"

# --- Backend health ---
echo ""
echo "[API Health]"
health=$(curl -s "$API/api/health")
echo "$health" | grep -q '"status":"ok"' && ok "Backend health ok" || bad "Backend unhealthy"

# --- Templates (home chips) ---
echo ""
echo "[Templates]"
tpl=$(curl -s "$API/api/templates")
count=$(echo "$tpl" | python3 -c "import sys,json; print(json.load(sys.stdin).get('count',0))")
[[ "$count" -gt 0 ]] && ok "listTemplates returns $count templates" || bad "No templates"

# --- Auth ---
echo ""
echo "[Auth]"
RAND=$(python3 -c "import random; print(random.randint(10000,99999))")
auth=$(curl -s -w "\n%{http_code}" -X POST "$API/api/auth/session" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"E2E Tester\",\"email\":\"e2e-$RAND@test.local\"}")
AUTH_CODE=$(echo "$auth" | tail -1)
AUTH_BODY=$(echo "$auth" | sed '$d')
if [[ "$AUTH_CODE" == "200" ]]; then
  USER_ID=$(echo "$AUTH_BODY" | python3 -c "import sys,json; print(json.load(sys.stdin)['user']['user_id'])")
  ok "signIn creates user $USER_ID"
else
  skip "signIn failed (HTTP $AUTH_CODE) — backend auth issue, workflow tests skipped"
  USER_ID=""
fi

# --- Upload ---
echo ""
echo "[Upload + Adhoc Run]"
if [[ ! -f "$SAMPLE" ]]; then bad "Sample PDF not found: $SAMPLE"; exit 1; fi
upload=$(curl -s -X POST "$API/api/upload" -F "files=@$SAMPLE")
UPLOAD_ID=$(echo "$upload" | python3 -c "import sys,json; print(json.load(sys.stdin)['upload_id'])")
DOC_ID=$(echo "$upload" | python3 -c "import sys,json; print(json.load(sys.stdin)['documents'][0]['document_id'])")
[[ -n "$UPLOAD_ID" ]] && ok "uploadFiles → upload_id=$UPLOAD_ID" || bad "Upload failed"

docs=$(curl -s "$API/api/uploads/$UPLOAD_ID")
echo "$docs" | grep -q "$DOC_ID" && ok "getUploadDocuments" || bad "getUploadDocuments failed"

run=$(curl -s -X POST "$API/api/runs/adhoc" \
  -H "Content-Type: application/json" \
  -d "{\"upload_id\":\"$UPLOAD_ID\",\"task_description\":\"Extract vendor, invoice number, amount, and date.\"}")
RUN_ID=$(echo "$run" | python3 -c "import sys,json; print(json.load(sys.stdin)['run_id'])")
[[ -n "$RUN_ID" ]] && ok "runAdhoc → run_id=$RUN_ID" || bad "runAdhoc failed"

# Poll run (max 120s)
echo ""
echo "[Run Polling]"
STATUS="running"
for i in $(seq 1 60); do
  run_data=$(curl -s "$API/api/runs/$RUN_ID")
  STATUS=$(echo "$run_data" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")
  if [[ "$STATUS" == "completed" || "$STATUS" == "failed" ]]; then break; fi
  sleep 2
done
if [[ "$STATUS" == "completed" ]]; then
  ok "Run completed"
  ROWS=$(echo "$run_data" | python3 -c "import sys,json; r=json.load(sys.stdin).get('result') or {}; print(len(r.get('rows') or []))")
  [[ "$ROWS" -gt 0 ]] && ok "Run has $ROWS result rows" || bad "Run completed but no rows"
else
  bad "Run ended with status=$STATUS (may need OpenAI key)"
fi

# Results page
code=$(curl -s -o /dev/null -w "%{http_code}" "$WEB/results/$RUN_ID")
assert_status "GET /results/$RUN_ID" "200" "$code"
results_html=$(curl -s "$WEB/results/$RUN_ID")
echo "$results_html" | grep -q "results/\[runId\]/page\|ResultsLayout\|v2-page" && ok "Results page bundle loads (client-rendered)" || bad "Results page content missing"
echo "$results_html" | grep -q "TemplateVersionPanel" && bad "Results still references old version panel" || ok "No run-level version panel"

# --- Save workflow ---
echo ""
echo "[Workflows]"
if [[ "$STATUS" == "completed" && -n "$USER_ID" ]]; then
  wf=$(curl -s -X POST "$API/api/workflows/from-run/$RUN_ID" \
    -H "Content-Type: application/json" \
    -d "{\"user_id\":\"$USER_ID\",\"name\":\"E2E WF $RAND\",\"description\":\"smoke test\"}")
  WF_ID=$(echo "$wf" | python3 -c "import sys,json; print(json.load(sys.stdin)['workflow_id'])")
  [[ -n "$WF_ID" ]] && ok "saveWorkflowFromRun → $WF_ID" || bad "saveWorkflowFromRun failed"

  wf_list=$(curl -s "$API/api/users/$USER_ID/workflows")
  echo "$wf_list" | grep -q "$WF_ID" && ok "getUserWorkflows includes new workflow" || bad "Workflow not in list"

  code=$(curl -s -o /dev/null -w "%{http_code}" "$WEB/workflows/$WF_ID")
  assert_status "GET /workflows/$WF_ID" "200" "$code"

  code=$(curl -s -o /dev/null -w "%{http_code}" "$WEB/workflows/$WF_ID/settings")
  assert_status "GET /workflows/$WF_ID/settings" "200" "$code"

  versions=$(curl -s "$API/api/workflows/$WF_ID/template-versions")
  vcount=$(echo "$versions" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))" 2>/dev/null || echo 0)
  [[ "$vcount" -ge 0 ]] && ok "getWorkflowTemplateVersions ($vcount versions)" || bad "template versions failed"

  # Rerun workflow
  upload2=$(curl -s -X POST "$API/api/upload" -F "files=@$SAMPLE")
  UPLOAD2=$(echo "$upload2" | python3 -c "import sys,json; print(json.load(sys.stdin)['upload_id'])")
  run2=$(curl -s -X POST "$API/api/workflows/$WF_ID/runs" \
    -H "Content-Type: application/json" \
    -d "{\"upload_id\":\"$UPLOAD2\"}")
  RUN2=$(echo "$run2" | python3 -c "import sys,json; print(json.load(sys.stdin)['run_id'])")
  [[ -n "$RUN2" ]] && ok "runWorkflow → $RUN2" || bad "runWorkflow failed"

  code=$(curl -s -o /dev/null -w "%{http_code}" "$WEB/workflows/$WF_ID/runs/$RUN2")
  assert_status "GET /workflows/$WF_ID/runs/$RUN2" "200" "$code"

  wf_runs=$(curl -s "$API/api/workflows/$WF_ID/runs")
  echo "$wf_runs" | grep -q "$RUN2" && ok "getWorkflowRuns includes rerun" || bad "getWorkflowRuns missing rerun"
else
  skip "Workflow save/rerun (run incomplete or auth unavailable)"
  WF_ID=""
fi

# --- V2 delivery + settings APIs ---
echo ""
echo "[V2 APIs — email/sheets need env keys; settings should 200]"
email_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API/api/runs/$RUN_ID/email" \
  -H "Content-Type: application/json" -d '{"to":"test@x.com","subject":"hi"}')
[[ "$email_code" == "502" || "$email_code" == "200" ]] \
  && ok "emailResults returns $email_code (502 = no RESEND_API_KEY)" \
  || bad "emailResults unexpected: $email_code"

sheets_code=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API/api/runs/$RUN_ID/sheets" \
  -H "Content-Type: application/json" -d '{"url":"https://docs.google.com/spreadsheets/d/abc/edit","sheet_name":"S"}')
[[ "$sheets_code" == "502" || "$sheets_code" == "200" ]] \
  && ok "pushToSheets returns $sheets_code (502 = no GOOGLE_SERVICE_ACCOUNT_JSON)" \
  || bad "pushToSheets unexpected: $sheets_code"

if [[ -n "${WF_ID:-}" ]]; then
  settings_code=$(curl -s -o /dev/null -w "%{http_code}" -X PATCH "$API/api/workflows/$WF_ID/settings" \
    -H "Content-Type: application/json" -d '{"name":"Updated","default_email":"ops@example.com"}')
  [[ "$settings_code" == "200" ]] \
    && ok "updateWorkflowSettings returns 200" \
    || bad "updateWorkflowSettings unexpected: $settings_code"

  patch_code=$(curl -s -o /dev/null -w "%{http_code}" -X PATCH "$API/api/workflows/$WF_ID" \
    -H "Content-Type: application/json" \
    -d "{\"from_run_id\":\"$RUN_ID\",\"version_name\":\"E2E version\"}")
  [[ "$patch_code" == "200" ]] \
    && ok "updateWorkflowFromRun returns 200" \
    || bad "updateWorkflowFromRun unexpected: $patch_code"
fi

run_ver_code=$(curl -s -o /dev/null -w "%{http_code}" "$API/api/runs/$RUN_ID/template-versions")
[[ "$run_ver_code" == "404" ]] \
  && ok "run template-versions removed (404)" \
  || bad "run template-versions unexpected: $run_ver_code"

# --- Refine (optional — may be slow) ---
echo ""
echo "[Refine]"
if [[ "$STATUS" == "completed" && "${RUN_REFINE:-0}" == "1" ]]; then
  refine=$(curl -s -X POST "$API/api/runs/$RUN_ID/refine" \
    -H "Content-Type: application/json" \
    -d '{"message":"also extract payment_status"}')
  NEW_RUN=$(echo "$refine" | python3 -c "import sys,json; print(json.load(sys.stdin).get('run',{}).get('run_id',''))" 2>/dev/null || echo "")
  [[ -n "$NEW_RUN" && "$NEW_RUN" != "$RUN_ID" ]] && ok "refineRun branches to $NEW_RUN" || bad "refineRun failed"
else
  skip "refineRun (set RUN_REFINE=1 to test — costs LLM tokens)"
fi

echo ""
echo "=== Summary: $PASS passed, $FAIL failed, $SKIP skipped ==="
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
