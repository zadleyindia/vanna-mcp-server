"""
vanna_get_training_data tool - View and manage existing training data
Priority #7 tool in our implementation
"""
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
from src.config.vanna_config import get_vanna
from src.config.settings import settings
import json

logger = logging.getLogger(__name__)

async def vanna_get_training_data(
    tenant_id: Optional[str] = None,
    training_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    include_shared: Optional[bool] = None,
    search_query: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc"
) -> Dict[str, Any]:
    """
    Retrieve existing training data with filtering and search capabilities.
    
    This tool allows administrators to view and analyze training data, helping to
    identify quality issues, duplicates, or outdated information that needs updating.
    
    Args:
        tenant_id (str, optional): Override default tenant (for multi-tenant mode)
            Default: None (uses settings.TENANT_ID)
            
        training_type (str, optional): Filter by type of training data
            - "ddl": DDL statements  
            - "documentation": Business documentation
            - "sql": SQL query examples
            Default: None (return all types)
            
        limit (int): Maximum number of items to return
            Default: 50 (max: 100)
            
        offset (int): Number of items to skip for pagination
            Default: 0
            
        include_shared (bool, optional): Include shared knowledge in results
            Default: None (respects ENABLE_SHARED_KNOWLEDGE setting)
            
        search_query (str, optional): Search within training data content
            Default: None (no search filter)
            
        sort_by (str): Field to sort results by
            - "created_at": Creation timestamp (default)
            - "type": Training data type
            - "tenant": Tenant ID
            Default: "created_at"
            
        sort_order (str): Sort direction
            - "asc": Ascending order
            - "desc": Descending order (default)
            Default: "desc"
    
    Returns:
        Dict containing:
        - training_data (list): List of training data items
        - total_count (int): Total number of matching items
        - returned_count (int): Number of items in this response
        - has_more (bool): Whether more items are available
        - filters_applied (dict): Active filters
        - tenant_id (str): Tenant context (if multi-tenant)
        - metadata (dict): Additional execution metadata
        
    Example Usage:
        # Get all DDL training data for current tenant
        vanna_get_training_data(
            training_type="ddl",
            limit=20
        )
        
        # Search for sales-related training data
        vanna_get_training_data(
            search_query="sales",
            include_shared=True
        )
        
        # Get paginated SQL examples
        vanna_get_training_data(
            training_type="sql",
            limit=10,
            offset=20,
            sort_by="created_at",
            sort_order="asc"
        )
    """
    try:
        vn = get_vanna()
        
        # 1. TENANT VALIDATION (MANDATORY)
        if settings.ENABLE_MULTI_TENANT:
            # Use default tenant if not provided
            if not tenant_id:
                tenant_id = settings.TENANT_ID
                logger.info(f"No tenant_id provided, using default: {tenant_id}")
            
            # Validate tenant_id
            if not tenant_id:
                return {
                    "success": False,
                    "error": "tenant_id is required when multi-tenant is enabled",
                    "allowed_tenants": settings.get_allowed_tenants()
                }
            
            if not settings.is_tenant_allowed(tenant_id):
                allowed = settings.get_allowed_tenants()
                return {
                    "success": False,
                    "error": f"Tenant '{tenant_id}' is not allowed",
                    "allowed_tenants": allowed if allowed else "All tenants allowed"
                }
        
        # 2. INPUT VALIDATION
        # Validate limit
        if limit > 100:
            limit = 100
            logger.warning("Limit exceeded 100, capping at maximum allowed")
        if limit < 1:
            limit = 1
        
        # Validate offset
        if offset < 0:
            offset = 0
        
        # Validate training_type
        valid_types = ["ddl", "documentation", "sql"]
        if training_type and training_type not in valid_types:
            return {
                "success": False,
                "error": f"Invalid training_type: {training_type}",
                "valid_types": valid_types,
                "suggestions": ["Use one of the valid training types", "Leave empty to get all types"]
            }
        
        # Validate sort_by
        valid_sort_fields = ["created_at", "type", "tenant"]
        if sort_by not in valid_sort_fields:
            sort_by = "created_at"
        
        # Validate sort_order
        if sort_order not in ["asc", "desc"]:
            sort_order = "desc"
        
        # 3. DATABASE TYPE AWARENESS
        database_type = settings.DATABASE_TYPE
        logger.info(f"Getting training data for database type: {database_type}, tenant: {tenant_id}")
        
        # 4. RETRIEVE TRAINING DATA
        training_data, total_count = _retrieve_training_data(
            vn=vn,
            tenant_id=tenant_id,
            training_type=training_type,
            limit=limit,
            offset=offset,
            include_shared=include_shared,
            search_query=search_query,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        # 5. FORMAT TRAINING DATA
        formatted_data = []
        for item in training_data:
            formatted_item = _format_training_item(item)
            formatted_data.append(formatted_item)
        
        # 6. PREPARE RESPONSE
        result = {
            "success": True,
            "training_data": formatted_data,
            "total_count": total_count,
            "returned_count": len(formatted_data),
            "has_more": (offset + len(formatted_data)) < total_count,
            "pagination": {
                "limit": limit,
                "offset": offset,
                "next_offset": offset + len(formatted_data) if (offset + len(formatted_data)) < total_count else None
            },
            "filters_applied": {
                "training_type": training_type,
                "search_query": search_query,
                "include_shared": include_shared if include_shared is not None else settings.ENABLE_SHARED_KNOWLEDGE,
                "sort_by": sort_by,
                "sort_order": sort_order
            }
        }
        
        # 7. METADATA (MANDATORY)
        result.update({
            "tenant_id": tenant_id if settings.ENABLE_MULTI_TENANT else None,
            "database_type": database_type,
            "timestamp": datetime.now().isoformat(),
            "shared_knowledge_enabled": settings.ENABLE_SHARED_KNOWLEDGE if settings.ENABLE_MULTI_TENANT else None,
            "strict_isolation": settings.STRICT_TENANT_ISOLATION if settings.ENABLE_MULTI_TENANT else None
        })
        
        logger.info(f"Successfully retrieved {len(formatted_data)} training items (total: {total_count})")
        return result
        
    except Exception as e:
        logger.error(f"Error in vanna_get_training_data: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": f"Training data retrieval error: {str(e)}",
            "error_type": type(e).__name__,
            "suggestions": [
                "Check database connection",
                "Verify tenant permissions",
                "Try with different filters"
            ]
        }

def _retrieve_training_data(vn, tenant_id: Optional[str], training_type: Optional[str],
                           limit: int, offset: int, include_shared: Optional[bool],
                           search_query: Optional[str], sort_by: str, sort_order: str) -> tuple:
    """Retrieve training data from database with filters"""
    try:
        conn = vn.conn
        cur = conn.cursor()
        
        # Build base query
        base_query = f"""
            SELECT id, training_data_type, content, metadata, created_at
            FROM {vn.schema_name}.training_data
            WHERE 1=1
        """
        
        # Count query
        count_query = f"""
            SELECT COUNT(*)
            FROM {vn.schema_name}.training_data
            WHERE 1=1
        """
        
        params = []
        
        # Add training type filter
        if training_type:
            base_query += " AND training_data_type = %s"
            count_query += " AND training_data_type = %s"
            params.append(training_type)
        
        # Add tenant filtering if enabled
        if settings.ENABLE_MULTI_TENANT and tenant_id:
            # Determine if we should include shared knowledge
            include_shared_final = include_shared if include_shared is not None else settings.ENABLE_SHARED_KNOWLEDGE
            
            if include_shared_final:
                # Include both tenant-specific and shared data
                base_query += " AND (metadata->>'tenant_id' = %s OR metadata->>'is_shared' = 'true')"
                count_query += " AND (metadata->>'tenant_id' = %s OR metadata->>'is_shared' = 'true')"
                params.append(tenant_id)
            else:
                # Only tenant-specific data
                base_query += " AND metadata->>'tenant_id' = %s"
                count_query += " AND metadata->>'tenant_id' = %s"
                params.append(tenant_id)
        
        # Add search filter if provided
        if search_query:
            base_query += " AND content ILIKE %s"
            count_query += " AND content ILIKE %s"
            params.append(f"%{search_query}%")
        
        # Get total count
        cur.execute(count_query, params)
        total_count = cur.fetchone()[0]
        
        # Add sorting
        sort_column = {
            "created_at": "created_at",
            "type": "training_data_type",
            "tenant": "metadata->>'tenant_id'"
        }.get(sort_by, "created_at")
        
        base_query += f" ORDER BY {sort_column} {sort_order.upper()}"
        
        # Add pagination
        base_query += " LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        # Execute main query
        cur.execute(base_query, params)
        results = cur.fetchall()
        
        cur.close()
        
        # Format results
        training_data = []
        for row in results:
            training_data.append({
                "id": str(row[0]),
                "type": row[1],
                "content": row[2],
                "metadata": row[3] if row[3] else {},
                "created_at": row[4].isoformat() if row[4] else None
            })
        
        return training_data, total_count
        
    except Exception as e:
        logger.error(f"Error retrieving training data: {e}")
        raise

def _format_training_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Format a training data item for response"""
    formatted = {
        "id": item["id"],
        "type": item["type"],
        "created_at": item["created_at"]
    }
    
    # Format content based on type
    content = item["content"]
    metadata = item["metadata"]
    
    if item["type"] == "ddl":
        # For DDL, show table name and column count if available
        if "normalized_schema" in metadata:
            schema_info = metadata["normalized_schema"]
            formatted["table_name"] = f"{schema_info.get('dataset', 'unknown')}.{schema_info.get('table_name', 'unknown')}"
            formatted["column_count"] = len(schema_info.get("columns", []))
            formatted["description"] = schema_info.get("description", "")[:100]
        else:
            # Try to extract table name from DDL
            formatted["content_preview"] = content[:200] + "..." if len(content) > 200 else content
    
    elif item["type"] == "documentation":
        # For documentation, show preview
        formatted["content_preview"] = content[:200] + "..." if len(content) > 200 else content
        formatted["length"] = len(content)
    
    elif item["type"] == "sql":
        # For SQL, show the question and SQL preview
        formatted["question"] = metadata.get("question", "No question provided")
        formatted["sql_preview"] = content[:150] + "..." if len(content) > 150 else content
        formatted["validated"] = metadata.get("validated", False)
    
    # Add metadata fields
    formatted["tenant_id"] = metadata.get("tenant_id")
    formatted["is_shared"] = metadata.get("is_shared", False)
    formatted["database_type"] = metadata.get("database_type")
    
    # Add any additional metadata
    if "added_by" in metadata:
        formatted["added_by"] = metadata["added_by"]
    if "last_used" in metadata:
        formatted["last_used"] = metadata["last_used"]
    if "usage_count" in metadata:
        formatted["usage_count"] = metadata["usage_count"]
    
    return formatted

# Tool definition for FastMCP
tool_definition = {
    "name": "vanna_get_training_data",
    "description": "View and manage existing training data with filtering and search",
    "input_schema": {
        "type": "object",
        "properties": {
            "tenant_id": {
                "type": "string",
                "description": "Tenant ID for multi-tenant mode (optional)"
            },
            "training_type": {
                "type": "string",
                "enum": ["ddl", "documentation", "sql"],
                "description": "Filter by type of training data"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of items to return (max: 100)",
                "default": 50
            },
            "offset": {
                "type": "integer",
                "description": "Number of items to skip for pagination",
                "default": 0
            },
            "include_shared": {
                "type": "boolean",
                "description": "Include shared knowledge in results"
            },
            "search_query": {
                "type": "string",
                "description": "Search within training data content"
            },
            "sort_by": {
                "type": "string",
                "enum": ["created_at", "type", "tenant"],
                "description": "Field to sort results by",
                "default": "created_at"
            },
            "sort_order": {
                "type": "string",
                "enum": ["asc", "desc"],
                "description": "Sort direction",
                "default": "desc"
            }
        },
        "required": []
    }
}