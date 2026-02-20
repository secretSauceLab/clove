#!/usr/bin/env bash
set -euo pipefail

REGION="${REGION:-us-west1}"
SERVICE="${SERVICE:-clove-api}"
API_KEY_SECRET="${API_KEY_SECRET:-CLOVER_API_KEY}"

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
URL="${URL:-$(gcloud run services describe "${SERVICE}" --region "${REGION}" --format='value(status.url)')}"

API_KEY="$(gcloud secrets versions access latest --secret="${API_KEY_SECRET}")"

echo "Project:  ${PROJECT_ID}"
echo "Region:   ${REGION}"
echo "Service:  ${SERVICE}"
echo "URL:      ${URL}"
echo

hdr=(-H "X-API-Key: ${API_KEY}")

request_json () {
  local method="$1"; shift
  local url="$1"; shift

  local tmp
  tmp="$(mktemp)"

  local http_code
  http_code="$(curl -sS -o "$tmp" -w "%{http_code}" -X "$method" "$url" "$@")" || {
    echo "ERROR: curl failed: $method $url" >&2
    cat "$tmp" >&2 || true
    rm -f "$tmp"
    return 1
  }

  if [[ "$http_code" -lt 200 || "$http_code" -ge 300 ]]; then
    echo "ERROR: $method $url returned HTTP $http_code" >&2
    echo "---- response body ----" >&2
    cat "$tmp" >&2
    echo "-----------------------" >&2
    rm -f "$tmp"
    return 1
  fi

  if ! python3 -m json.tool < "$tmp" >/dev/null 2>&1; then
    echo "ERROR: $method $url returned non-JSON body (HTTP $http_code)" >&2
    echo "---- response body ----" >&2
    cat "$tmp" >&2
    echo "-----------------------" >&2
    rm -f "$tmp"
    return 1
  fi

  cat "$tmp"
  rm -f "$tmp"
}

echo "==> GET /health"
request_json GET "${URL}/health" >/dev/null
echo "OK"

echo
echo "==> GET /cases"
cases_json="$(request_json GET "${URL}/cases" "${hdr[@]}")"
echo "OK"

case_id="$(printf "%s" "$cases_json" | python3 -c 'import json,sys; data=json.load(sys.stdin); items=data.get("items") or []; print(items[0]["case_id"] if items else "")')"

if [[ -z "${case_id}" ]]; then
  echo
  echo "==> No cases found. Creating one via POST /intakes"
  intake_payload='{"full_name":"Prod Smoke Test","email":"prod-smoke-test@example.com","phone":"555-555-5555","narrative":"Smoke test intake (safe to delete)."}'
  created="$(request_json POST "${URL}/intakes" "${hdr[@]}" -H "Content-Type: application/json" -d "${intake_payload}")"
  case_id="$(printf "%s" "$created" | python3 -c 'import json,sys; print(json.load(sys.stdin)["case_id"])')"
  echo "Created case_id=${case_id}"
else
  echo "Using existing case_id=${case_id}"
fi

echo
echo "==> POST /cases/{case_id}/notes"
note_payload='{"author":"prod-smoke-test","body":"Smoke test note"}'
request_json POST "${URL}/cases/${case_id}/notes" "${hdr[@]}" -H "Content-Type: application/json" -d "${note_payload}" >/dev/null
echo "OK"

echo
echo "==> GET /cases/{case_id}/notes"
request_json GET "${URL}/cases/${case_id}/notes" "${hdr[@]}" >/dev/null
echo "OK"

echo
echo "==> POST /cases/{case_id}/documents (metadata)"
doc_payload='{"filename":"smoke_test.pdf","content_type":"application/pdf"}'
doc_created="$(request_json POST "${URL}/cases/${case_id}/documents" "${hdr[@]}" -H "Content-Type: application/json" -d "${doc_payload}")"
document_id="$(printf "%s" "$doc_created" | python3 -c 'import json,sys; print(json.load(sys.stdin)["document_id"])')"
echo "Created document_id=${document_id}"

echo
echo "==> GET /cases/{case_id}/documents"
request_json GET "${URL}/cases/${case_id}/documents" "${hdr[@]}" >/dev/null
echo "OK"

echo
echo "Smoke test PASSED ✅"
