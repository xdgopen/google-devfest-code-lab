#!/usr/bin/env bash
# Shared deployment settings. Override any value via environment variables:
#   PROJECT_ID=my-proj REGION=asia-southeast1 ./deploy/setup_gcp.sh
set -euo pipefail

: "${PROJECT_ID:=$(gcloud config get-value project 2>/dev/null)}"
if [[ -z "${PROJECT_ID}" ]]; then
  echo "❌ PROJECT_ID is not set (export PROJECT_ID=... or gcloud config set project ...)" >&2
  exit 1
fi

REGION="${REGION:-us-east1}"
SERVICE="${SERVICE:-bloggeragent}"
AR_REPO="${AR_REPO:-blogger-repo}"
SA_NAME="${SA_NAME:-blogger-agent-sa}"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
SQL_INSTANCE="${SQL_INSTANCE:-blogger-pg}"
SQL_TIER="${SQL_TIER:-db-f1-micro}"
DB_NAME="${DB_NAME:-blogger}"
DB_USER="${DB_USER:-blogger}"
DB_SECRET="${DB_SECRET:-blogger-database-url}"
BUCKET="${BUCKET:-${PROJECT_ID}-blogger-artifacts}"
MODEL="${MODEL:-gemini-3.5-flash}"
GENAI_LOCATION="${GENAI_LOCATION:-global}"
IMAGE_TAG="${IMAGE_TAG:-$(date +%Y%m%d-%H%M%S)}"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/${SERVICE}:${IMAGE_TAG}"
ALLOW_UNAUTHENTICATED="${ALLOW_UNAUTHENTICATED:-true}"

PROJECT_NUMBER="$(gcloud projects describe "${PROJECT_ID}" --format='value(projectNumber)')"
COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
CLOUDBUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"
INSTANCE_CONNECTION_NAME="${PROJECT_ID}:${REGION}:${SQL_INSTANCE}"

log() { printf '\n\033[1;32m▶ %s\033[0m\n' "$*"; }
