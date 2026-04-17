import sys
import os
from google import genai
from google.oauth2 import service_account
from config import config
from db import fetch_norma_by_id

def generate_html_summary(op_id):
    # 1. Recuperar datos de Postgres
    print(f"📥 Recuperando datos de la norma {op_id}...")
    norma = fetch_norma_by_id(op_id)
    
    if not norma:
        print(f"❌ No se encontró la norma con ID {op_id}")
        return

    # 2. Configurar el nuevo cliente de GenAI
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
    
    # Formatear fecha
    try:
        from datetime import datetime
        if hasattr(norma['fecha_publicacion'], 'strftime'):
            fecha_formateada = norma['fecha_publicacion'].strftime("%d/%m/%Y")
        else:
            dt = datetime.fromisoformat(str(norma['fecha_publicacion']).split(' ')[0])
            fecha_formateada = dt.strftime("%d/%m/%Y")
    except:
        fecha_formateada = str(norma['fecha_publicacion'])

    # 3. Construir el prompt con el template de n8n
    prompt = f"""
    Analiza la siguiente norma legal del diario oficial El Peruano y genera un resumen ejecutivo.
    
    TIPO: {norma['tipo_dispositivo']}
    NOMBRE: {norma['nombre_dispositivo']}
    TEXTO COMPLETO:
    {norma['texto_completo']}

    Devuelve ÚNICAMENTE código HTML válido, sin markdown, sin bloques de código, sin explicaciones. Usa esta estructura exacta:

    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px;">
      <h2>⚖️ NORMA LEGAL: {norma['nombre_dispositivo']}</h2>
      <p>🗓️ <strong>FECHA:</strong> {fecha_formateada}</p>
      <p>🏛️ <strong>ENTIDAD:</strong> {norma['fuente'] or '[ministerios/sunat/contraloria]'}</p>
      <p>[párrafo introductorio de 2-3 líneas basado en el texto]</p>
      <h3>1. MARCO LEGAL</h3>
      <ul><li>[norma 1 citada]</li><li>[norma 2 citada]</li></ul>
      <h3>2. PRINCIPALES DISPOSICIONES</h3>
      <p>[disposiciones más importantes resumidas]</p>
      <h3>3. RESPONSABILIDADES Y ÁMBITO DE APLICACIÓN</h3>
      <p>[entidades responsables y alcance]</p>
      <h3>4. IMPACTO Y BENEFICIOS</h3>
      <p>[efectos prácticos]</p>
      <p>🇵🇪<a href="{norma['url_web']}">Ver norma completa</a></p>
    </div>
    """

    print("\n🪄 Generando resumen ejecutivo con Gemini 2.5...\n")
    try:
        response = client.models.generate_content(
            model="publishers/google/models/gemini-2.5-flash-lite",
            contents=prompt
        )
        
        # Limpiar posibles delimitadores de markdown si Gemini se equivoca
        html_content = response.text.strip()
        if html_content.startswith("```"):
            # Eliminar bloques de código markdown
            lines = html_content.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            html_content = "\n".join(lines).strip()
        
        print("====================================")
        print(" RESUMEN GENERADO (CÓDIGO HTML)")
        print("====================================\n")
        print(html_content)
        print("\n====================================")
        
    except Exception as e:
        print(f"❌ Error en la generación del resumen: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python generate_summary.py [ID_OP]")
    else:
        op_id = sys.argv[1]
        generate_html_summary(op_id)
