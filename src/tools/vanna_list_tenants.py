"""
vanna_list_tenants tool - List allowed tenants in multi-tenant mode
"""
from typing import Dict, Any
import logging
from src.config.settings import settings

logger = logging.getLogger(__name__)

async def vanna_list_tenants() -> Dict[str, Any]:
    """
    List allowed tenants and current configuration.
    
    This tool helps users discover:
    - Whether multi-tenant mode is enabled
    - The default tenant ID
    - List of allowed tenants (if restricted)
    - Whether shared knowledge is enabled
    
    Returns:
        Dict containing:
        - multi_tenant_enabled (bool): Whether multi-tenant mode is active
        - default_tenant (str): The default tenant ID
        - allowed_tenants (list): List of allowed tenant IDs
        - all_tenants_allowed (bool): Whether all tenants are allowed
        - shared_knowledge_enabled (bool): Whether shared knowledge is enabled
        - current_database_type (str): Current database type
        
    Example Response:
        {
            "multi_tenant_enabled": true,
            "default_tenant": "zaldey",
            "allowed_tenants": ["zaldey", "singla", "customer1"],
            "all_tenants_allowed": false,
            "shared_knowledge_enabled": true,
            "current_database_type": "bigquery",
            "message": "3 tenants are allowed. Use 'shared' for shared knowledge."
        }
    """
    try:
        # Get configuration
        allowed_list = settings.get_allowed_tenants()
        all_allowed = len(allowed_list) == 0
        
        # Build response
        response = {
            "multi_tenant_enabled": settings.ENABLE_MULTI_TENANT,
            "default_tenant": settings.TENANT_ID,
            "allowed_tenants": allowed_list if allowed_list else [],
            "all_tenants_allowed": all_allowed,
            "shared_knowledge_enabled": settings.ENABLE_SHARED_KNOWLEDGE,
            "current_database_type": settings.DATABASE_TYPE
        }
        
        # Add helpful message
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
        
        # Add usage examples
        response["usage_examples"] = []
        
        if settings.ENABLE_MULTI_TENANT:
            if allowed_list and len(allowed_list) > 1:
                # Show example with different tenant
                other_tenant = allowed_list[1] if allowed_list[0] == settings.TENANT_ID else allowed_list[0]
                response["usage_examples"].extend([
                    {
                        "description": "Query with default tenant",
                        "tool": "vanna_ask",
                        "params": {"query": "Show total sales"}
                    },
                    {
                        "description": f"Query with tenant '{other_tenant}'",
                        "tool": "vanna_ask",
                        "params": {"query": "Show total sales", "tenant_id": other_tenant}
                    }
                ])
            
            if settings.ENABLE_SHARED_KNOWLEDGE:
                response["usage_examples"].append({
                    "description": "Train shared knowledge",
                    "tool": "vanna_train",
                    "params": {
                        "training_type": "documentation",
                        "content": "Best practices for all tenants",
                        "is_shared": True
                    }
                })
        
        logger.info("Listed tenant configuration")
        return response
        
    except Exception as e:
        logger.error(f"Error in vanna_list_tenants: {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "error_type": type(e).__name__,
            "suggestions": ["Check configuration", "Verify settings"]
        }

# Tool definition for FastMCP
tool_definition = {
    "name": "vanna_list_tenants",
    "description": "List allowed tenants and multi-tenant configuration",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": []
    }
}