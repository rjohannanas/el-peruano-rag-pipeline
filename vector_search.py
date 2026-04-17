from google.cloud import aiplatform
from google.cloud.aiplatform.matching_engine.matching_engine_index_endpoint import Namespace
from google.oauth2 import service_account
from config import config

_initialized = False

def init_aiplatform():
    global _initialized
    if not _initialized:
        credentials = None
        if config.GCP_CREDENTIALS_PATH:
            try:
                credentials = service_account.Credentials.from_service_account_file(
                    config.GCP_CREDENTIALS_PATH,
                    scopes=["https://www.googleapis.com/auth/cloud-platform"]
                )
            except FileNotFoundError:
                pass

        aiplatform.init(
            project=config.GCP_PROJECT_ID, 
            location=config.GCP_LOCATION, 
            credentials=credentials
        )
        _initialized = True

def upsert_to_vector_search(datapoints):
    """
    Toma una lista de diccionarios con 'id' y 'embedding' y los inserta/actualiza 
    en el Endpoint de Vector Search (Matching Engine).
    """
    if not datapoints:
        return []

    init_aiplatform()

    index_datapoints = []
    for dp in datapoints:
        restricts = []
        if dp["metadata"].get("entidad_id"):
            restricts.append(aiplatform.gapic.IndexDatapoint.Restriction(namespace="entidad_id", allow_list=[dp["metadata"]["entidad_id"]]))
        if dp["metadata"].get("tipo_dispositivo"):
            restricts.append(aiplatform.gapic.IndexDatapoint.Restriction(namespace="tipo_dispositivo", allow_list=[dp["metadata"]["tipo_dispositivo"]]))
        if dp["metadata"].get("fuente"):
            restricts.append(aiplatform.gapic.IndexDatapoint.Restriction(namespace="fuente", allow_list=[dp["metadata"]["fuente"]]))

        index_datapoints.append(
            aiplatform.gapic.IndexDatapoint(
                datapoint_id=dp["id"],
                feature_vector=dp["embedding"],
                restricts=restricts
            )
        )

    index_name = f"projects/{config.GCP_PROJECT_ID}/locations/{config.GCP_LOCATION}/indexes/{config.VERTEX_INDEX_ID}"
    
    try:
        index = aiplatform.MatchingEngineIndex(index_name=index_name)
        index.upsert_datapoints(datapoints=index_datapoints)
        print(f"✓ {len(index_datapoints)} vectores insertados/actualizados exitosamente en Vector Search.")
        return [dp["id"] for dp in datapoints]
    except Exception as e:
        print(f"Error realizando Upsert en Vector Search: {e}")
        return []

def search_nearest_neighbors(query_embedding, num_neighbors=3):
    """
    Busca los vecinos más cercanos en el Endpoint de Vector Search 
    dado un embedding de consulta.
    """
    init_aiplatform()
    
    endpoint_name = f"projects/{config.GCP_PROJECT_ID}/locations/{config.GCP_LOCATION}/indexEndpoints/{config.VERTEX_INDEX_ENDPOINT_ID}"
    
    try:
        endpoint = aiplatform.MatchingEngineIndexEndpoint(index_endpoint_name=endpoint_name)
        
        # Ejecutar la búsqueda
        response = endpoint.find_neighbors(
            deployed_index_id=config.VERTEX_DEPLOYED_INDEX_ID,
            queries=[query_embedding],
            num_neighbors=num_neighbors
        )
        
        # Extraer IDs de la respuesta
        # response[0] es la lista de vecinos para la primera (y única) query
        neighbor_ids = [neighbor.id for neighbor in response[0]]
        return neighbor_ids
    except Exception as e:
        print(f"Error en la búsqueda semántica: {e}")
        return []
