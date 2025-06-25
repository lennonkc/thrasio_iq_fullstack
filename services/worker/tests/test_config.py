#!/usr/bin/env python3
"""Test script to verify GCP configuration."""

import os
import sys
from pathlib import Path

# Add the app directory to Python path
app_dir = Path(__file__).parent.parent / "app"
sys.path.insert(0, str(app_dir))

try:
    from core.config import get_settings
    from google.cloud import bigquery
    import google.auth
    import os
    from dotenv import load_dotenv
    
    print("=== Testing GCP Configuration ===")
    print(f"Current working directory: {os.getcwd()}")
    print(f".env file exists: {os.path.exists('.env')}")
    
    # Load .env file manually
    load_dotenv()
    print(f"GCP_PROJECT_ID env var: {os.getenv('GCP_PROJECT_ID')}")
    print(f"LLM_PROJECT_ID env var: {os.getenv('LLM_PROJECT_ID')}")
    print()
    
    # Load settings
    settings = get_settings()
    print(f"Environment: {settings.environment}")
    print(f"Default GCP Project: {settings.google_cloud.project_id}")
    print(f"BigQuery Project: {settings.google_cloud.bigquery_project_id}")
    print(f"LLM Project: {settings.llm.project_id}")
    print()
    
    # Test Application Default Credentials
    print("=== Testing Application Default Credentials ===")
    try:
        credentials, project = google.auth.default()
        print(f"✅ ADC loaded successfully")
        print(f"Default project: {project}")
        print(f"Credentials type: {type(credentials).__name__}")
    except Exception as e:
        print(f"❌ ADC failed: {e}")
        sys.exit(1)
    print()
    
    # Test BigQuery connection
    print("=== Testing BigQuery Connection ===")
    try:
        bq_options = settings.get_bigquery_client_options()
        print(f"BigQuery options: {bq_options}")
        
        # Create BigQuery client
        client = bigquery.Client(**bq_options)
        
        # Test with a simple query
        query = "SELECT 1 as test_value"
        job = client.query(query)
        results = list(job.result())
        
        print(f"✅ BigQuery connection successful")
        print(f"Test query result: {results[0].test_value}")
        
        # List datasets
        datasets = list(client.list_datasets())
        print(f"Available datasets: {[d.dataset_id for d in datasets[:5]]}")
        
    except Exception as e:
        print(f"❌ BigQuery connection failed: {e}")
    print()
    
    # Test LLM configuration (without actual connection due to permission issues)
    print("=== Testing LLM Configuration ===")
    try:
        llm_options = settings.get_llm_client_options()
        print(f"LLM options: {llm_options}")
        print(f"✅ LLM configuration loaded (connection not tested due to permissions)")
    except Exception as e:
        print(f"❌ LLM configuration failed: {e}")
    print()
    
    print("=== Configuration Summary ===")
    print(f"Default GCP Project: {settings.google_cloud.project_id}")
    print(f"BigQuery Project: {settings.google_cloud.bigquery_project_id}")
    print(f"LLM Project: {settings.llm.project_id}")
    print(f"Using ADC: {not settings.google_cloud.credentials_path}")
    print(f"LLM credentials path: {settings.llm.credentials_path or 'Using ADC'}")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Make sure you're in the correct directory and dependencies are installed")
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()