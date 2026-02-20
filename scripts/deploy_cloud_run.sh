#!/usr/bin/env bash
set -euo pipefail

# Config (override via env)
REGION="${REGION:-us-west1}"
SERVICE="${SERVICE:-clove-api}"
REPO="${REPO:-clove}"

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
if [[ -z "${PROJECT_ID}" ]]; then
  echo "ERROR: PROJECT_ID is empty. Run: gcloud config set project <your-project-id>" >&2
  exit 1
fi

IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO}/api:${TAG:-v1}"

echo "Project:  ${PROJECT_ID}"
echo "Region:   ${REGION}"
echo "Service:  ${SERVICE}"
echo "Image:    ${IMAGE}"
echo

echo "==> Cloud Build: build + push image"
gcloud builds submit --tag "${IMAGE}" .

echo
echo "==> Deploy to Cloud Run"
gcloud run deploy "${SERVICE}" \
  --region "${REGION}" \
  --image "${IMAGE}"

echo
echo "==> Service URL"
URL="$(gcloud run services describe "${SERVICE}" --region "${REGION}" --format='value(status.url)')"
echo "${URL}"
