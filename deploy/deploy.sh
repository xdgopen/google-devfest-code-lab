#!/usr/bin/env bash
# Build the image with Cloud Build and deploy it to Cloud Run.
set -euo pipefail
source "$(dirname "$0")/config.sh"
cd "$(dirname "$0")/.."

log "Build ${IMAGE} with Cloud Build"
gcloud builds submit --tag "${IMAGE}" --region="${REGION}" .

AUTH_FLAG="--allow-unauthenticated"
[[ "${ALLOW_UNAUTHENTICATED}" == "true" ]] || AUTH_FLAG="--no-allow-unauthenticated"

log "Deploy Cloud Run service ${SERVICE}"
gcloud run deploy "${SERVICE}" \
  --image="${IMAGE}" \
  --region="${REGION}" \
  --service-account="${SA_EMAIL}" \
  --add-cloudsql-instances="${INSTANCE_CONNECTION_NAME}" \
  --set-secrets="DATABASE_URL=${DB_SECRET}:latest" \
  --set-env-vars="GOOGLE_GENAI_USE_VERTEXAI=TRUE,GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${GENAI_LOCATION},MODEL=${MODEL},ARTIFACT_BUCKET=${BUCKET},ENABLE_MEMORY=true,LOG_LEVEL=INFO" \
  --cpu=1 --memory=1Gi --concurrency=20 --timeout=900 \
  --min-instances=0 --max-instances=3 \
  ${AUTH_FLAG}

URL="$(gcloud run services describe "${SERVICE}" --region="${REGION}" --format='value(status.url)')"
log "Smoke test ${URL}"
curl -fsS "${URL}/healthz" && echo
curl -fsS "${URL}/readyz" && echo
log "✅ Deployed: ${URL}"
