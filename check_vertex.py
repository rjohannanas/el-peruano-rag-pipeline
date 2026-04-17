from google.cloud import aiplatform
from config import config as app_config

def check_resources():
    aiplatform.init(project=app_config.GCP_PROJECT_ID, location=app_config.GCP_LOCATION)
    
    print("--- INDEX ENDPOINTS ---")
    endpoints = aiplatform.MatchingEngineIndexEndpoint.list()
    for e in endpoints:
        print(f"Endpoint: {e.display_name} ({e.resource_name})")
        if e.deployed_indexes:
            for di in e.deployed_indexes:
                print(f"  - Deployed Index ID: {di.deployed_index_id}")
                print(f"    Index Resource: {di.index}")
                # Check for automatic_resources or dedicated_resources
                if hasattr(di, 'automatic_resources'):
                    print(f"    Min/Max Replicas: {di.automatic_resources.min_replica_count}/{di.automatic_resources.max_replica_count}")
                elif hasattr(di, 'dedicated_resources'):
                    # Manually check fields if object structure is complex
                    try:
                        print(f"    Machine Type: {di.dedicated_resources.machine_spec.machine_type}")
                        print(f"    Min Replicas: {di.dedicated_resources.min_replica_count}")
                    except:
                        print("    (Dedicated resources info unavailable)")
        else:
            print("  - No indexes deployed.")
    
    print("\n--- INDEXES ---")
    indexes = aiplatform.MatchingEngineIndex.list()
    for i in indexes:
        print(f"Index: {i.display_name} ({i.resource_name})")
        d = i.to_dict()
        print(f"    Update Method: {d.get('indexUpdateMethod', 'N/A')}")

if __name__ == "__main__":
    check_resources()
