import psycopg2
from config import config

def setup_db():
    try:
        conn = psycopg2.connect(config.DATABASE_URL)
        cursor = conn.cursor()
        print("Conectado a la base de datos...")
        
        # Add column if it doesn't exist
        query = "ALTER TABLE public.normas ADD COLUMN IF NOT EXISTS fecha_vectorizacion TIMESTAMP;"
        cursor.execute(query)
        conn.commit()
        print("✓ Columna 'fecha_vectorizacion' verificada/creada exitosamente en public.normas")
        
    except Exception as e:
        print(f"Error al configurar la tabla: {e}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    setup_db()
