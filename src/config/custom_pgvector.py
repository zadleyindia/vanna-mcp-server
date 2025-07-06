"""
Custom PGVector implementation that forces our schema
"""
import os
from typing import Optional, List, Dict, Any
from langchain.vectorstores.pgvector import PGVector
from langchain.schema import Document
import logging

logger = logging.getLogger(__name__)

class CustomPGVector(PGVector):
    """Override PGVector to use our schema instead of public"""
    
    def __init__(self, 
                 connection_string: str,
                 embedding_function: Any,
                 collection_name: str = "default",
                 schema_name: str = "vannabq",
                 **kwargs):
        """Initialize with forced schema"""
        self.schema_name = schema_name
        
        # Modify the connection string to set search path
        if '?' in connection_string:
            connection_string += f"&options=-csearch_path={schema_name},public"
        else:
            connection_string += f"?options=-csearch_path={schema_name},public"
        
        # Override table names to include schema
        self.collection_table_name = f"{schema_name}.langchain_pg_collection"
        self.embedding_table_name = f"{schema_name}.langchain_pg_embedding"
        
        super().__init__(
            connection_string=connection_string,
            embedding_function=embedding_function,
            collection_name=collection_name,
            **kwargs
        )
        
        # Force schema in SQL queries
        self._override_sql_templates()
        
    def _override_sql_templates(self):
        """Override SQL templates to use our schema"""
        # This is a bit hacky but necessary
        if hasattr(self, '_create_collection_query'):
            self._create_collection_query = self._create_collection_query.replace(
                'langchain_pg_collection', 
                f'{self.schema_name}.langchain_pg_collection'
            )
        
        if hasattr(self, '_create_embedding_query'):
            self._create_embedding_query = self._create_embedding_query.replace(
                'langchain_pg_embedding',
                f'{self.schema_name}.langchain_pg_embedding'
            )
    
    def create_tables_if_not_exists(self) -> None:
        """Override to create tables in our schema"""
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                # Ensure schema exists
                cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {self.schema_name}")
                
                # Set search path
                cursor.execute(f"SET search_path TO {self.schema_name}, public")
                
                # Create collection table
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.collection_table_name} (
                        uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        name VARCHAR NOT NULL,
                        cmetadata JSONB
                    )
                """)
                
                # Create embedding table  
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.embedding_table_name} (
                        id VARCHAR PRIMARY KEY,
                        collection_id UUID REFERENCES {self.collection_table_name}(uuid) ON DELETE CASCADE,
                        embedding VECTOR,
                        document TEXT,
                        cmetadata JSONB
                    )
                """)
                
                conn.commit()
                
        logger.info(f"Ensured tables exist in schema: {self.schema_name}")