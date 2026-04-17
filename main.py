import sys
import logging
from db import fetch_pending_normas, mark_normas_as_vectorized
from embeddings import generate_embeddings_batch
from vector_search import upsert_to_vector_search

# Logging compatible con Cloud Logging (texto plano, sin caracteres especiales)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
log = logging.getLogger(__name__)

def run_pipeline(limit=100):
    log.info("====================================")
    log.info("  PIPELINE DE ALMACENAMIENTO RAG    ")
    log.info("====================================")

    # 1. Extraer nuevas normas
    log.info("-- PASO 1: Extrayendo normas pendientes --")
    normas = fetch_pending_normas(limit=limit)
    if not normas:
        log.info("OK: No hay normas nuevas pendientes. Todo al dia.")
        return True

    log.info(f"Normas a vectorizar en este ciclo: {len(normas)}")

    # 2. Generar embeddings por lotes
    log.info("-- PASO 2: Generando embeddings (Vertex AI) --")
    datapoints = generate_embeddings_batch(normas)

    if not datapoints:
        log.error("ERROR: No se pudieron generar los embeddings.")
        return False

    # 3. Indexar en Vector Search
    log.info("-- PASO 3: Indexando en Vertex AI Vector Search --")
    inserted_ids = upsert_to_vector_search(datapoints)

    if inserted_ids:
        # 4. Marcar como vectorizadas solo si Vertex fue exitoso
        log.info("-- PASO 4: Actualizando estado en Base de Datos --")
        mark_normas_as_vectorized(inserted_ids)
        log.info(f"EXITO: Proceso completado para {len(inserted_ids)} registros.")
        return True
    else:
        log.error("ALERTA: No se pudieron insertar los vectores en Vertex AI.")
        return False

if __name__ == "__main__":
    try:
        limit_arg = int(sys.argv[1]) if len(sys.argv) > 1 else 100
        success = run_pipeline(limit=limit_arg)
        # Cloud Run Job interpreta exit code != 0 como fallo
        sys.exit(0 if success else 1)
    except Exception as e:
        log.exception(f"Error critico en el pipeline: {e}")
        sys.exit(1)
