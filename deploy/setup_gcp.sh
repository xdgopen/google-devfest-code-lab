#!/usr/bin/env bash
# One-time, idempotent infrastructure setup for the Blogger Agent on Google Cloud.
# Creates: APIs, Artifact Registry, runtime service account + IAM, Cloud SQL
# (Postgres 16), Secret Manager secret with DATABASE_URL, GCS artifact bucket.
set -euo pipefail
source "$(dirname "$0")/config.sh"

log "Project ${PROJECT_ID} (${PROJECT_NUMBER}) – region ${REGION}"
gcloud config set project "${PROJECT_ID}" >/dev/null

log "1/7 Enable APIs"
gcloud services enable \
  run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com \
  aiplatform.googleapis.com sqladmin.googleapis.com secretmanager.googleapis.com \
  storage.googleapis.com logging.googleapis.com cloudtrace.googleapis.com \
  iam.googleapis.com

log "2/7 Artifact Registry repository ${AR_REPO}"
gcloud artifacts repositories describe "${AR_REPO}" --location="${REGION}" >/dev/null 2>&1 ||
  gcloud artifacts repositories create "${AR_REPO}" --repository-format=docker \
    --location="${REGION}" --description="Blogger Agent images"

log "3/7 Runtime service account ${SA_EMAIL}"
gcloud iam service-accounts describe "${SA_EMAIL}" >/dev/null 2>&1 ||
  gcloud iam service-accounts create "${SA_NAME}" --display-name="Blogger Agent runtime"
for role in roles/aiplatform.user roles/cloudsql.client roles/secretmanager.secretAccessor \
            roles/logging.logWriter roles/cloudtrace.agent roles/monitoring.metricWriter; do
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" --member="serviceAccount:${SA_EMAIL}" \
    --role="${role}" --condition=None --quiet >/dev/null
done

log "4/7 Build permissions (codelab step 8 + Cloud Build deploys)"
for sa in "${COMPUTE_SA}" "${CLOUDBUILD_SA}"; do
  for role in roles/cloudbuild.builds.builder roles/artifactregistry.writer roles/run.admin \
              roles/logging.logWriter roles/storage.objectViewer; do
    gcloud projects add-iam-policy-binding "${PROJECT_ID}" --member="serviceAccount:${sa}" \
      --role="${role}" --condition=None --quiet >/dev/null 2>&1 || true
  done
  gcloud iam service-accounts add-iam-policy-binding "${SA_EMAIL}" --member="serviceAccount:${sa}" \
    --role=roles/iam.serviceAccountUser --quiet >/dev/null 2>&1 || true
done

log "5/7 Cloud SQL Postgres ${SQL_INSTANCE} (${SQL_TIER}) – first run takes ~5-10 min"
if ! gcloud sql instances describe "${SQL_INSTANCE}" >/dev/null 2>&1; then
  gcloud sql instances create "${SQL_INSTANCE}" --database-version=POSTGRES_16 \
    --edition=ENTERPRISE --tier="${SQL_TIER}" --region="${REGION}" \
    --storage-size=10 --storage-auto-increase --availability-type=zonal
fi
gcloud sql databases describe "${DB_NAME}" --instance="${SQL_INSTANCE}" >/dev/null 2>&1 ||
  gcloud sql databases create "${DB_NAME}" --instance="${SQL_INSTANCE}"

log "6/7 DB user + DATABASE_URL secret"
if ! gcloud secrets describe "${DB_SECRET}" >/dev/null 2>&1; then
  DB_PASSWORD="$(openssl rand -base64 32 | tr -dc 'A-Za-z0-9' | head -c 32)"
  if gcloud sql users list --instance="${SQL_INSTANCE}" --format='value(name)' | grep -qx "${DB_USER}"; then
    gcloud sql users set-password "${DB_USER}" --instance="${SQL_INSTANCE}" --password="${DB_PASSWORD}"
  else
    gcloud sql users create "${DB_USER}" --instance="${SQL_INSTANCE}" --password="${DB_PASSWORD}"
  fi
  # Cloud Run mounts the Cloud SQL unix socket under /cloudsql/<connection name>
  printf 'postgresql://%s:%s@/%s?host=/cloudsql/%s' \
    "${DB_USER}" "${DB_PASSWORD}" "${DB_NAME}" "${INSTANCE_CONNECTION_NAME}" |
    gcloud secrets create "${DB_SECRET}" --replication-policy=automatic --data-file=-
  unset DB_PASSWORD
else
  echo "Secret ${DB_SECRET} already exists – keeping current password."
fi
gcloud secrets add-iam-policy-binding "${DB_SECRET}" --member="serviceAccount:${SA_EMAIL}" \
  --role=roles/secretmanager.secretAccessor --quiet >/dev/null

log "7/7 Artifact bucket gs://${BUCKET}"
gcloud storage buckets describe "gs://${BUCKET}" >/dev/null 2>&1 ||
  gcloud storage buckets create "gs://${BUCKET}" --location="${REGION}" --uniform-bucket-level-access
gcloud storage buckets add-iam-policy-binding "gs://${BUCKET}" \
  --member="serviceAccount:${SA_EMAIL}" --role=roles/storage.objectAdmin >/dev/null

log "✅ Infrastructure ready. Next: ./deploy/deploy.sh"
