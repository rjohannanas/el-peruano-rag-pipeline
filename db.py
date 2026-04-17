import psycopg2
from datetime import date, datetime
from config import config

def get_db_connection():
    """Establece y devuelve la conexión a Cloud SQL/PostgreSQL usando psycopg2 y DATABASE_URL."""
    if not config.DATABASE_URL:
        raise ValueError("DATABASE_URL no está configurado en las variables de entorno.")
    return psycopg2.connect(config.DATABASE_URL)

def fetch_pending_normas(limit=50):
    """
    Extrae normas que no han sido vectorizadas aún.
    Busca normas donde texto_completo no sea nulo y fecha_vectorizacion sea NULL.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    # NOTA: Asegúrate de correr en DB: ALTER TABLE public.normas ADD COLUMN fecha_vectorizacion TIMESTAMP;
    query = """
        SELECT op, nombre_dispositivo, texto_completo, fecha_publicacion, entidad_id, tipo_dispositivo, fuente
        FROM public.normas 
        WHERE texto_completo IS NOT NULL 
          AND fecha_vectorizacion IS NULL
    """
    if limit:
        query += f" LIMIT {limit}"

    try:
        cursor.execute(query)
        rows = cursor.fetchall()

        normas = []
        for op, nombre, texto, fecha, entidad, tipo, fuente in rows:
            normas.append({
                "op": op,
                "nombre_dispositivo": nombre,
                "texto_completo": texto,
                "fecha_publicacion": fecha.isoformat() if isinstance(fecha, (date, datetime)) else str(fecha),
                "entidad_id": entidad,
                "tipo_dispositivo": tipo,
                "fuente": fuente
            })
        return normas
    except Exception as e:
        print(f"Error extrayendo normas: {e}")
        return []
    finally:
        cursor.close()
        conn.close()


def mark_normas_as_vectorized(op_ids):
    """
    Actualiza la fecha_vectorizacion para los IDs indicados.
    Se usa después de que se confirma que subieron a Vertex AI.
    """
    if not op_ids:
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        UPDATE public.normas
        SET fecha_vectorizacion = CURRENT_TIMESTAMP
        WHERE op = ANY(%s)
    """
    try:
        cursor.execute(query, (op_ids,))
        conn.commit()
        print(f"✓ {cursor.rowcount} normas marcadas como vectorizadas en la DB.")
    except Exception as e:
        print(f"Error actualizando normas vectorizadas: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()
def fetch_norma_by_id(op_id):
    """
    Recupera todos los campos de una norma específica por su ID (op).
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT op, nombre_dispositivo, tipo_dispositivo, fecha_publicacion, sumilla, texto_completo, url_web, url_pdf, entidad_id, fuente
        FROM public.normas
        WHERE op = %s
    """
    try:
        cursor.execute(query, (op_id,))
        row = cursor.fetchone()
        if row:
            return {
                "op": row[0],
                "nombre_dispositivo": row[1],
                "tipo_dispositivo": row[2],
                "fecha_publicacion": row[3],
                "sumilla": row[4],
                "texto_completo": row[5],
                "url_web": row[6],
                "url_pdf": row[7],
                "entidad_id": row[8],
                "fuente": row[9]
            }
        return None
    except Exception as e:
        print(f"Error recuperando norma {op_id}: {e}")
        return None
    finally:
        cursor.close()
        conn.close()

def get_normas_by_ids(op_ids):
    """
    Recupera múltiples normas por sus IDs.
    """
    if not op_ids:
        return []
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT op, nombre_dispositivo, tipo_dispositivo, fecha_publicacion, sumilla, texto_completo, url_web, url_pdf, entidad_id, fuente
        FROM public.normas
        WHERE op = ANY(%s)
    """
    try:
        cursor.execute(query, (op_ids,))
        rows = cursor.fetchall()
        normas = []
        for row in rows:
            normas.append({
                "op": row[0],
                "nombre_dispositivo": row[1],
                "tipo_dispositivo": row[2],
                "fecha_publicacion": row[3],
                "sumilla": row[4],
                "texto_completo": row[5],
                "url_web": row[6],
                "url_pdf": row[7],
                "entidad_id": row[8],
                "fuente": row[9]
            })
        return normas
    except Exception as e:
        print(f"Error recuperando normas: {e}")
        return []
    finally:
        cursor.close()
        conn.close()
