import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.cloud import aiplatform
from config import config

def cleanup():
    # Usar el ID de proyecto como string si es posible, o el número
    project = config.GCP_PROJECT_ID 
    location = config.GCP_LOCATION
    
    print(f"Iniciando limpieza en Proyecto: {project}, Localización: {location}")
    aiplatform.init(project=project, location=location)
    
    # Intentar listar
    endpoints = aiplatform.MatchingEngineIndexEndpoint.list()
    indexes = aiplatform.MatchingEngineIndex.list()
    
    print(f"Encontrados {len(endpoints)} Endpoints y {len(indexes)} Índices vía list().")
    
    # 1. Borrar Endpoints
    for e in endpoints:
        print(f"Eliminando Endpoint: {e.display_name} ({e.resource_name})")
        for di in e.deployed_indexes:
            print(f"  - Undeploying {di.id}...")
            try:
                e.undeploy_index(deployed_index_id=di.id)
            except Exception as ex: print(f"    Error: {ex}")
        try:
            e.delete(force=True)
            print("  - Eliminado.")
        except Exception as ex: print(f"    Error: {ex}")

    # 2. Borrar Índices
    for i in indexes:
        print(f"Eliminando Índice: {i.display_name} ({i.resource_name})")
        try:
            i.delete()
            print("  - Eliminado.")
        except Exception as ex: print(f"    Error: {ex}")

    # 3. Intentar borrar por los IDs conocidos del log si no se borraron arriba
    known_indexes = ["1771385800114569216"]
    known_endpoints = ["8466461635224010752", "3430029876940242944"]
    
    print("\n--- Intento de borrado por IDs conocidos del log ---")
    for eid in known_endpoints:
        try:
            e = aiplatform.MatchingEngineIndexEndpoint(eid)
            print(f"Encontrado Endpoint por ID: {eid}. Eliminando...")
            for di in e.deployed_indexes:
                e.undeploy_index(deployed_index_id=di.id)
            e.delete(force=True)
        except Exception: pass

    for iid in known_indexes:
        try:
            i = aiplatform.MatchingEngineIndex(iid)
            print(f"Encontrado Índice por ID: {iid}. Eliminando...")
            i.delete()
        except Exception: pass

    print("\nLimpieza finalizada.")

if __name__ == "__main__":
    cleanup()
