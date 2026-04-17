import os
from google import genai
from google.oauth2 import service_account
from config import config

def list_available_models():
    print(f"--- Listando modelos en {config.GCP_PROJECT_ID} (us-central1) ---")
    
    credentials = None
    if os.path.exists(config.GCP_CREDENTIALS_PATH):
        credentials = service_account.Credentials.from_service_account_file(
            config.GCP_CREDENTIALS_PATH,
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
    
    client = genai.Client(
        vertexai=True, 
        project=config.GCP_PROJECT_ID, 
        location=config.GCP_LOCATION,
        credentials=credentials
    )
    
    try:
        print("Buscando modelos compatibles...")
        # Listamos los modelos disponibles para este proyecto/ubicación
        for model in client.models.list():
            if "gemini" in model.name.lower():
                print(f"✅ Encontrado: {model.name}")
    except Exception as e:
        print(f"❌ Error al listar modelos: {e}")

if __name__ == "__main__":
    list_available_models()
