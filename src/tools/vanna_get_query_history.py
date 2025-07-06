"""
vanna_get_query_history tool - View query history and analytics
"""
from typing import Dict, Any, Optional, List
import logging
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
        
        # Query Vanna's training data for query_history entries
        # Since we're using vanna.train() with tag="query_history", 
        # we can get these through Vanna's get_training_data method
        
        training_data = vanna.get_training_data()
        
        # Filter for query_history entries and apply tenant filtering
        queries = []
        total_execution_time = 0
        confidence_scores = []
        
        for item in training_data:
            # Check if this is a query history entry (has our special tag)
            if 'query_history' in str(item).lower():
                # Extract metadata if available
                metadata = getattr(item, 'metadata', {}) or {}
                
                # Apply tenant filtering if enabled
                if settings.ENABLE_MULTI_TENANT and effective_tenant:
                    item_tenant = metadata.get("tenant_id")
                    if item_tenant and item_tenant != effective_tenant:
                        continue
                
                query_info = {
                    "id": getattr(item, 'id', 'unknown'),
                    "question": getattr(item, 'question', '')[:100],
                    "sql": getattr(item, 'sql', '')[:200],
                    "confidence_score": metadata.get("confidence_score", 0),
                    "execution_time_ms": metadata.get("execution_time_ms", 0),
                    "tenant_id": metadata.get("tenant_id"),
                    "database_type": metadata.get("database_type")
                }
                
                queries.append(query_info)
                
                if metadata.get("execution_time_ms"):
                    total_execution_time += metadata.get("execution_time_ms", 0)
                if metadata.get("confidence_score"):
                    confidence_scores.append(metadata.get("confidence_score", 0))
                
                # Limit results
                if len(queries) >= limit:
                    break
        
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