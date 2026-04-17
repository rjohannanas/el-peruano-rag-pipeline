#!/bin/bash
# =============================================================================
# deploy.sh — Despliegue del Pipeline de Vectorización a Cloud Run Job
# Proyecto: vertex-normas (164732621152)
# =============================================================================

set -e  # Detener si cualquier comando falla

# ─────────────────────────────────────────────
# VARIABLES — editar si cambian tus recursos
# ─────────────────────────────────────────────
PROJECT_ID="vertex-normas"
REGION="us-central1"
SERVICE_ACCOUNT="vertex-ai-normas@vertex-normas.iam.gserviceaccount.com"

REPO_NAME="normas-repo"
IMAGE_NAME="normas-pipeline"
IMAGE_TAG="latest"
IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:${IMAGE_TAG}"

JOB_NAME="normas-pipeline"
SCHEDULER_JOB_NAME="normas-pipeline-diario"

# Cloud SQL
CLOUD_SQL_INSTANCE="vertex-normas:us-central1:scraper-elperuano"
DB_USER="postgres"
DB_NAME="postgres"
# La contraseña se carga desde tu .env local (DB_PASSWORD)
source .env 2>/dev/null || true

# Extraer contraseña del DATABASE_URL del .env si DB_PASSWORD no está definida
if [ -z "$DB_PASSWORD" ]; then
    DB_PASSWORD=$(python3 -c "
import os, urllib.parse
url = os.getenv('DATABASE_URL', '')
if url:
    from urllib.parse import urlparse
    parsed = urlparse(url)
    print(urllib.parse.unquote(parsed.password or ''))
" 2>/dev/null)
fi

# DATABASE_URL para Cloud Run con Auth Proxy (socket Unix)
DB_URL_CLOUD_RUN="postgresql://${DB_USER}:${DB_PASSWORD}@/${DB_NAME}?host=/cloudsql/${CLOUD_SQL_INSTANCE}"

# Vertex AI
VERTEX_INDEX_ENDPOINT_ID="8203845481952968704"
VERTEX_DEPLOYED_INDEX_ID="deploy_text_embedding_004"
VERTEX_INDEX_ID="8459231246759755776"

# ─────────────────────────────────────────────
# PASO 1: Habilitar las APIs necesarias
# ─────────────────────────────────────────────
echo ""
echo "==> PASO 1: Habilitando APIs de GCP..."
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    cloudscheduler.googleapis.com \
    sqladmin.googleapis.com \
    aiplatform.googleapis.com \
    --project="${PROJECT_ID}"

# ─────────────────────────────────────────────
# PASO 2: Asignar roles IAM a la Service Account
# ─────────────────────────────────────────────
echo ""
echo "==> PASO 2: Asignando roles IAM a ${SERVICE_ACCOUNT}..."

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/cloudsql.client" \
    --condition=None \
    --quiet

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/aiplatform.user" \
    --condition=None \
    --quiet

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/run.invoker" \
    --condition=None \
    --quiet

echo "    Roles asignados correctamente."

# ─────────────────────────────────────────────
# PASO 3: Crear Artifact Registry si no existe
# ─────────────────────────────────────────────
echo ""
echo "==> PASO 3: Verificando Artifact Registry '${REPO_NAME}'..."
if ! gcloud artifacts repositories describe "${REPO_NAME}" \
    --location="${REGION}" \
    --project="${PROJECT_ID}" &>/dev/null; then
    echo "    Creando repositorio de Docker..."
    gcloud artifacts repositories create "${REPO_NAME}" \
        --repository-format=docker \
        --location="${REGION}" \
        --project="${PROJECT_ID}" \
        --description="Imagenes Docker para el pipeline de normas"
else
    echo "    Repositorio ya existe, continuando..."
fi

# Configurar Docker para Artifact Registry
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet

# ─────────────────────────────────────────────
# PASO 4: Construir y publicar imagen Docker
# ─────────────────────────────────────────────
echo ""
echo "==> PASO 4: Construyendo y publicando imagen Docker..."
echo "    Imagen destino: ${IMAGE_URI}"

gcloud builds submit \
    --tag="${IMAGE_URI}" \
    --project="${PROJECT_ID}" \
    .

echo "    Imagen publicada correctamente."

# ─────────────────────────────────────────────
# PASO 5: Crear / actualizar el Cloud Run Job
# ─────────────────────────────────────────────
echo ""
echo "==> PASO 5: Creando/actualizando Cloud Run Job '${JOB_NAME}'..."

# Verificar si ya existe el job para usar update en vez de create
if gcloud run jobs describe "${JOB_NAME}" \
    --region="${REGION}" \
    --project="${PROJECT_ID}" &>/dev/null; then
    JOB_CMD="update"
    echo "    Job existente detectado, actualizando..."
else
    JOB_CMD="create"
    echo "    Creando nuevo Job..."
fi

gcloud run jobs ${JOB_CMD} "${JOB_NAME}" \
    --image="${IMAGE_URI}" \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --service-account="${SERVICE_ACCOUNT}" \
    --add-cloudsql-instances="${CLOUD_SQL_INSTANCE}" \
    --set-env-vars="DATABASE_URL=${DB_URL_CLOUD_RUN}" \
    --set-env-vars="GCP_PROJECT_ID=${PROJECT_ID}" \
    --set-env-vars="GCP_LOCATION=${REGION}" \
    --set-env-vars="VERTEX_INDEX_ENDPOINT_ID=${VERTEX_INDEX_ENDPOINT_ID}" \
    --set-env-vars="VERTEX_DEPLOYED_INDEX_ID=${VERTEX_DEPLOYED_INDEX_ID}" \
    --set-env-vars="VERTEX_INDEX_ID=${VERTEX_INDEX_ID}" \
    --set-env-vars="EMBEDDING_MODEL_NAME=text-embedding-004" \
    --set-env-vars="EMBEDDING_DIMENSIONS=768" \
    --memory=1Gi \
    --cpu=1 \
    --task-timeout=1800 \
    --max-retries=1

echo "    Job configurado correctamente."

# ─────────────────────────────────────────────
# PASO 6: Crear Cloud Scheduler (5am Lima = 10am UTC)
# ─────────────────────────────────────────────
echo ""
echo "==> PASO 6: Configurando Cloud Scheduler para ejecución diaria a las 5am Lima..."

# Obtener el ID numérico del proyecto para el target del scheduler
PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format="value(projectNumber)")

if gcloud scheduler jobs describe "${SCHEDULER_JOB_NAME}" \
    --location="${REGION}" \
    --project="${PROJECT_ID}" &>/dev/null; then
    echo "    Scheduler existente detectado, actualizando..."
    gcloud scheduler jobs update http "${SCHEDULER_JOB_NAME}" \
        --location="${REGION}" \
        --project="${PROJECT_ID}" \
        --schedule="0 10 * * *" \
        --time-zone="UTC" \
        --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_NUMBER}/jobs/${JOB_NAME}:run" \
        --http-method=POST \
        --oauth-service-account-email="${SERVICE_ACCOUNT}"
else
    gcloud scheduler jobs create http "${SCHEDULER_JOB_NAME}" \
        --location="${REGION}" \
        --project="${PROJECT_ID}" \
        --schedule="0 10 * * *" \
        --time-zone="UTC" \
        --uri="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_NUMBER}/jobs/${JOB_NAME}:run" \
        --http-method=POST \
        --oauth-service-account-email="${SERVICE_ACCOUNT}" \
        --description="Pipeline diario de vectorizacion de normas legales - 5am Lima"
fi

echo ""
echo "========================================================"
echo "  DESPLIEGUE COMPLETADO"
echo "========================================================"
echo ""
echo "  Job:       ${JOB_NAME}"
echo "  Imagen:    ${IMAGE_URI}"
echo "  Horario:   Diario a las 5:00am (Lima / UTC-5)"
echo "  Auth Proxy: ${CLOUD_SQL_INSTANCE}"
echo ""
echo "  Para ejecutar manualmente:"
echo "  gcloud run jobs execute ${JOB_NAME} --region=${REGION} --project=${PROJECT_ID}"
echo ""
echo "  Para ver los logs:"
echo "  gcloud logging read 'resource.type=cloud_run_job AND resource.labels.job_name=${JOB_NAME}' --project=${PROJECT_ID} --limit=50"
echo ""
