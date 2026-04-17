import sys
import os
from google import genai
from google.oauth2 import service_account
from config import config
from embeddings import get_embedding_model
from vector_search import search_nearest_neighbors
from db import get_normas_by_ids

def run_query(user_query):
    print(f"🔍 Buscando: {user_query}")
    
    # 1. Generar embedding de la consulta (seguimos usando embeddings.py que funciona bien)
    model_emb = get_embedding_model()
    query_vector = model_emb.get_embeddings([user_query])[0].values
    
    # 2. Buscar en Vector Search
    neighbor_ids = search_nearest_neighbors(query_vector, num_neighbors=3)
    if not neighbor_ids:
        print("No se encontraron resultados relevantes.")
        return

    # 3. Hidratar desde Postgres
    normas = get_normas_by_ids(neighbor_ids)
    if not normas:
        print("No se pudo recuperar la información de la base de datos.")
        return

    # 4. Inferencia con la nueva librería google-genai
    print("\n🧠 Pensando respuesta con Gemini 2.0...")
    
    # Configurar credenciales y cliente
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
    
    # Construir el contexto
    contexto = "\n\n".join([
        f"CONTENIDO DE LA NORMA {n['op']} ({n['nombre_dispositivo']}):\n{n['texto_completo'][:10000]}" 
        for n in normas
    ])
    
    prompt = f"""
    Eres un asistente legal experto en normas peruanas. 
    A continuación tienes fragmentos de normas legales recuperados de una base de datos.
    Responde a la pregunta del usuario basándote únicamente en este contexto relevante.
    
    CONTEXTO:
    {contexto}
    
    PREGUNTA DEL USUARIO:
    {user_query}
    """
    
    try:
        response = client.models.generate_content(
            model="publishers/google/models/gemini-2.5-flash-lite",
            contents=prompt
        )
        
        print("\n====================================")
        print(" RESPUESTA DE LA IA")
        print("====================================\n")
        print(response.text)
        print("\n------------------------------------")
        print("Fuentes consultadas:")
        for n in normas:
            print(f"- {n['nombre_dispositivo']} (OP: {n['op']})")
            
    except Exception as e:
        print(f"❌ Error en la generación con Gemini 2.0: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python query_rag.py \"tu pregunta aqui\"")
    else:
        query = " ".join(sys.argv[1:])
        run_query(query)
