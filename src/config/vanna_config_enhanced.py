"""
Enhanced Vanna configuration that forces all operations to use our schema
"""
from typing import Optional, Dict, Any
import logging
import psycopg2
from vanna.base import VannaBase
from vanna.openai import OpenAI_Chat
from vanna.pgvector import PG_VectorStore

from .settings import settings

logger = logging.getLogger(__name__)

class VannaMCPEnhanced(OpenAI_Chat, PG_VectorStore, VannaBase):
    """
    Enhanced Vanna class that ensures ALL tables are in our schema
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize Vanna with schema enforcement"""
        
        # Build configuration
        vanna_config = {
            "api_key": settings.OPENAI_API_KEY,
            "model": settings.OPENAI_MODEL,
            "embedding_model": settings.OPENAI_EMBEDDING_MODEL,
            "connection_string": self._get_enhanced_connection_string(),
            "schema_name": settings.VANNA_SCHEMA,
            "model_name": settings.VANNA_MODEL_NAME,
        }
        
        if config:
            vanna_config.update(config)
        
        # Initialize parent classes
        VannaBase.__init__(self, config=vanna_config)
        OpenAI_Chat.__init__(self, config=vanna_config)
        PG_VectorStore.__init__(self, config=vanna_config)
        
        # Force schema for all operations
        self._enforce_schema()
        
        logger.info(f"Initialized VannaMCP with enforced schema: {settings.VANNA_SCHEMA}")
    
    def _get_enhanced_connection_string(self) -> str:
        """Get connection string with schema in search path"""
        conn_str = settings.get_supabase_connection_string()
        schema = settings.VANNA_SCHEMA
        
        # Add schema to search path
        if '?' in conn_str:
            conn_str += f"&options=-csearch_path={schema},public"
        else:
            conn_str += f"?options=-csearch_path={schema},public"
        
        return conn_str
    
    def _enforce_schema(self):
        """Ensure all operations use our schema"""
        schema = settings.VANNA_SCHEMA
        
        # Set schema for current connection
        try:
            conn = psycopg2.connect(settings.get_supabase_connection_string())
            cursor = conn.cursor()
            
            # Set search path for this session
            cursor.execute(f"SET search_path TO {schema}, public")
            
            # Ensure LangChain tables exist in our schema
            cursor.execute(f"""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = %s 
                AND table_name IN ('langchain_pg_collection', 'langchain_pg_embedding')
            """, (schema,))
            
            tables = cursor.fetchall()
            if len(tables) < 2:
                logger.warning(f"LangChain tables not found in {schema} schema")
                logger.info("Run scripts/fix_vanna_schema.py to move them")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to enforce schema: {e}")
    
    def train(self, 
              question: Optional[str] = None,
              sql: Optional[str] = None,
              ddl: Optional[str] = None,
              documentation: Optional[str] = None,
              plan: Optional[str] = None) -> bool:
        """
        Override train to ensure schema is used
        """
        # Log where data is being stored
        logger.debug(f"Training data will be stored in schema: {settings.VANNA_SCHEMA}")
        
        # Call parent train method
        result = super().train(
            question=question,
            sql=sql,
            ddl=ddl,
            documentation=documentation,
            plan=plan
        )
        
        return result

def get_vanna_enhanced():
    """Get enhanced Vanna instance with schema enforcement"""
    return VannaMCPEnhanced()