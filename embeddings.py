import vertexai
import time
from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel
from google.oauth2 import service_account
from config import config

# Inicialización diferida del modelo
_model = None

def get_embedding_model():
    global _model
    if _model is None:
        # Configurar credenciales (si usas default login en un server, credentials_path puede ser None)
        credentials = None
        if config.GCP_CREDENTIALS_PATH:
            try:
                credentials = service_account.Credentials.from_service_account_file(
                    config.GCP_CREDENTIALS_PATH,
                    scopes=["https://www.googleapis.com/auth/cloud-platform"]
                )
            except FileNotFoundError:
                print(f"Advertencia: No se encontró {config.GCP_CREDENTIALS_PATH}. Se usará la identidad predeterminada de GCP.")

        vertexai.init(
            project=config.GCP_PROJECT_ID, 
            location=config.GCP_LOCATION, 
            credentials=credentials
        )
        
        # Cargar modelo especificado en la configuración
        _model = TextEmbeddingModel.from_pretrained(config.EMBEDDING_MODEL_NAME)
        print(f"Modelo cargado: {config.EMBEDDING_MODEL_NAME}")
        
    return _model


def generate_embeddings_batch(normas):
    """
    Genera embeddings en lotes para optimizar llamadas a la API de Vertex AI.
    Soporta procesar hasta 250 elementos por llamada.
    """
    if not normas:
        return []

    model = get_embedding_model()
    
    # Preparar inputs
    # Vertex Search recomienda textos de hasta ~2000 tokens (usamos corte por caracteres aprox ~8000)
    inputs = []
    for norma in normas:
        texto_recortado = norma["texto_completo"][:8000]
        
        # Si usas text-embedding-004 puedes pasar task_type="RETRIEVAL_DOCUMENT" opcionalmente
        # via TextEmbeddingInput (depende de versión de sdk), pero usaremos formato string estandar:
        inputs.append(texto_recortado)

    datapoints = []
    
    # Procesar en lotes pequeños para no superar el límite de 20,000 tokens por llamada de Vertex AI
    BATCH_SIZE = 5
    for i in range(0, len(inputs), BATCH_SIZE):
        lote_textos = inputs[i:i + BATCH_SIZE]
        lote_normas = normas[i:i + BATCH_SIZE]
        
        # Sistema de reintento para evitar fallos por cuota (Error 429)
        max_retries = 5
        wait_time = 5 # Empezamos con 5 segundos de espera
        
        for attempt in range(max_retries):
            try:
                # El modelo text-embedding-004 soporta dimensiones variables
                kwargs = {}
                if "004" in config.EMBEDDING_MODEL_NAME or "multilingual" in config.EMBEDDING_MODEL_NAME:
                    kwargs["output_dimensionality"] = config.EMBEDDING_DIMENSIONS
                
                embeddings = model.get_embeddings(lote_textos, **kwargs)
                
                for j, embedding_obj in enumerate(embeddings):
                    norma = lote_normas[j]
                    datapoints.append({
                        "id": str(norma["op"]),
                        "embedding": embedding_obj.values,
                        "metadata": {
                            "nombre": norma["nombre_dispositivo"],
                            "fecha": norma["fecha_publicacion"],
                            "entidad_id": str(norma["entidad_id"]) if norma["entidad_id"] is not None else "",
                            "tipo_dispositivo": str(norma["tipo_dispositivo"]) if norma["tipo_dispositivo"] is not None else "",
                            "fuente": str(norma["fuente"]) if norma["fuente"] is not None else ""
                        }
                    })
                # Si llegamos aquí, el lote fue exitoso. Salimos del bucle de reintentos.
                break 
                
            except Exception as e:
                if "429" in str(e) and attempt < max_retries - 1:
                    print(f"⚠️ Límite de cuota alcanzado en lote {i}. Reintentando en {wait_time}s... (Intento {attempt+1}/{max_retries})")
                    time.sleep(wait_time)
                    wait_time *= 2 # Backoff exponencial
                else:
                    print(f"❌ Error definitivo en el lote {i}: {e}")
                    break

    print(f"✓ {len(datapoints)} embeddings generados en total.")
    return datapoints
