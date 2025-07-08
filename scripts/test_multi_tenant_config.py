#!/usr/bin/env python3
"""
Test multi-tenant configuration without database connection
This simulates what vanna_list_tenants tool would return
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

def test_multi_tenant_config():
    """Test multi-tenant configuration without requiring database connection"""
    print("=== Multi-Tenant Configuration Test ===\n")
    
    # Set some test environment variables to simulate configuration
    test_configs = [
        {
            "name": "Default Configuration (No Multi-tenant)",
            "env": {
                "ENABLE_MULTI_TENANT": "false",
                "TENANT_ID": "",
                "ALLOWED_TENANTS": "",
                "ENABLE_SHARED_KNOWLEDGE": "true"
            }
        },
        {
            "name": "Multi-tenant with Specific Allowed Tenants",
            "env": {
                "ENABLE_MULTI_TENANT": "true",
                "TENANT_ID": "zaldey",
                "ALLOWED_TENANTS": "zaldey,singla,customer1",
                "ENABLE_SHARED_KNOWLEDGE": "true"
            }
        },
        {
            "name": "Multi-tenant with All Tenants Allowed",
            "env": {
                "ENABLE_MULTI_TENANT": "true",
                "TENANT_ID": "default-tenant",
                "ALLOWED_TENANTS": "",
                "ENABLE_SHARED_KNOWLEDGE": "true"
            }
        }
    ]
    
    for config in test_configs:
        print(f"\n--- {config['name']} ---")
        
        # Save current env
        saved_env = {}
        for key in config['env']:
            saved_env[key] = os.environ.get(key)
        
        # Set test env
        for key, value in config['env'].items():
            if value:
                os.environ[key] = value
            elif key in os.environ:
                del os.environ[key]
        
        # Import settings fresh for each config
        import importlib
        if 'src.config.settings' in sys.modules:
            importlib.reload(sys.modules['src.config.settings'])
        
        from src.config.settings import settings
        
        # Simulate vanna_list_tenants response
        allowed_list = settings.get_allowed_tenants()
        all_allowed = len(allowed_list) == 0
        
        response = {
            "multi_tenant_enabled": settings.ENABLE_MULTI_TENANT,
            "default_tenant": settings.TENANT_ID,
            "allowed_tenants": allowed_list if allowed_list else [],
            "all_tenants_allowed": all_allowed,
            "shared_knowledge_enabled": settings.ENABLE_SHARED_KNOWLEDGE,
            "current_database_type": settings.DATABASE_TYPE
        }
        
        # Add message
        if not settings.ENABLE_MULTI_TENANT:
            response["message"] = "Multi-tenant mode is disabled. Tenant parameters are ignored."
        elif all_allowed:
            response["message"] = "All tenant IDs are allowed (no restrictions)."
            if settings.ENABLE_SHARED_KNOWLEDGE:
                response["message"] += " Use tenant_id='shared' for shared knowledge."
        else:
            response["message"] = f"{len(allowed_list)} tenants are allowed."
            if settings.ENABLE_SHARED_KNOWLEDGE:
                response["message"] += " Use tenant_id='shared' for shared knowledge."
        
        # Print response
        print(f"Response that vanna_list_tenants would return:")
        for key, value in response.items():
            print(f"  {key}: {value}")
        
        # Restore env
        for key, value in saved_env.items():
            if value is not None:
                os.environ[key] = value
            elif key in os.environ:
                del os.environ[key]
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    test_multi_tenant_config()