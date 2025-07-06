"""
Simplified query history storage using existing Vanna connection infrastructure
"""
import asyncio
import logging
from src.config.settings import settings

logger = logging.getLogger(__name__)

async def store_query_history(query: str, sql: str, execution_time_ms: float, confidence: float, tenant_id: str):
    """Store query in dedicated query_history table using existing Vanna connection"""
    try:
        # Run the database operation in executor to avoid blocking
        await asyncio.get_event_loop().run_in_executor(
            None,
            _store_query_history_sync,
            query, sql, execution_time_ms, confidence, tenant_id
        )
        
        logger.debug(f"Stored query history: {query[:50]}... (confidence: {confidence})")
        
    except Exception as e:
        logger.warning(f"Failed to store query history: {e}")
        # Don't fail the main operation if history storage fails

def _store_query_history_sync(query: str, sql: str, execution_time_ms: float, confidence: float, tenant_id: str):
    """Synchronous version for executor - uses existing Vanna connection"""
    from src.config.vanna_config import get_vanna
    
    # Get the existing Vanna instance which has working connection
    vanna = get_vanna()
    
    # Use the same connection method as the core Vanna tables
    with vanna._get_connection() as conn:
        with conn.cursor() as cur:
            # Use configurable schema (same as other Vanna tables)
            schema = settings.VANNA_SCHEMA
            
            # Insert into query history table (table created by _ensure_schema_and_tables)
            cur.execute(f"""
                INSERT INTO {schema}.query_history 
                (question, generated_sql, execution_time_ms, confidence_score, tenant_id, database_type, executed, row_count, error_message, user_feedback)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                query,
                sql,
                int(execution_time_ms),
                round(confidence, 2),
                tenant_id,
                settings.DATABASE_TYPE,
                False,  # executed
                None,   # row_count
                None,   # error_message
                None    # user_feedback
            ))
            conn.commit()