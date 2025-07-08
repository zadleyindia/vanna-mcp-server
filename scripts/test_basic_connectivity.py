#!/usr/bin/env python3
"""
Test basic connectivity and multi-tenant configuration
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import settings and vanna config
from src.config.settings import settings
from src.config.vanna_config import get_vanna

def test_basic_connectivity():
    """Test basic connectivity and configuration"""
    print("=== Basic Connectivity Test ===\n")
    
    # Check environment variables
    print("1. Environment Configuration:")
    print(f"   - SUPABASE_URL: {'Set' if os.getenv('SUPABASE_URL') else 'Not set'}")
    print(f"   - SUPABASE_KEY: {'Set' if os.getenv('SUPABASE_KEY') else 'Not set'}")
    print(f"   - OPENAI_API_KEY: {'Set' if os.getenv('OPENAI_API_KEY') else 'Not set'}")
    print(f"   - BIGQUERY_PROJECT: {os.getenv('BIGQUERY_PROJECT', 'Not set')}")
    print(f"   - TENANT_ID: {os.getenv('TENANT_ID', 'Not set')}")
    print(f"   - ENABLE_MULTI_TENANT: {os.getenv('ENABLE_MULTI_TENANT', 'Not set')}")
    print()
    
    # Check settings
    print("2. Settings Configuration:")
    print(f"   - Database Type: {settings.DATABASE_TYPE}")
    print(f"   - Schema: {settings.VANNA_SCHEMA}")
    print(f"   - Multi-tenant Enabled: {settings.ENABLE_MULTI_TENANT}")
    print(f"   - Default Tenant: {settings.TENANT_ID}")
    print(f"   - Allowed Tenants: {settings.get_allowed_tenants()}")
    print(f"   - Shared Knowledge: {settings.ENABLE_SHARED_KNOWLEDGE}")
    print()
    
    # Validate configuration
    print("3. Configuration Validation:")
    config_status = settings.validate_config()
    print(f"   - Valid: {config_status['valid']}")
    if config_status['errors']:
        print("   - Errors:")
        for error in config_status['errors']:
            print(f"     • {error}")
    if config_status['warnings']:
        print("   - Warnings:")
        for warning in config_status['warnings']:
            print(f"     • {warning}")
    print()
    
    # Test Vanna initialization
    print("4. Vanna Initialization:")
    try:
        vn = get_vanna()
        print("   ✓ Vanna initialized successfully")
        
        # Check if we can access the database
        if hasattr(vn, 'run_sql'):
            # Test database connection
            test_query = "SELECT 1 as test"
            try:
                result = vn.run_sql(test_query)
                print("   ✓ Database connection successful")
            except Exception as e:
                print(f"   ✗ Database connection failed: {e}")
        
    except Exception as e:
        print(f"   ✗ Failed to initialize Vanna: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_basic_connectivity()