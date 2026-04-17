import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

class Config:
    # DB (Cloud SQL)
    DATABASE_URL = os.getenv("DATABASE_URL", None)
    
    # GCP & Vertex AI
    GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "164732621152")
    GCP_LOCATION = os.getenv("GCP_LOCATION", "us-central1")
    GCP_CREDENTIALS_PATH = os.getenv("GCP_CREDENTIALS_PATH", None)  # None en Cloud Run → usa ADC

    # Vertex Search
    VERTEX_INDEX_ENDPOINT_ID = os.getenv("VERTEX_INDEX_ENDPOINT_ID", "")
    VERTEX_DEPLOYED_INDEX_ID = os.getenv("VERTEX_DEPLOYED_INDEX_ID", "")
    VERTEX_INDEX_ID = os.getenv("VERTEX_INDEX_ID", "")

    # Embeddings
    EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "text-embedding-004")
    
    # Manejar dimensiones
    try:
        EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "768"))
    except ValueError:
        EMBEDDING_DIMENSIONS = 768

config = Config()
