#!/usr/bin/env bash
# The ORIGINAL codelab deployment (step 8): ADK CLI → Cloud Run with the ADK Web UI.
# Kept for comparison with the production pipeline (deploy.sh).
set -euo pipefail
source "$(dirname "$0")/config.sh"
cd "$(dirname "$0")/../backend/bloggeragent"

adk deploy cloud_run \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --service_name="${SERVICE}-adkweb" \
  --with_ui \
  . \
  -- \
  --set-env-vars "GOOGLE_GENAI_USE_VERTEXAI=TRUE,MODEL=${MODEL},GOOGLE_CLOUD_LOCATION=${GENAI_LOCATION}"
