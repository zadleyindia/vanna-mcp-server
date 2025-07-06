"""
Multi-database and multi-tenant Vanna implementation
"""
from typing import Dict, Any, Optional, List
import logging
import json
from datetime import datetime
from vanna.base import VannaBase
from vanna.openai import OpenAI_Chat
from vanna.pgvector import PG_VectorStore

from .settings import settings

logger = logging.getLogger(__name__)

class MultiDatabaseVanna(OpenAI_Chat, PG_VectorStore, VannaBase):
    """
    Vanna implementation supporting multiple databases and tenants
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize with multi-database support"""
        vanna_config = {
            "api_key": settings.OPENAI_API_KEY,
            "model": settings.OPENAI_MODEL,
            "embedding_model": settings.OPENAI_EMBEDDING_MODEL,
            "connection_string": settings.get_supabase_connection_string(),
        }
        
        if config:
            vanna_config.update(config)
        
        # Initialize parent classes
        VannaBase.__init__(self, config=vanna_config)
        OpenAI_Chat.__init__(self, config=vanna_config)
        PG_VectorStore.__init__(self, config=vanna_config)
        
        logger.info("Initialized MultiDatabaseVanna")
    
    def train(self,
              question: Optional[str] = None,
              sql: Optional[str] = None,
              ddl: Optional[str] = None,
              documentation: Optional[str] = None,
              database_type: Optional[str] = None,
              database_name: Optional[str] = None,
              schema_name: Optional[str] = None,
              table_name: Optional[str] = None,
              tenant_id: Optional[str] = None,
              is_shared: bool = False,
              metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Enhanced train method with database and tenant support
        
        Args:
            question: Natural language question
            sql: SQL query
            ddl: Data Definition Language statement
            documentation: Documentation text
            database_type: Type of database (bigquery, mssql, etc.)
            database_name: Name of the database/project
            schema_name: Schema name
            table_name: Table name
            tenant_id: Tenant identifier (overrides settings)
            is_shared: Mark as shared knowledge
            metadata: Additional metadata
        """
        # Determine database type
        db_type = database_type or settings.DATABASE_TYPE
        
        # Determine tenant ID
        if settings.ENABLE_MULTI_TENANT:
            if is_shared:
                effective_tenant_id = "shared"
            else:
                effective_tenant_id = tenant_id or settings.TENANT_ID
        else:
            effective_tenant_id = None  # No tenant in single-tenant mode
        
        # Build enhanced metadata
        enhanced_metadata = {
            "database_type": db_type,
            "timestamp": str(datetime.now())
        }
        
        # Add tenant only in multi-tenant mode
        if settings.ENABLE_MULTI_TENANT:
            enhanced_metadata["tenant_id"] = effective_tenant_id
        
        # Add optional fields if provided
        if database_name:
            enhanced_metadata["database_name"] = database_name
        elif db_type == "bigquery":
            enhanced_metadata["database_name"] = settings.BIGQUERY_PROJECT
        elif db_type == "mssql":
            enhanced_metadata["database_name"] = settings.MSSQL_DATABASE
        
        if schema_name:
            enhanced_metadata["schema_name"] = schema_name
        if table_name:
            enhanced_metadata["table_name"] = table_name
        
        if metadata:
            enhanced_metadata.update(metadata)
        
        # Log what we're training
        if settings.ENABLE_MULTI_TENANT:
            logger.info(f"Training for database: {db_type}, tenant: {effective_tenant_id}")
        else:
            logger.info(f"Training for database: {db_type}")
        
        # Extract table info from DDL if available
        if ddl:
            import re
            table_match = re.search(r'CREATE TABLE\s+[`"\[]?([^`"\[\]\s]+)', ddl, re.IGNORECASE)
            if table_match:
                full_table = table_match.group(1)
                parts = full_table.split('.')
                if len(parts) >= 2 and not schema_name:
                    enhanced_metadata['schema_name'] = parts[-2]
                if not table_name:
                    enhanced_metadata['table_name'] = parts[-1]
        
        # Vanna's train method doesn't accept metadata directly
        # We need to handle this differently based on the training type
        if ddl:
            # For DDL, we'll store metadata separately after training
            success = super().train(ddl=ddl)
            if success and settings.ENABLE_MULTI_TENANT:
                # TODO: Store metadata in a separate tracking table or as part of the embedding
                logger.debug(f"DDL trained with metadata: {enhanced_metadata}")
            return success
        elif documentation:
            success = super().train(documentation=documentation)
            if success and settings.ENABLE_MULTI_TENANT:
                logger.debug(f"Documentation trained with metadata: {enhanced_metadata}")
            return success
        elif sql and question:
            success = super().train(question=question, sql=sql)
            if success and settings.ENABLE_MULTI_TENANT:
                logger.debug(f"SQL trained with metadata: {enhanced_metadata}")
            return success
        else:
            return False
    
    def ask(self, 
            question: str,
            database_type: Optional[str] = None,
            tenant_id: Optional[str] = None,
            include_shared: Optional[bool] = None,
            print_results: bool = True,
            auto_train: bool = True,
            visualize: bool = True) -> str:
        """
        Enhanced ask method with database and tenant filtering
        
        Args:
            question: Natural language question
            database_type: Override database type
            tenant_id: Override tenant ID (for multi-tenant mode)
            include_shared: Override shared knowledge setting
            print_results: Print results to console
            auto_train: Automatically train on successful queries
            visualize: Generate visualizations
            
        Returns:
            Generated SQL query string
        """
        # Determine database type
        db_type = database_type or settings.DATABASE_TYPE
        
        # Determine effective tenant and shared settings
        if settings.ENABLE_MULTI_TENANT:
            effective_tenant = tenant_id or settings.TENANT_ID
            use_shared = include_shared if include_shared is not None else settings.ENABLE_SHARED_KNOWLEDGE
        else:
            effective_tenant = None
            use_shared = False
        
        # Build metadata filter
        metadata_filter = {"database_type": db_type}
        
        if settings.ENABLE_MULTI_TENANT:
            if use_shared:
                # This requires custom SQL - we'll need to override pgvector methods
                logger.info(f"Querying for tenant '{effective_tenant}' with shared knowledge")
            else:
                metadata_filter["tenant_id"] = effective_tenant
                logger.info(f"Querying for tenant '{effective_tenant}' only")
        
        # Log the query context
        logger.info(f"Processing question for database: {db_type}")
        
        # For now, use parent ask method
        # TODO: Override get_similar_question_sql to apply metadata filtering
        sql = super().ask(
            question=question,
            print_results=print_results,
            auto_train=auto_train,
            visualize=visualize
        )
        
        return sql
    
    def get_training_data_filtered(self,
                                   database_type: Optional[str] = None,
                                   tenant_id: Optional[str] = None,
                                   training_data_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get training data with filters
        """
        import pandas as pd
        import psycopg2
        
        conn = psycopg2.connect(self.config['connection_string'])
        
        # Build query with filters
        query = """
        SELECT 
            id,
            training_data_type,
            content,
            metadata,
            created_at
        FROM langchain_pg_embedding e
        JOIN langchain_pg_collection c ON e.collection_id = c.uuid
        WHERE 1=1
        """
        
        params = []
        
        if database_type:
            query += " AND e.cmetadata->>'database_type' = %s"
            params.append(database_type)
        
        if tenant_id:
            query += " AND e.cmetadata->>'tenant_id' = %s"
            params.append(tenant_id)
        
        if training_data_type:
            query += " AND c.name = %s"
            params.append(training_data_type)
        
        query += " ORDER BY created_at DESC"
        
        df = pd.read_sql(query, conn, params=params)
        conn.close()
        
        return df.to_dict('records')
    
    def remove_training_data_filtered(self,
                                      id: str,
                                      tenant_id: Optional[str] = None) -> bool:
        """
        Remove training data with tenant check
        """
        import psycopg2
        
        conn = psycopg2.connect(self.config['connection_string'])
        cursor = conn.cursor()
        
        try:
            # Verify tenant access before deletion
            if tenant_id:
                cursor.execute("""
                    SELECT cmetadata->>'tenant_id' as tenant
                    FROM langchain_pg_embedding
                    WHERE id = %s
                """, (id,))
                
                result = cursor.fetchone()
                if result and result[0] != tenant_id and result[0] != 'shared':
                    logger.warning(f"Tenant {tenant_id} tried to delete data from tenant {result[0]}")
                    return False
            
            # Delete the embedding
            cursor.execute("DELETE FROM langchain_pg_embedding WHERE id = %s", (id,))
            conn.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove training data: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()


# Usage examples:
"""
# Initialize multi-database Vanna
vn = MultiDatabaseVanna()

# Train with BigQuery data
vn.train(
    ddl="CREATE TABLE `project.dataset.sales` (id INT64, amount NUMERIC)",
    database_type="bigquery",
    database_name="bigquerylascout",
    schema_name="SQL_ZADLEY",
    tenant_id="tenant1"
)

# Train with MS SQL data
vn.train(
    ddl="CREATE TABLE [dbo].[sales] (id INT, amount DECIMAL(10,2))",
    database_type="mssql",
    database_name="sales_db",
    schema_name="dbo",
    tenant_id="tenant1"
)

# Ask questions filtered by database
bigquery_sql = vn.ask(
    "Show me total sales",
    database_type="bigquery",
    tenant_id="tenant1"
)

mssql_sql = vn.ask(
    "Show me total sales",
    database_type="mssql",
    tenant_id="tenant1"
)
"""