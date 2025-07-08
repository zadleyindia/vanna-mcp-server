"""
vanna_get_schemas tool - Display database structure and schemas
Priority #6 tool in our implementation
"""
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
from src.config.vanna_config import get_vanna
from src.config.settings import settings
import json

logger = logging.getLogger(__name__)

async def vanna_get_schemas(
    tenant_id: Optional[str] = None,
    include_metadata: bool = True,
    include_sample_values: bool = False,
    table_filter: Optional[str] = None,
    format_output: str = "hierarchical"
) -> Dict[str, Any]:
    """
    Get database schemas and table structures accessible to the tenant.
    
    This tool retrieves the database structure including tables, columns, and their
    metadata. It respects multi-tenant isolation and only shows schemas/tables
    accessible to the current tenant.
    
    Args:
        tenant_id (str, optional): Override default tenant (for multi-tenant mode)
            Default: None (uses settings.TENANT_ID)
            
        include_metadata (bool): Include detailed metadata like data types and descriptions
            Default: True
            
        include_sample_values (bool): Include sample values for columns (if available)
            Default: False
            
        table_filter (str, optional): Filter tables by name pattern (supports wildcards)
            Default: None (show all accessible tables)
            Example: "sales*" to show only tables starting with "sales"
            
        format_output (str): Output format for schema information
            - "hierarchical": Grouped by dataset/schema (default)
            - "flat": Simple list of all tables
            - "detailed": Maximum detail with all metadata
            Default: "hierarchical"
    
    Returns:
        Dict containing:
        - schemas (dict/list): Database schemas and table structures
        - table_count (int): Total number of accessible tables
        - column_count (int): Total number of columns across all tables
        - tenant_id (str): Tenant context (if multi-tenant)
        - database_type (str): Type of database (e.g., "bigquery")
        - metadata (dict): Additional execution metadata
        
    Example Usage:
        # Get all schemas for current tenant
        vanna_get_schemas()
        
        # Get only sales-related tables with full details
        vanna_get_schemas(
            table_filter="sales*",
            include_sample_values=True,
            format_output="detailed"
        )
        
        # Get flat list of all tables without metadata
        vanna_get_schemas(
            include_metadata=False,
            format_output="flat"
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
        
        # 2. DATABASE TYPE VALIDATION
        database_type = settings.DATABASE_TYPE
        logger.info(f"Getting schemas for database type: {database_type}, tenant: {tenant_id}")
        
        # 3. RETRIEVE SCHEMA INFORMATION
        # Get DDL training data which contains schema information
        all_ddls = _get_ddl_training_data(vn, tenant_id)
        
        # Parse schemas from DDL data
        schemas = _parse_schemas_from_ddl(all_ddls, table_filter)
        
        # 4. FORMAT OUTPUT BASED ON REQUEST
        formatted_output = _format_schema_output(schemas, format_output, include_metadata, include_sample_values)
        
        # 5. CALCULATE STATISTICS
        table_count = sum(len(tables) for tables in schemas.values())
        column_count = sum(
            len(table_info.get("columns", [])) 
            for table_list in schemas.values() 
            for table_info in table_list.values()
        )
        
        # 6. PREPARE RESPONSE
        result = {
            "success": True,
            "schemas": formatted_output,
            "table_count": table_count,
            "column_count": column_count,
            "format": format_output
        }
        
        # 7. METADATA (MANDATORY)
        if include_metadata:
            result.update({
                "tenant_id": tenant_id if settings.ENABLE_MULTI_TENANT else None,
                "database_type": database_type,
                "timestamp": datetime.now().isoformat(),
                "shared_knowledge_enabled": settings.ENABLE_SHARED_KNOWLEDGE if settings.ENABLE_MULTI_TENANT else None,
                "strict_isolation": settings.STRICT_TENANT_ISOLATION if settings.ENABLE_MULTI_TENANT else None,
                "filter_applied": table_filter if table_filter else None
            })
        
        logger.info(f"Successfully retrieved {table_count} tables with {column_count} columns")
        return result
        
    except Exception as e:
        logger.error(f"Error in vanna_get_schemas: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": f"Schema retrieval error: {str(e)}",
            "error_type": type(e).__name__,
            "suggestions": [
                "Check database connection",
                "Verify tenant permissions",
                "Ensure DDL training data exists"
            ]
        }

def _get_ddl_training_data(vn, tenant_id: Optional[str]) -> List[Dict[str, Any]]:
    """Retrieve DDL training data respecting tenant isolation"""
    try:
        # Use Vanna's connection to query training data
        conn = vn.conn
        cur = conn.cursor()
        
        # Query for DDL training data with tenant filtering
        query = f"""
            SELECT id, content, metadata
            FROM {vn.schema_name}.training_data
            WHERE training_data_type = 'ddl'
        """
        
        # Add tenant filtering if enabled
        if settings.ENABLE_MULTI_TENANT and tenant_id:
            if settings.ENABLE_SHARED_KNOWLEDGE:
                # Include both tenant-specific and shared DDLs
                query += f" AND (metadata->>'tenant_id' = %s OR metadata->>'is_shared' = 'true')"
                cur.execute(query, (tenant_id,))
            else:
                # Only tenant-specific DDLs
                query += f" AND metadata->>'tenant_id' = %s"
                cur.execute(query, (tenant_id,))
        else:
            cur.execute(query)
        
        results = cur.fetchall()
        cur.close()
        
        # Format results
        ddls = []
        for row in results:
            ddls.append({
                "id": str(row[0]),
                "content": row[1],
                "metadata": row[2] if row[2] else {}
            })
        
        return ddls
        
    except Exception as e:
        logger.error(f"Error retrieving DDL data: {e}")
        return []

def _parse_schemas_from_ddl(ddls: List[Dict[str, Any]], table_filter: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """Parse schema information from DDL statements"""
    schemas = {}
    
    for ddl_data in ddls:
        content = ddl_data.get("content", "")
        metadata = ddl_data.get("metadata", {})
        
        # Extract normalized schema if available (from our secure DDL training)
        if "normalized_schema" in metadata:
            schema_info = metadata["normalized_schema"]
            dataset = schema_info.get("dataset", "default")
            table_name = schema_info.get("table_name", "")
            
            # Apply table filter if specified
            if table_filter and not _matches_filter(table_name, table_filter):
                continue
            
            if dataset not in schemas:
                schemas[dataset] = {}
            
            schemas[dataset][table_name] = {
                "columns": schema_info.get("columns", []),
                "description": schema_info.get("description", ""),
                "tenant_id": metadata.get("tenant_id"),
                "is_shared": metadata.get("is_shared", False),
                "created_at": metadata.get("created_at")
            }
        else:
            # Fallback: Try to parse raw DDL (legacy data)
            logger.debug("Processing legacy DDL without normalized schema")
            # Basic parsing - this should be minimal since we enforce normalized schemas
            
    return schemas

def _matches_filter(table_name: str, filter_pattern: str) -> bool:
    """Check if table name matches filter pattern (supports * wildcard)"""
    import fnmatch
    return fnmatch.fnmatch(table_name.lower(), filter_pattern.lower())

def _format_schema_output(schemas: Dict[str, Dict[str, Any]], format_type: str, 
                         include_metadata: bool, include_samples: bool) -> Any:
    """Format schema output based on requested format"""
    
    if format_type == "flat":
        # Simple flat list of tables
        flat_list = []
        for dataset, tables in schemas.items():
            for table_name, table_info in tables.items():
                entry = f"{dataset}.{table_name}"
                if include_metadata:
                    entry = {
                        "table": f"{dataset}.{table_name}",
                        "columns": len(table_info.get("columns", [])),
                        "tenant": table_info.get("tenant_id"),
                        "shared": table_info.get("is_shared", False)
                    }
                flat_list.append(entry)
        return flat_list
    
    elif format_type == "detailed":
        # Maximum detail with all metadata
        detailed = {}
        for dataset, tables in schemas.items():
            detailed[dataset] = {}
            for table_name, table_info in tables.items():
                detailed[dataset][table_name] = {
                    "full_name": f"{dataset}.{table_name}",
                    "columns": table_info.get("columns", []),
                    "description": table_info.get("description", ""),
                    "metadata": {
                        "tenant_id": table_info.get("tenant_id"),
                        "is_shared": table_info.get("is_shared", False),
                        "created_at": table_info.get("created_at")
                    }
                }
                
                # Add sample values if requested and available
                if include_samples:
                    for col in detailed[dataset][table_name]["columns"]:
                        if "sample_values" in col:
                            col["samples"] = col["sample_values"]
        
        return detailed
    
    else:  # hierarchical (default)
        # Group by dataset with moderate detail
        hierarchical = {}
        for dataset, tables in schemas.items():
            hierarchical[dataset] = {
                "tables": list(tables.keys()),
                "table_count": len(tables)
            }
            
            if include_metadata:
                hierarchical[dataset]["table_details"] = {}
                for table_name, table_info in tables.items():
                    hierarchical[dataset]["table_details"][table_name] = {
                        "column_count": len(table_info.get("columns", [])),
                        "description": table_info.get("description", "")[:100] + "..." 
                                      if len(table_info.get("description", "")) > 100 
                                      else table_info.get("description", ""),
                        "is_shared": table_info.get("is_shared", False)
                    }
        
        return hierarchical

# Tool definition for FastMCP
tool_definition = {
    "name": "vanna_get_schemas",
    "description": "Display database structure and schemas accessible to the tenant",
    "input_schema": {
        "type": "object",
        "properties": {
            "tenant_id": {
                "type": "string",
                "description": "Tenant ID for multi-tenant mode (optional)"
            },
            "include_metadata": {
                "type": "boolean",
                "description": "Include detailed metadata",
                "default": True
            },
            "include_sample_values": {
                "type": "boolean",
                "description": "Include sample values for columns",
                "default": False
            },
            "table_filter": {
                "type": "string",
                "description": "Filter tables by name pattern (supports * wildcard)"
            },
            "format_output": {
                "type": "string",
                "enum": ["hierarchical", "flat", "detailed"],
                "description": "Output format for schema information",
                "default": "hierarchical"
            }
        },
        "required": []
    }
}