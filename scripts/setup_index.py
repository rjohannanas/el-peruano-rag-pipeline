import os
import sys

# Agregar ruta padre al sys.path para poder importar config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.cloud import aiplatform
from config import config

def create_index_and_endpoint():
    """
    Este script crea un Index de Matching Engine (Vector Search) 
    y un Endpoint, ajustado a las dimensiones de config.py, de manera no interactiva.
    """
    print(f"🔹 Configurando Vector Search para el Modelo: {config.EMBEDDING_MODEL_NAME}")
    print(f"🔹 Dimensiones Requeridas: {config.EMBEDDING_DIMENSIONS}")
    
    # Init central de la SDK
    aiplatform.init(project=config.GCP_PROJECT_ID, location=config.GCP_LOCATION)
    
    index_display_name = f"indice_RAG_{config.EMBEDDING_MODEL_NAME.replace('-', '_')}"
    
    print("\n[1] Creando Índice de Factores...")
    print("Nota: Esto puede tardar desde 30 mins hasta 1 hora en completarse en Google Cloud. El script se quedará esperando.")
    try:
        my_index = aiplatform.MatchingEngineIndex.create_tree_ah_index(
            display_name=index_display_name,
            dimensions=config.EMBEDDING_DIMENSIONS,
            approximate_neighbors_count=150,
            distance_measure_type="DOT_PRODUCT_DISTANCE",
            leaf_node_embedding_count=500,
            leaf_nodes_to_search_percent=10,
            index_update_method="STREAM_UPDATE",
        )
        print(f"✅ Índice creado exitosamente: {my_index.resource_name}")
    except Exception as e:
        print(f"❌ Error al crear el índice: {e}")
        return

    print("\n[2] Creando Index Endpoint...")
    endpoint_display_name = f"endpoint_RAG_{config.EMBEDDING_MODEL_NAME.replace('-', '_')}"
    
    try:
        my_index_endpoint = aiplatform.MatchingEngineIndexEndpoint.create(
            display_name=endpoint_display_name,
            public_endpoint_enabled=True 
        )
        print(f"✅ Endpoint de Índice creado exitosamente: {my_index_endpoint.resource_name}")
    except Exception as e:
        print(f"❌ Error al crear el Endpoint: {e}")
        return

    print("\n[3] Desplegando Índice al Endpoint...")
    print("Esto también puede tomar varios minutos.")
    deploy_name = f"deploy_{config.EMBEDDING_MODEL_NAME.replace('-', '_')}"
    try:
        my_index_endpoint.deploy_index(
            index=my_index,
            deployed_index_id=deploy_name
        )
        print(f"✅ Índice desplegado exitosamente con ID: {deploy_name}")
    except Exception as e:
        print(f"❌ Error al desplegar el Índice: {e}")
        return
        
    print("\n====================================")
    print("  SETUP COMPLETADO EXITOSAMENTE     ")
    print("====================================")
    print(f"Actualiza tu archivo .env con los siguientes valores:")
    print(f"VERTEX_INDEX_ID={my_index.name}")
    print(f"VERTEX_INDEX_ENDPOINT_ID={my_index_endpoint.name}")
    print(f"VERTEX_DEPLOYED_INDEX_ID={deploy_name}")

if __name__ == "__main__":
    create_index_and_endpoint()
