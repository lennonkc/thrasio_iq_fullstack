#!/usr/bin/env python3
"""Test script to verify package imports after updates."""

import sys
import os

# Add the worker directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # Test pydantic imports
    from pydantic import BaseModel, Field
    print("✓ Pydantic imported successfully")
    
    # Test pydantic-settings import
    from pydantic_settings import BaseSettings
    print("✓ Pydantic-settings imported successfully")
    
    # Test config import
    from app.core.config import settings
    print("✓ Config loaded successfully")
    
    # Test pandas import
    import pandas as pd
    print("✓ Pandas imported successfully")
    
    # Test numpy import
    import numpy as np
    print("✓ Numpy imported successfully")
    
    # Test google cloud imports
    from google.cloud import bigquery
    print("✓ Google Cloud BigQuery imported successfully")
    
    # Test langgraph imports
    from langgraph.graph import StateGraph
    print("✓ LangGraph imported successfully")
    
    print("\n🎉 All package imports successful!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    sys.exit(1)