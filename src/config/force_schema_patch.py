#!/usr/bin/env python3
"""
Force Vanna/LangChain to use our schema by patching the connection
"""
import psycopg2
from psycopg2 import sql
import logging

logger = logging.getLogger(__name__)

def force_schema_for_session(connection_string: str, schema: str):
    """
    Create a connection that forces all operations to use our schema
    """
    conn = psycopg2.connect(connection_string)
    cursor = conn.cursor()
    
    # Set the search path for this session
    cursor.execute(f"SET search_path TO {schema}, public")
    
    # Create or replace views in our schema that redirect to tables
    cursor.execute(f"""
        DO $$
        BEGIN
            -- If tables exist in public, create views in our schema
            IF EXISTS (SELECT 1 FROM information_schema.tables 
                      WHERE table_schema = 'public' 
                      AND table_name = 'langchain_pg_collection') THEN
                
                -- Drop tables from public and recreate in our schema
                -- First get the data
                CREATE TEMP TABLE temp_collections AS 
                SELECT * FROM public.langchain_pg_collection;
                
                CREATE TEMP TABLE temp_embeddings AS 
                SELECT * FROM public.langchain_pg_embedding;
                
                -- Drop from public
                DROP TABLE IF EXISTS public.langchain_pg_embedding CASCADE;
                DROP TABLE IF EXISTS public.langchain_pg_collection CASCADE;
                
                -- Recreate in our schema
                CREATE TABLE IF NOT EXISTS {schema}.langchain_pg_collection (
                    uuid UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name VARCHAR,
                    cmetadata JSONB
                );
                
                CREATE TABLE IF NOT EXISTS {schema}.langchain_pg_embedding (
                    id VARCHAR PRIMARY KEY,
                    collection_id UUID,
                    embedding VECTOR,
                    document TEXT,
                    cmetadata JSONB,
                    FOREIGN KEY (collection_id) REFERENCES {schema}.langchain_pg_collection(uuid)
                );
                
                -- Restore data
                INSERT INTO {schema}.langchain_pg_collection 
                SELECT * FROM temp_collections;
                
                INSERT INTO {schema}.langchain_pg_embedding 
                SELECT * FROM temp_embeddings;
                
                -- Clean up
                DROP TABLE temp_collections;
                DROP TABLE temp_embeddings;
                
                -- Create redirect rules
                CREATE OR REPLACE RULE redirect_collection_insert AS
                ON INSERT TO public.langchain_pg_collection
                DO INSTEAD
                INSERT INTO {schema}.langchain_pg_collection VALUES (NEW.*);
                
                CREATE OR REPLACE RULE redirect_embedding_insert AS
                ON INSERT TO public.langchain_pg_embedding
                DO INSTEAD
                INSERT INTO {schema}.langchain_pg_embedding VALUES (NEW.*);
            END IF;
        END $$;
    """)
    
    conn.commit()
    cursor.close()
    return conn

def patch_vanna_connection(vanna_instance, schema: str):
    """
    Patch a Vanna instance to force schema usage
    """
    original_connect = psycopg2.connect
    
    def patched_connect(*args, **kwargs):
        """Intercept all connections and set schema"""
        conn = original_connect(*args, **kwargs)
        cursor = conn.cursor()
        cursor.execute(f"SET search_path TO {schema}, public")
        cursor.close()
        logger.debug(f"Forced search_path to {schema}")
        return conn
    
    # Monkey patch psycopg2.connect
    psycopg2.connect = patched_connect
    
    return vanna_instance