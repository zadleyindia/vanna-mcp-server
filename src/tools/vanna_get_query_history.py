"""
vanna_get_query_history tool - View query history and analytics
"""
from typing import Dict, Any, Optional, List
import logging
import asyncio
from src.config.vanna_config import get_vanna
from src.config.settings import settings

logger = logging.getLogger(__name__)

async def vanna_get_query_history(
    tenant_id: Optional[str] = None,
    limit: int = 10,
    include_analytics: bool = True
) -> Dict[str, Any]:
    """
    Get query history and analytics.
    
    Args:
        tenant_id: Filter by specific tenant (defaults to current tenant)
        limit: Number of recent queries to return
        include_analytics: Include aggregate analytics
        
    Returns:
        Query history with optional analytics
    """
    try:
        vanna = get_vanna()
        
        # Determine effective tenant
        effective_tenant = tenant_id or settings.TENANT_ID
        
        logger.info(f"Retrieving query history for tenant '{effective_tenant}', limit {limit}")
        
        # Query dedicated query_history table using direct PostgreSQL connection
        result_data = await asyncio.get_event_loop().run_in_executor(
            None,
            _get_query_history_sync,
            effective_tenant, limit
        )
        
        queries = []
        total_execution_time = 0
        confidence_scores = []
        
        for row in result_data:
            query_info = {
                "id": row["id"],
                "question": row["question"][:100],
                "sql": row["generated_sql"][:200],
                "confidence_score": float(row.get("confidence_score", 0)),
                "execution_time_ms": row.get("execution_time_ms", 0),
                "tenant_id": row.get("tenant_id"),
                "database_type": row.get("database_type"),
                "executed": row.get("executed", False),
                "row_count": row.get("row_count"),
                "error_message": row.get("error_message"),
                "user_feedback": row.get("user_feedback"),
                "created_at": row.get("created_at")
            }
            
            queries.append(query_info)
            
            if row.get("execution_time_ms"):
                total_execution_time += row.get("execution_time_ms", 0)
            if row.get("confidence_score"):
                confidence_scores.append(float(row.get("confidence_score", 0)))
        
        response = {
            "queries": queries,
            "total_queries": len(queries),
            "tenant_id": effective_tenant
        }
        
        if include_analytics and queries:
            execution_times = [q["execution_time_ms"] for q in queries if q["execution_time_ms"]]
            executed_queries = [q for q in queries if q["executed"]]
            
            analytics = {
                "total_queries": len(queries),
                "executed_queries": len(executed_queries),
                "average_execution_time_ms": total_execution_time / len(execution_times) if execution_times else 0,
                "average_confidence_score": sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0,
                "queries_by_confidence": {
                    "high_confidence": len([s for s in confidence_scores if s >= 0.8]),
                    "medium_confidence": len([s for s in confidence_scores if 0.5 <= s < 0.8]),
                    "low_confidence": len([s for s in confidence_scores if s < 0.5])
                },
                "fastest_query_ms": min(execution_times) if execution_times else 0,
                "slowest_query_ms": max(execution_times) if execution_times else 0,
                "success_rate": len([q for q in queries if not q["error_message"]]) / len(queries) if queries else 0,
                "database_types": list(set(q["database_type"] for q in queries if q["database_type"]))
            }
            response["analytics"] = analytics
        
        logger.info(f"Retrieved {len(queries)} queries from history")
        return response
        
    except Exception as e:
        logger.error(f"Error retrieving query history: {str(e)}", exc_info=True)
        return {
            "error": str(e),
            "message": "Failed to retrieve query history",
            "queries": []
        }

def _get_query_history_sync(effective_tenant: str, limit: int):
    """Synchronous version for executor"""
    import psycopg2
    import psycopg2.extras
    from urllib.parse import urlparse
    
    # Get connection string and parse it
    conn_str = settings.get_supabase_connection_string()
    parsed = urlparse(conn_str)
    
    # Create direct PostgreSQL connection
    conn = psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port,
        database=parsed.path[1:] if parsed.path else 'postgres',
        user=parsed.username,
        password=parsed.password
    )
    
    cursor = conn.cursor(psycopg2.extras.RealDictCursor)
    
    # Use configurable schema for table name
    schema = settings.VANNA_SCHEMA
    table_name = f"{schema}.query_history"
    
    # Build query with tenant filtering if enabled
    if settings.ENABLE_MULTI_TENANT and effective_tenant:
        query_sql = f"""
        SELECT * FROM {table_name} 
        WHERE tenant_id = %s 
        ORDER BY created_at DESC 
        LIMIT %s
        """
        cursor.execute(query_sql, (effective_tenant, limit))
    else:
        query_sql = f"""
        SELECT * FROM {table_name} 
        ORDER BY created_at DESC 
        LIMIT %s
        """
        cursor.execute(query_sql, (limit,))
    
    # Fetch results
    result_data = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return result_data

# For FastMCP registration
tool_definition = {
    "name": "vanna_get_query_history",
    "description": "View query history and analytics for data analysis insights",
    "input_schema": {
        "type": "object",
        "properties": {
            "tenant_id": {
                "type": "string",
                "description": "Filter by specific tenant (optional)"
            },
            "limit": {
                "type": "integer",
                "description": "Number of recent queries to return",
                "default": 10,
                "minimum": 1,
                "maximum": 100
            },
            "include_analytics": {
                "type": "boolean",
                "description": "Include aggregate analytics",
                "default": True
            }
        }
    }
}