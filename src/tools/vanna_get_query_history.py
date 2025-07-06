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
        
        # Query vanna_embeddings for history entries (those with no embedding and type=query_history)
        from supabase import create_client
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        
        # Build query filters
        query_builder = supabase.table("vanna_embeddings").select("*")
        
        # Filter for query history entries (no embedding, type=query_history)
        query_builder = query_builder.is_("embedding", "null")
        query_builder = query_builder.eq("cmetadata->>type", "query_history")
        
        # Apply tenant filtering if enabled
        if settings.ENABLE_MULTI_TENANT and effective_tenant:
            query_builder = query_builder.eq("cmetadata->>tenant_id", effective_tenant)
        
        # Order by ID (most recent first) and limit
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: query_builder.order("id", desc=True).limit(limit).execute()
        )
        
        queries = []
        total_execution_time = 0
        confidence_scores = []
        
        for row in result.data:
            metadata = row.get("cmetadata", {})
            
            query_info = {
                "id": row["id"],
                "question": metadata.get("question", "")[:100],
                "sql": metadata.get("generated_sql", "")[:200],
                "confidence_score": metadata.get("confidence_score", 0),
                "execution_time_ms": metadata.get("execution_time_ms", 0),
                "tenant_id": metadata.get("tenant_id"),
                "database_type": metadata.get("database_type"),
                "timestamp": metadata.get("timestamp")
            }
            
            queries.append(query_info)
            
            if metadata.get("execution_time_ms"):
                total_execution_time += metadata.get("execution_time_ms", 0)
            if metadata.get("confidence_score"):
                confidence_scores.append(metadata.get("confidence_score", 0))
        
        response = {
            "queries": queries,
            "total_queries": len(queries),
            "tenant_id": effective_tenant
        }
        
        if include_analytics and queries:
            analytics = {
                "average_execution_time_ms": total_execution_time / len(queries) if queries else 0,
                "average_confidence_score": sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0,
                "queries_by_confidence": {
                    "high_confidence": len([s for s in confidence_scores if s >= 0.8]),
                    "medium_confidence": len([s for s in confidence_scores if 0.5 <= s < 0.8]),
                    "low_confidence": len([s for s in confidence_scores if s < 0.5])
                },
                "fastest_query_ms": min([metadata.get("execution_time_ms", 0) for metadata in [q for q in queries if q.get("execution_time_ms")]], default=0),
                "slowest_query_ms": max([metadata.get("execution_time_ms", 0) for metadata in [q for q in queries if q.get("execution_time_ms")]], default=0)
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