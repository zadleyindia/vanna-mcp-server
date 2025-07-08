"""
Storage service for catalog data in BigQuery
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from google.cloud import bigquery
from google.cloud.exceptions import GoogleCloudError

from ..config.settings import settings
from .schema import CATALOG_SCHEMAS

logger = logging.getLogger(__name__)

class CatalogStorage:
    """Service for storing catalog data in BigQuery with embeddings"""
    
    def __init__(self, project_id: Optional[str] = None, dataset_id: Optional[str] = None):
        self.project_id = project_id or settings.BIGQUERY_PROJECT
        self.dataset_id = dataset_id or "vannabq"  # Store in Vanna's dataset
        self.client = bigquery.Client(project=self.project_id)
        
        # Embedding service will be initialized when needed
        self.embedding_service = None
    
    async def initialize_tables(self) -> Dict[str, bool]:
        """Create catalog tables if they don't exist"""
        
        results = {}
        
        for table_name, schema_template in CATALOG_SCHEMAS:
            try:
                # Format schema with project and dataset
                schema_sql = schema_template.format(
                    project=self.project_id,
                    dataset=self.dataset_id
                )
                
                # Execute DDL
                job = self.client.query(schema_sql)
                job.result()  # Wait for completion
                
                results[table_name] = True
                logger.info(f"Initialized table: {table_name}")
                
            except Exception as e:
                logger.error(f"Failed to create table {table_name}: {str(e)}")
                results[table_name] = False
        
        return results
    
    async def store_table_context(self, context_data: Dict[str, Any]) -> str:
        """Store table business context with embedding"""
        
        table_id = f"{self.project_id}.{self.dataset_id}.catalog_table_context"
        
        # Generate embedding for context
        if context_data.get('context_chunk'):
            embedding = await self._generate_embedding(context_data['context_chunk'])
            context_data['embedding'] = embedding
            context_data['embedding_model'] = settings.OPENAI_EMBEDDING_MODEL
        
        # Set timestamps
        context_data['created_at'] = datetime.utcnow().isoformat()
        context_data['updated_at'] = datetime.utcnow().isoformat()
        
        # Insert or update
        return await self._upsert_record(
            table_id=table_id,
            record=context_data,
            unique_key='table_fqdn'
        )
    
    async def store_column_chunks(self, chunks: List[Dict[str, Any]]) -> List[str]:
        """Store column information chunks with embeddings"""
        
        table_id = f"{self.project_id}.{self.dataset_id}.catalog_column_chunks"
        results = []
        
        for chunk in chunks:
            # Generate embedding
            if chunk.get('column_chunk'):
                embedding = await self._generate_embedding(chunk['column_chunk'])
                chunk['embedding'] = embedding
                chunk['embedding_model'] = settings.OPENAI_EMBEDDING_MODEL
            
            # Set timestamp
            chunk['created_at'] = datetime.utcnow().isoformat()
            
            # Insert or update
            result = await self._upsert_record(
                table_id=table_id,
                record=chunk,
                unique_key=('table_fqdn', 'chunk_index')
            )
            results.append(result)
        
        return results
    
    async def store_view_queries(self, chunks: List[Dict[str, Any]]) -> List[str]:
        """Store view SQL patterns with embeddings"""
        
        table_id = f"{self.project_id}.{self.dataset_id}.catalog_view_queries"
        results = []
        
        for chunk in chunks:
            # Generate embedding
            if chunk.get('query_chunk'):
                embedding = await self._generate_embedding(chunk['query_chunk'])
                chunk['embedding'] = embedding
                chunk['embedding_model'] = settings.OPENAI_EMBEDDING_MODEL
            
            # Set timestamp
            chunk['created_at'] = datetime.utcnow().isoformat()
            
            # Insert or update
            result = await self._upsert_record(
                table_id=table_id,
                record=chunk,
                unique_key=('view_fqdn', 'chunk_index')
            )
            results.append(result)
        
        return results
    
    async def store_dataset_summary(self, summary_data: Dict[str, Any]) -> str:
        """Store dataset summary with embedding"""
        
        table_id = f"{self.project_id}.{self.dataset_id}.catalog_summary"
        
        # Generate embedding
        if summary_data.get('summary_chunk'):
            embedding = await self._generate_embedding(summary_data['summary_chunk'])
            summary_data['embedding'] = embedding
            summary_data['embedding_model'] = settings.OPENAI_EMBEDDING_MODEL
        
        # Set timestamp
        summary_data['created_at'] = datetime.utcnow().isoformat()
        
        # Insert or update
        return await self._upsert_record(
            table_id=table_id,
            record=summary_data,
            unique_key=('summary_type', 'summary_key')
        )
    
    async def mark_outdated_records(self, table_fqdn: str) -> None:
        """Mark existing records as outdated before sync"""
        
        tables = [
            'catalog_table_context',
            'catalog_column_chunks',
            'catalog_view_queries'
        ]
        
        for table in tables:
            query = f"""
            UPDATE `{self.project_id}.{self.dataset_id}.{table}`
            SET sync_status = 'outdated',
                updated_at = CURRENT_TIMESTAMP()
            WHERE table_fqdn = @table_fqdn
                AND sync_status = 'current'
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("table_fqdn", "STRING", table_fqdn)
                ]
            )
            
            try:
                job = self.client.query(query, job_config=job_config)
                job.result()
            except Exception as e:
                logger.error(f"Failed to mark records as outdated in {table}: {str(e)}")
    
    async def delete_outdated_records(self) -> Dict[str, int]:
        """Delete records marked as outdated after sync"""
        
        results = {}
        tables = [
            'catalog_table_context',
            'catalog_column_chunks', 
            'catalog_view_queries'
        ]
        
        for table in tables:
            query = f"""
            DELETE FROM `{self.project_id}.{self.dataset_id}.{table}`
            WHERE sync_status = 'outdated'
            """
            
            try:
                job = self.client.query(query)
                job.result()
                results[table] = job.num_dml_affected_rows or 0
            except Exception as e:
                logger.error(f"Failed to delete outdated records from {table}: {str(e)}")
                results[table] = -1
        
        return results
    
    async def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status across all catalog tables"""
        
        query = f"""
        WITH status_summary AS (
            SELECT 
                'catalog_table_context' as table_name,
                sync_status,
                COUNT(*) as count,
                MAX(catalog_version) as latest_version,
                MIN(created_at) as oldest_record,
                MAX(created_at) as newest_record
            FROM `{self.project_id}.{self.dataset_id}.catalog_table_context`
            GROUP BY sync_status
            
            UNION ALL
            
            SELECT 
                'catalog_column_chunks' as table_name,
                sync_status,
                COUNT(*) as count,
                MAX(catalog_version) as latest_version,
                MIN(created_at) as oldest_record,
                MAX(created_at) as newest_record
            FROM `{self.project_id}.{self.dataset_id}.catalog_column_chunks`
            GROUP BY sync_status
            
            UNION ALL
            
            SELECT 
                'catalog_view_queries' as table_name,
                sync_status,
                COUNT(*) as count,
                MAX(catalog_version) as latest_version,
                MIN(created_at) as oldest_record,
                MAX(created_at) as newest_record
            FROM `{self.project_id}.{self.dataset_id}.catalog_view_queries`
            GROUP BY sync_status
        )
        SELECT * FROM status_summary
        ORDER BY table_name, sync_status
        """
        
        try:
            results = self.client.query(query).result()
            
            status = {}
            for row in results:
                table = row['table_name']
                if table not in status:
                    status[table] = {}
                
                status[table][row['sync_status']] = {
                    'count': row['count'],
                    'latest_version': row['latest_version'].isoformat() if row['latest_version'] else None,
                    'oldest_record': row['oldest_record'].isoformat() if row['oldest_record'] else None,
                    'newest_record': row['newest_record'].isoformat() if row['newest_record'] else None
                }
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get sync status: {str(e)}")
            return {}
    
    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI"""
        
        # Lazy initialization of embedding service
        if not self.embedding_service:
            from ..services.embedding_service import EmbeddingService
            self.embedding_service = EmbeddingService()
        
        try:
            return await self.embedding_service.generate_embedding(text)
        except Exception as e:
            logger.warning(f"Failed to generate embedding: {str(e)}")
            return []  # Return empty embedding on failure
    
    async def _upsert_record(self, table_id: str, record: Dict[str, Any], 
                           unique_key: Any) -> str:
        """Insert or update a record based on unique key"""
        
        # Generate ID if not provided
        if not record.get('id'):
            import uuid
            record['id'] = str(uuid.uuid4())
        
        # Build merge query based on unique key type
        if isinstance(unique_key, tuple):
            # Composite key
            key_conditions = " AND ".join([f"T.{k} = S.{k}" for k in unique_key])
        else:
            # Single key
            key_conditions = f"T.{unique_key} = S.{unique_key}"
        
        # Prepare record for insertion
        # Convert arrays and complex types to JSON strings for BigQuery
        prepared_record = {}
        for k, v in record.items():
            if isinstance(v, (list, dict)) and k not in ['embedding', 'column_names', 'tables_referenced']:
                prepared_record[k] = json.dumps(v)
            else:
                prepared_record[k] = v
        
        # Use streaming insert for simplicity (could optimize with MERGE later)
        try:
            table = self.client.get_table(table_id)
            errors = self.client.insert_rows_json(table, [prepared_record])
            
            if errors:
                logger.error(f"Failed to insert record: {errors}")
                raise Exception(f"Insert failed: {errors}")
            
            return record['id']
            
        except Exception as e:
            logger.error(f"Failed to upsert record: {str(e)}")
            raise