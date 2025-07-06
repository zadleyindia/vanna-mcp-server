"""
Enhanced PGVector implementation with schema support.

This implementation extends the basic pgvector to support custom schemas,
avoiding the limitation of being restricted to the public schema.
"""

import ast
import json
import logging
import uuid
from typing import Optional, Dict, Any, List

import pandas as pd
from langchain_core.documents import Document
from sqlalchemy import create_engine, text
import psycopg2
from psycopg2.extras import RealDictCursor

from vanna import ValidationError
from vanna.base import VannaBase
from vanna.types import TrainingPlan, TrainingPlanItem


class SchemaAwarePGVectorStore(VannaBase):
    """PGVector store that supports custom schemas."""
    
    def __init__(self, config=None):
        if not config or "connection_string" not in config:
            raise ValueError(
                "A valid 'config' dictionary with a 'connection_string' is required.")

        VannaBase.__init__(self, config=config)

        self.connection_string = config.get("connection_string")
        self.n_results = config.get("n_results", 10)
        self.schema_name = config.get("schema", "public")  # Support custom schema
        
        # Parse connection string to get database connection params
        self._parse_connection_string()
        
        # Initialize tables if needed
        self._ensure_schema_and_tables()
        
        if config and "embedding_function" in config:
            self.embedding_function = config.get("embedding_function")
        else:
            from langchain_huggingface import HuggingFaceEmbeddings
            self.embedding_function = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    def _parse_connection_string(self):
        """Parse PostgreSQL connection string."""
        # Extract components from postgresql://user:pass@host:port/db format
        from urllib.parse import urlparse, unquote
        parsed = urlparse(self.connection_string)
        
        self.db_params = {
            'host': parsed.hostname,
            'port': parsed.port or 5432,
            'database': parsed.path.lstrip('/'),
            'user': parsed.username,
            'password': unquote(parsed.password) if parsed.password else None
        }
    
    def _get_connection(self):
        """Get a database connection."""
        return psycopg2.connect(**self.db_params)
    
    def _ensure_schema_and_tables(self):
        """Create schema and tables if they don't exist."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # Create schema if it doesn't exist
                cur.execute(f"CREATE SCHEMA IF NOT EXISTS {self.schema_name}")
                
                # Create collections table
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.schema_name}.vanna_collections (
                        uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        name VARCHAR NOT NULL UNIQUE,
                        cmetadata JSON
                    )
                """)
                
                # Create embeddings table
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.schema_name}.vanna_embeddings (
                        id VARCHAR PRIMARY KEY,
                        collection_id UUID REFERENCES {self.schema_name}.vanna_collections(uuid),
                        embedding VECTOR(1536),
                        document TEXT,
                        cmetadata JSONB
                    )
                """)
                
                # Create query history table for analytics (separate from training data)
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.schema_name}.query_history (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        question TEXT NOT NULL,
                        generated_sql TEXT NOT NULL,
                        execution_time_ms INTEGER,
                        confidence_score NUMERIC(3,2),
                        tenant_id VARCHAR(255),
                        database_type VARCHAR(50),
                        executed BOOLEAN DEFAULT false,
                        row_count INTEGER,
                        error_message TEXT,
                        user_feedback VARCHAR(20),
                        created_at TIMESTAMPTZ DEFAULT NOW()
                    )
                """)
                
                # Create indexes
                cur.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{self.schema_name}_embedding_collection 
                    ON {self.schema_name}.vanna_embeddings(collection_id)
                """)
                
                cur.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{self.schema_name}_embedding_metadata 
                    ON {self.schema_name}.vanna_embeddings USING GIN (cmetadata)
                """)
                
                # Query history indexes
                cur.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{self.schema_name}_query_history_created 
                    ON {self.schema_name}.query_history(created_at DESC)
                """)
                
                cur.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{self.schema_name}_query_history_tenant 
                    ON {self.schema_name}.query_history(tenant_id)
                """)
                
                cur.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{self.schema_name}_query_history_confidence 
                    ON {self.schema_name}.query_history(confidence_score DESC)
                """)
                
                conn.commit()
    
    def _get_or_create_collection(self, name: str) -> str:
        """Get or create a collection and return its UUID."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                # Try to get existing collection
                cur.execute(
                    f"SELECT uuid FROM {self.schema_name}.vanna_collections WHERE name = %s",
                    (name,)
                )
                result = cur.fetchone()
                
                if result:
                    return str(result[0])
                
                # Create new collection
                cur.execute(
                    f"INSERT INTO {self.schema_name}.vanna_collections (name) VALUES (%s) RETURNING uuid",
                    (name,)
                )
                conn.commit()
                return str(cur.fetchone()[0])
    
    def _add_embedding(self, collection_name: str, id: str, document: str, 
                      embedding: List[float], metadata: Dict[str, Any]) -> str:
        """Add an embedding to the store."""
        collection_id = self._get_or_create_collection(collection_name)
        
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    INSERT INTO {self.schema_name}.vanna_embeddings 
                    (id, collection_id, embedding, document, cmetadata)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        embedding = EXCLUDED.embedding,
                        document = EXCLUDED.document,
                        cmetadata = EXCLUDED.cmetadata
                """, (id, collection_id, embedding, document, json.dumps(metadata)))
                conn.commit()
        
        return id
    
    def _similarity_search(self, collection_name: str, query_embedding: List[float], 
                          k: int = 5, metadata_filter: Optional[Dict[str, Any]] = None) -> List[Dict]:
        """Perform similarity search with optional metadata filtering."""
        collection_id = self._get_or_create_collection(collection_name)
        
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Build query with metadata filter
                query = f"""
                    SELECT document, cmetadata,
                           embedding <=> %s::vector as distance
                    FROM {self.schema_name}.vanna_embeddings
                    WHERE collection_id = %s
                """
                
                params = [query_embedding, collection_id]
                
                if metadata_filter:
                    # Handle tenant-specific filtering
                    if 'tenant_id' in metadata_filter:
                        tenant_id = metadata_filter['tenant_id']
                        from ..config.settings import settings
                        
                        if settings.INCLUDE_LEGACY_DATA:
                            # Include records with matching tenant_id OR no tenant_id (legacy data)
                            query += """ AND (
                                (cmetadata->>'tenant_id' = %s) OR 
                                (cmetadata->>'tenant_id' IS NULL)
                            )"""
                            params.append(tenant_id)
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.info(f"LEGACY mode - Including records for tenant '{tenant_id}' OR no tenant_id")
                        else:
                            # Strict filtering: only exact tenant_id matches
                            query += " AND cmetadata->>'tenant_id' = %s"
                            params.append(tenant_id)
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.info(f"STRICT mode filtering for tenant '{tenant_id}'")
                        
                        # Add other filters (excluding tenant_id since we handled it specially)
                        other_filters = {k: v for k, v in metadata_filter.items() if k != 'tenant_id'}
                        if other_filters:
                            query += " AND cmetadata @> %s"
                            params.append(json.dumps(other_filters))
                    
                    elif 'is_shared' in metadata_filter:
                        # Handle shared knowledge filtering
                        query += " AND cmetadata->>'is_shared' = %s"
                        params.append(metadata_filter['is_shared'])
                        
                        # Add other filters
                        other_filters = {k: v for k, v in metadata_filter.items() if k != 'is_shared'}
                        if other_filters:
                            query += " AND cmetadata @> %s"
                            params.append(json.dumps(other_filters))
                    
                    else:
                        # Standard filtering for non-tenant fields
                        query += " AND cmetadata @> %s"
                        params.append(json.dumps(metadata_filter))
                
                query += " ORDER BY distance LIMIT %s"
                params.append(k)
                
                # Log the query for debugging
                import logging
                logger = logging.getLogger(__name__)
                logger.debug(f"Similarity search query: {query}")
                logger.debug(f"Query params: {params}")
                
                cur.execute(query, params)
                results = cur.fetchall()
                
                logger.debug(f"Similarity search returned {len(results)} results")
                if results and len(results) > 0:
                    logger.debug(f"First result metadata: {results[0].get('cmetadata', {})}")
                
                return results
    
    def add_question_sql(self, question: str, sql: str, **kwargs) -> str:
        question_sql_json = json.dumps(
            {
                "question": question,
                "sql": sql,
            },
            ensure_ascii=False,
        )
        id = str(uuid.uuid4()) + "-sql"
        
        # Build metadata with custom schema info
        metadata = kwargs.get("metadata", {})
        metadata["id"] = id
        metadata["schema"] = self.schema_name
        if "createdat" in kwargs:
            metadata["createdat"] = kwargs["createdat"]
        
        embedding = self.generate_embedding(question_sql_json)
        
        return self._add_embedding("sql", id, question_sql_json, embedding, metadata)

    def add_ddl(self, ddl: str, **kwargs) -> str:
        id = str(uuid.uuid4()) + "-ddl"
        
        # Build metadata
        metadata = kwargs.get("metadata", {})
        metadata["id"] = id
        metadata["schema"] = self.schema_name
        
        embedding = self.generate_embedding(ddl)
        
        return self._add_embedding("ddl", id, ddl, embedding, metadata)

    def add_documentation(self, documentation: str, **kwargs) -> str:
        id = str(uuid.uuid4()) + "-doc"
        
        # Build metadata
        metadata = kwargs.get("metadata", {})
        metadata["id"] = id
        metadata["schema"] = self.schema_name
        
        embedding = self.generate_embedding(documentation)
        
        return self._add_embedding("documentation", id, documentation, embedding, metadata)

    def get_similar_question_sql(self, question: str, **kwargs) -> list:
        query_embedding = self.generate_embedding(question)
        
        # Get metadata filter from kwargs
        metadata_filter = kwargs.get("metadata_filter", None)
        
        results = self._similarity_search("sql", query_embedding, self.n_results, metadata_filter)
        
        return [ast.literal_eval(doc["document"]) for doc in results]

    def get_related_ddl(self, question: str, **kwargs) -> list:
        query_embedding = self.generate_embedding(question)
        
        # Get metadata filter from kwargs
        metadata_filter = kwargs.get("metadata_filter", None)
        
        results = self._similarity_search("ddl", query_embedding, self.n_results, metadata_filter)
        
        return [doc["document"] for doc in results]

    def get_related_documentation(self, question: str, **kwargs) -> list:
        query_embedding = self.generate_embedding(question)
        
        # Get metadata filter from kwargs
        metadata_filter = kwargs.get("metadata_filter", None)
        
        results = self._similarity_search("documentation", query_embedding, self.n_results, metadata_filter)
        
        return [doc["document"] for doc in results]

    def get_training_data(self, **kwargs) -> pd.DataFrame:
        """Get all training data from the store."""
        data = []
        
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get all collections
                cur.execute(f"SELECT name, uuid FROM {self.schema_name}.vanna_collections")
                collections = cur.fetchall()
                
                for collection in collections:
                    # Get embeddings for this collection
                    cur.execute(f"""
                        SELECT id, document, cmetadata
                        FROM {self.schema_name}.vanna_embeddings
                        WHERE collection_id = %s
                    """, (collection['uuid'],))
                    
                    for row in cur.fetchall():
                        data.append({
                            'id': row['id'],
                            'type': collection['name'],
                            'content': row['document'],
                            'metadata': row['cmetadata']
                        })
        
        return pd.DataFrame(data)

    def remove_training_data(self, id: str, **kwargs) -> bool:
        """Remove training data by ID."""
        with self._get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"DELETE FROM {self.schema_name}.vanna_embeddings WHERE id = %s",
                    (id,)
                )
                conn.commit()
                return cur.rowcount > 0

    def generate_embedding(self, data: str, **kwargs) -> List[float]:
        """Generate embedding for data."""
        # Check if this is a ProductionVanna instance with OpenAI
        if hasattr(self, 'generate_embedding_openai'):
            return self.generate_embedding_openai(data)
        else:
            return self.embedding_function.embed_query(data)