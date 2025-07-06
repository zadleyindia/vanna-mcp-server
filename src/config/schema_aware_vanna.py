"""
Schema-aware Vanna implementation that properly respects the configured schema
"""
import os
import psycopg2
from typing import Optional, Dict, Any, List
import pandas as pd
from vanna.base import VannaBase
from vanna.openai import OpenAI_Chat
from vanna.pgvector import PG_VectorStore
import logging

from .settings import settings

logger = logging.getLogger(__name__)

class SchemaAwarePGVectorStore(PG_VectorStore):
    """
    Override PG_VectorStore to properly use configured schema
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize with schema awareness"""
        self.schema_name = config.get('schema_name', 'public')
        super().__init__(config)
        
        # Override the connection to ensure schema is set
        self._ensure_schema_tables()
    
    def _ensure_schema_tables(self):
        """Ensure tables exist in our schema, not public"""
        conn_str = self.config.get('connection_string')
        conn = psycopg2.connect(conn_str)
        cursor = conn.cursor()
        
        try:
            # Create schema if not exists
            cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {self.schema_name}")
            
            # Set search path for this session
            cursor.execute(f"SET search_path TO {self.schema_name}, public")
            
            # Check if we need to migrate tables from public
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('langchain_pg_collection', 'langchain_pg_embedding')
            """)
            
            public_tables = cursor.fetchall()
            if public_tables:
                logger.info(f"Migrating LangChain tables from public to {self.schema_name}")
                
                # Migrate with data
                for (table_name,) in public_tables:
                    cursor.execute(f"""
                        CREATE TABLE IF NOT EXISTS {self.schema_name}.{table_name} 
                        (LIKE public.{table_name} INCLUDING ALL)
                    """)
                    
                    cursor.execute(f"""
                        INSERT INTO {self.schema_name}.{table_name}
                        SELECT * FROM public.{table_name}
                        ON CONFLICT DO NOTHING
                    """)
                    
                    cursor.execute(f"DROP TABLE public.{table_name} CASCADE")
                    
                logger.info("Migration complete")
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Error ensuring schema tables: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding - ensure it uses our schema"""
        # Set search path before operations
        if hasattr(self, 'conn') and self.conn:
            cursor = self.conn.cursor()
            cursor.execute(f"SET search_path TO {self.schema_name}, public")
            cursor.close()
        
        return super().generate_embedding(text)
    
    def add_question_sql(self, question: str, sql: str, **kwargs) -> str:
        """Override to ensure operations use our schema"""
        # Temporarily set search path
        conn_str = self.config.get('connection_string')
        conn = psycopg2.connect(conn_str)
        cursor = conn.cursor()
        
        try:
            cursor.execute(f"SET search_path TO {self.schema_name}, public")
            conn.commit()
        finally:
            cursor.close()
            conn.close()
        
        return super().add_question_sql(question, sql, **kwargs)
    
    def add_ddl(self, ddl: str, **kwargs) -> str:
        """Override to ensure operations use our schema"""
        conn_str = self.config.get('connection_string')
        conn = psycopg2.connect(conn_str)
        cursor = conn.cursor()
        
        try:
            cursor.execute(f"SET search_path TO {self.schema_name}, public")
            conn.commit()
        finally:
            cursor.close()
            conn.close()
        
        return super().add_ddl(ddl, **kwargs)
    
    def get_similar_question_sql(self, question: str, **kwargs) -> list:
        """Override to ensure operations use our schema"""
        conn_str = self.config.get('connection_string')
        conn = psycopg2.connect(conn_str)
        cursor = conn.cursor()
        
        try:
            cursor.execute(f"SET search_path TO {self.schema_name}, public")
            conn.commit()
        finally:
            cursor.close()
            conn.close()
        
        return super().get_similar_question_sql(question, **kwargs)
    
    def get_training_data(self, **kwargs) -> pd.DataFrame:
        """Override to ensure operations use our schema"""
        conn_str = self.config.get('connection_string')
        conn = psycopg2.connect(conn_str)
        cursor = conn.cursor()
        
        try:
            cursor.execute(f"SET search_path TO {self.schema_name}, public")
            
            # Also check our custom training_data table
            cursor.execute(f"""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = %s 
                AND table_name = 'training_data'
            """, (self.schema_name,))
            
            if cursor.fetchone()[0] > 0:
                # We have a custom training_data table
                query = f"""
                    SELECT 
                        training_data_type as type,
                        content,
                        metadata
                    FROM {self.schema_name}.training_data
                """
                return pd.read_sql(query, conn)
            
            conn.commit()
        finally:
            cursor.close()
            conn.close()
        
        return super().get_training_data(**kwargs)


class SchemaAwareVanna(OpenAI_Chat, SchemaAwarePGVectorStore, VannaBase):
    """
    Vanna implementation that properly respects schema configuration
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize with schema awareness"""
        
        # Build configuration from settings
        vanna_config = {
            "api_key": settings.OPENAI_API_KEY,
            "model": settings.OPENAI_MODEL,
            "embedding_model": settings.OPENAI_EMBEDDING_MODEL,
            "connection_string": self._get_schema_connection_string(),
            "schema_name": settings.VANNA_SCHEMA,
            "model_name": settings.VANNA_MODEL_NAME,
        }
        
        if config:
            vanna_config.update(config)
        
        # Initialize parent classes in correct order
        VannaBase.__init__(self, config=vanna_config)
        OpenAI_Chat.__init__(self, config=vanna_config)
        SchemaAwarePGVectorStore.__init__(self, config=vanna_config)
        
        logger.info(f"Initialized SchemaAwareVanna with schema: {settings.VANNA_SCHEMA}")
    
    def _get_schema_connection_string(self) -> str:
        """Get connection string with schema configuration"""
        conn_str = settings.get_supabase_connection_string()
        schema = settings.VANNA_SCHEMA
        
        # Add schema to search path in connection string
        if '?' in conn_str:
            conn_str += f"&options=-csearch_path={schema},public"
        else:
            conn_str += f"?options=-csearch_path={schema},public"
        
        return conn_str
    
    def train(self, 
              question: Optional[str] = None,
              sql: Optional[str] = None,
              ddl: Optional[str] = None,
              documentation: Optional[str] = None,
              plan: Optional[str] = None) -> bool:
        """
        Override train to ensure schema is used
        """
        logger.debug(f"Training data will be stored in schema: {settings.VANNA_SCHEMA}")
        
        # Ensure search path is set for this operation
        conn_str = self.config.get('connection_string')
        conn = psycopg2.connect(conn_str)
        cursor = conn.cursor()
        
        try:
            cursor.execute(f"SET search_path TO {settings.VANNA_SCHEMA}, public")
            conn.commit()
        finally:
            cursor.close()
            conn.close()
        
        # Call parent train method
        return super().train(
            question=question,
            sql=sql,
            ddl=ddl,
            documentation=documentation,
            plan=plan
        )


def get_schema_aware_vanna():
    """Get a schema-aware Vanna instance"""
    return SchemaAwareVanna()