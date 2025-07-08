"""
Service for querying catalog data from BigQuery
"""
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from google.cloud import bigquery
from google.cloud.exceptions import GoogleCloudError

from ..config.settings import settings

logger = logging.getLogger(__name__)

class CatalogQuerier:
    """Service for querying catalog data from BigQuery"""
    
    def __init__(self, catalog_project: Optional[str] = None, catalog_dataset: Optional[str] = None):
        self.catalog_project = catalog_project or settings.CATALOG_PROJECT
        self.catalog_dataset = catalog_dataset or settings.CATALOG_DATASET
        self.client = bigquery.Client(project=settings.BIGQUERY_PROJECT)
    
    async def fetch_catalog_data(self, dataset_filter: Optional[str] = None) -> Tuple[List[Dict], List[Dict]]:
        """
        Fetch catalog data from BigQuery tables
        Returns: (datasets, tables_with_columns_and_views)
        """
        
        # Build dataset filter condition
        dataset_condition = ""
        if dataset_filter:
            dataset_condition = f"AND dataset_id = '{dataset_filter}'"
        
        # Query 1: Get datasets
        datasets_query = f"""
        SELECT 
            project_id,
            dataset_id,
            dataset_fqdn,
            business_domain,
            dataset_type,
            owner_email,
            refresh_cadence,
            source_system,
            description,
            row_count_last_audit,
            last_updated_ts
        FROM `{self.catalog_project}.{self.catalog_dataset}.Dataset_Metadata`
        WHERE status = 'In Use'
        {dataset_condition}
        ORDER BY dataset_id
        """
        
        # Query 2: Get tables and views
        tables_query = f"""
        SELECT 
            t.project_id,
            t.dataset_id,
            t.table_id,
            t.table_fqdn,
            t.object_type,
            t.business_domain,
            t.grain_description,
            t.row_count AS row_count_last_audit,
            t.column_count,
            t.last_updated_ts,
            t.column_profile_last_audit,
            t.column_profile_due
        FROM `{self.catalog_project}.{self.catalog_dataset}.Table_Metadata` t
        WHERE t.status = 'In Use' 
            AND t.exists_flag = TRUE
            {dataset_condition.replace('dataset_id', 't.dataset_id')}
        ORDER BY t.dataset_id, t.table_id
        """
        
        # Query 3: Get columns
        columns_query = f"""
        SELECT 
            c.project_id,
            c.dataset_id,
            c.table_id,
            c.column_name,
            c.data_type,
            c.is_nullable,
            c.description,
            c.distinct_count,
            c.null_count,
            c.blank_count,
            c.row_count,
            c.min_value,
            c.max_value,
            c.average_value,
            c.top_5_values,
            c.sample_values,
            c.profile_timestamp,
            c.pii_flag
        FROM `{self.catalog_project}.{self.catalog_dataset}.Column_Metadata` c
        WHERE c.exists_flag = TRUE
        ORDER BY c.dataset_id, c.table_id, c.column_name
        """
        
        # Query 4: Get view queries
        views_query = f"""
        SELECT 
            v.project_id,
            v.dataset_id,
            v.view_name,
            v.sql_query as query,
            v.view_type
        FROM `{self.catalog_project}.{self.catalog_dataset}.View_Definitions` v
        ORDER BY v.dataset_id, v.view_name
        """
        
        # Query 5: Get Hevo models (optional)
        hevo_query = f"""
        SELECT 
            h.table_fqdn,
            h.hevo_model_id,
            h.hevo_model_name,
            h.hevo_query as query,
            h.hevo_model_last_run_at,
            h.hevo_model_status
        FROM `{self.catalog_project}.{self.catalog_dataset}.Hevo_Models` h
        WHERE h.hevo_model_status = 'ACTIVE'
        ORDER BY h.table_fqdn
        """
        
        try:
            # Execute queries
            logger.info("Fetching datasets from catalog...")
            datasets = list(self.client.query(datasets_query).result())
            datasets_list = [dict(row) for row in datasets]
            logger.info(f"Found {len(datasets_list)} datasets")
            
            logger.info("Fetching tables from catalog...")
            tables = list(self.client.query(tables_query).result())
            tables_dict = {}
            for row in tables:
                table_data = dict(row)
                table_key = f"{table_data['project_id']}.{table_data['dataset_id']}.{table_data['table_id']}"
                table_data['columns'] = []
                tables_dict[table_key] = table_data
            logger.info(f"Found {len(tables_dict)} tables/views")
            
            logger.info("Fetching columns from catalog...")
            columns = list(self.client.query(columns_query).result())
            for row in columns:
                col_data = dict(row)
                table_key = f"{col_data['project_id']}.{col_data['dataset_id']}.{col_data['table_id']}"
                if table_key in tables_dict:
                    tables_dict[table_key]['columns'].append(col_data)
            
            logger.info("Fetching view definitions...")
            views = list(self.client.query(views_query).result())
            for row in views:
                view_data = dict(row)
                view_key = f"{view_data['project_id']}.{view_data['dataset_id']}.{view_data['view_name']}"
                if view_key in tables_dict:
                    tables_dict[view_key]['query'] = view_data['query']
                    tables_dict[view_key]['query_source'] = 'view'
                    tables_dict[view_key]['view_type'] = view_data.get('view_type', 'STANDARD').lower()
            
            # Try to get Hevo models (optional)
            try:
                logger.info("Fetching Hevo models...")
                hevo_models = list(self.client.query(hevo_query).result())
                for row in hevo_models:
                    hevo_data = dict(row)
                    table_fqdn = hevo_data['table_fqdn']
                    if table_fqdn in tables_dict and not tables_dict[table_fqdn].get('query'):
                        tables_dict[table_fqdn]['query'] = hevo_data['query']
                        tables_dict[table_fqdn]['query_source'] = 'hevo'
            except Exception as e:
                logger.warning(f"Failed to fetch Hevo models (non-critical): {str(e)}")
            
            # Convert tables dict to list
            tables_list = list(tables_dict.values())
            
            # Group tables by dataset for JSON structure compatibility
            for dataset in datasets_list:
                dataset_key = f"{dataset['project_id']}.{dataset['dataset_id']}"
                dataset['tables'] = [
                    t for t in tables_list 
                    if f"{t['project_id']}.{t['dataset_id']}" == dataset_key
                ]
            
            return datasets_list, tables_list
            
        except GoogleCloudError as e:
            logger.error(f"BigQuery error while fetching catalog: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error while fetching catalog: {str(e)}")
            raise
    
    async def fetch_from_json(self, json_path: str) -> Tuple[List[Dict], List[Dict]]:
        """
        Alternative method to load catalog from exported JSON file
        Returns: (datasets, tables_with_columns)
        """
        
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            
            if 'catalog' not in data:
                raise ValueError("Invalid catalog JSON format - missing 'catalog' key")
            
            datasets = data['catalog']
            all_tables = []
            
            # Flatten the structure to match BigQuery query results
            for dataset in datasets:
                tables = dataset.pop('tables', [])
                for table in tables:
                    # Add dataset info to each table
                    table['dataset_id'] = dataset['dataset_id']
                    table['project_id'] = dataset['project_id']
                    
                    # Ensure table_fqdn exists
                    if 'table_fqdn' not in table:
                        table['table_fqdn'] = f"{table['project_id']}.{table['dataset_id']}.{table['table_id']}"
                    
                    all_tables.append(table)
                
                # Add tables back to dataset for compatibility
                dataset['tables'] = tables
            
            logger.info(f"Loaded {len(datasets)} datasets and {len(all_tables)} tables from JSON")
            return datasets, all_tables
            
        except FileNotFoundError:
            logger.error(f"Catalog JSON file not found: {json_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in catalog file: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error loading catalog from JSON: {str(e)}")
            raise
    
    async def get_table_context(self, table_fqdns: List[str]) -> List[Dict[str, Any]]:
        """Get stored table context for specific tables"""
        
        if not table_fqdns:
            return []
        
        # Build IN clause
        table_list = ", ".join([f"'{t}'" for t in table_fqdns])
        
        query = f"""
        SELECT 
            table_fqdn,
            context_chunk,
            business_domain,
            grain_description,
            row_count,
            column_count,
            catalog_version
        FROM `{settings.BIGQUERY_PROJECT}.vannabq.catalog_table_context`
        WHERE table_fqdn IN ({table_list})
            AND sync_status = 'current'
        """
        
        try:
            results = self.client.query(query).result()
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Failed to get table context: {str(e)}")
            return []
    
    async def get_column_info(self, table_fqdns: List[str]) -> List[Dict[str, Any]]:
        """Get stored column information for specific tables"""
        
        if not table_fqdns:
            return []
        
        table_list = ", ".join([f"'{t}'" for t in table_fqdns])
        
        query = f"""
        SELECT 
            table_fqdn,
            chunk_index,
            column_chunk,
            column_names,
            has_pii,
            null_percentage
        FROM `{settings.BIGQUERY_PROJECT}.vannabq.catalog_column_chunks`
        WHERE table_fqdn IN ({table_list})
            AND sync_status = 'current'
        ORDER BY table_fqdn, chunk_index
        """
        
        try:
            results = self.client.query(query).result()
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Failed to get column info: {str(e)}")
            return []
    
    async def find_similar_queries(self, embedding: List[float], limit: int = 5) -> List[Dict[str, Any]]:
        """Find similar view queries using vector search"""
        
        # Note: BigQuery doesn't have native vector search yet
        # This is a placeholder for when it's available or if using an extension
        # For now, return empty list
        
        logger.warning("Vector search not yet implemented in BigQuery")
        return []
    
    async def search_by_domain(self, business_domain: str) -> List[Dict[str, Any]]:
        """Search catalog by business domain"""
        
        query = f"""
        SELECT 
            table_fqdn,
            context_chunk,
            grain_description,
            row_count,
            column_count
        FROM `{settings.BIGQUERY_PROJECT}.vannabq.catalog_table_context`
        WHERE business_domain = @domain
            AND sync_status = 'current'
        ORDER BY row_count DESC
        LIMIT 50
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("domain", "STRING", business_domain)
            ]
        )
        
        try:
            results = self.client.query(query, job_config=job_config).result()
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Failed to search by domain: {str(e)}")
            return []