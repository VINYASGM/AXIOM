"""
Generate OpenAPI Documentation

Extracts OpenAPI JSON from the FastAPI application and saves it to docs/.
"""
import os
import sys
import json
import yaml

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

def generate_docs():
    """Generate OpenAPI specs."""
    openapi_schema = app.openapi()
    
    # Ensure docs directory exists
    docs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "docs")
    # Actually, simpler path: ../../docs relative to services/ai/scripts
    # services/ai/scripts -> services/ai -> services -> root -> docs ??
    # AXIOM/docs
    
    # Let's just put it in services/ai/docs for now
    docs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs")
    os.makedirs(docs_dir, exist_ok=True)
    
    # Save JSON
    json_path = os.path.join(docs_dir, "openapi.json")
    with open(json_path, "w") as f:
        json.dump(openapi_schema, f, indent=2)
    print(f"Generated {json_path}")
    
    # Save YAML
    yaml_path = os.path.join(docs_dir, "openapi.yaml")
    with open(yaml_path, "w") as f:
        yaml.dump(openapi_schema, f, sort_keys=False)
    print(f"Generated {yaml_path}")

if __name__ == "__main__":
    generate_docs()
