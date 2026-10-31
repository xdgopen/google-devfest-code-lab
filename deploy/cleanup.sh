#!/usr/bin/env bash
# Delete EVERYTHING created by setup_gcp.sh / deploy.sh / deploy_adk_cli.sh.
set -euo pipefail
source "$(dirname "$0")/config.sh"

read -r -p "Delete all Blogger Agent resources in ${PROJECT_ID}? Type the project id to confirm: " answer
[[ "${answer}" == "${PROJECT_ID}" ]] || { echo "Aborted."; exit 1; }

log "Cloud Run services"
for svc in "${SERVICE}" "${SERVICE}-adkweb"; do
  gcloud run services delete "${svc}" --region="${REGION}" --quiet 2>/dev/null || true
done
log "Artifact Registry repositories"
gcloud artifacts repositories delete "${AR_REPO}" --location="${REGION}" --quiet 2>/dev/null || true
gcloud artifacts repositories delete cloud-run-source-deploy --location="${REGION}" --quiet 2>/dev/null || true
log "Cloud SQL instance (and its data)"
gcloud sql instances delete "${SQL_INSTANCE}" --quiet 2>/dev/null || true
log "Secret, bucket"
gcloud secrets delete "${DB_SECRET}" --quiet 2>/dev/null || true
gcloud storage rm --recursive "gs://${BUCKET}" --quiet 2>/dev/null || true
log "IAM bindings + service account"
for role in roles/aiplatform.user roles/cloudsql.client roles/secretmanager.secretAccessor \
            roles/logging.logWriter roles/cloudtrace.agent roles/monitoring.metricWriter; do
  gcloud projects remove-iam-policy-binding "${PROJECT_ID}" --member="serviceAccount:${SA_EMAIL}" \
    --role="${role}" --condition=None --quiet >/dev/null 2>&1 || true
done
gcloud iam service-accounts delete "${SA_EMAIL}" --quiet 2>/dev/null || true
log "✅ Cleanup done (APIs stay enabled – they cost nothing)."
