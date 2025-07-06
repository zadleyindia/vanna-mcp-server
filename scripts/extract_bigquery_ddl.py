#!/usr/bin/env python3
"""
Extract DDL from BigQuery tables and enhance with metadata from data catalog
This script connects to BigQuery and extracts table structures for Vanna training
"""
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent))

from google.cloud import bigquery
from src.config.settings import settings
from src.config.vanna_config import get_vanna

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BigQueryDDLExtractor:
    """Extract and enhance DDL from BigQuery"""
    
    def __init__(self):
        """Initialize BigQuery client"""
        self.client = bigquery.Client(project=settings.BIGQUERY_PROJECT)
        self.catalog_dataset = "metadata_data_dictionary"
        self.vanna = get_vanna()
        
    def get_datasets(self) -> List[str]:
        """Get list of datasets, respecting access control"""
        all_datasets = []
        
        for dataset in self.client.list_datasets():
            dataset_id = dataset.dataset_id
            
            # Check access control
            if self._is_dataset_allowed(dataset_id):
                all_datasets.append(dataset_id)
                logger.info(f"Including dataset: {dataset_id}")
            else:
                logger.info(f"Skipping dataset: {dataset_id} (access control)")
                
        return all_datasets
    
    def _is_dataset_allowed(self, dataset_id: str) -> bool:
        """Check if dataset is allowed based on access control settings"""
        control_mode = settings.ACCESS_CONTROL_MODE
        control_list = settings.get_access_control_list()
        
        if not control_list:
            return True  # No control list means allow all
            
        if control_mode == "whitelist":
            return dataset_id in control_list
        elif control_mode == "blacklist":
            return dataset_id not in control_list
        
        return True
    
    def get_table_metadata(self, dataset_id: str, table_id: str) -> Optional[Dict[str, Any]]:
        """Get metadata from the data catalog for a specific table"""
        try:
            query = f"""
            SELECT 
                tm.description as table_description,
                tm.business_domain,
                tm.row_count_last_audit,
                tm.grain_description,
                cm.column_name,
                cm.description as column_description,
                cm.data_type,
                cm.is_nullable,
                cm.distinct_count,
                cm.sample_values,
                cm.top_5_values
            FROM `{settings.BIGQUERY_PROJECT}.{self.catalog_dataset}.Table_Metadata` tm
            LEFT JOIN `{settings.BIGQUERY_PROJECT}.{self.catalog_dataset}.Column_Metadata` cm
                ON tm.table_fqdn = cm.table_fqdn
            WHERE tm.dataset_id = @dataset_id
            AND tm.table_id = @table_id
            """
            
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("dataset_id", "STRING", dataset_id),
                    bigquery.ScalarQueryParameter("table_id", "STRING", table_id)
                ]
            )
            
            results = self.client.query(query, job_config=job_config).result()
            
            metadata = {
                "table_info": {},
                "columns": {}
            }
            
            for row in results:
                if not metadata["table_info"]:
                    metadata["table_info"] = {
                        "description": row.table_description,
                        "business_domain": row.business_domain,
                        "row_count": row.row_count_last_audit,
                        "grain_description": row.grain_description
                    }
                
                if row.column_name:
                    metadata["columns"][row.column_name] = {
                        "description": row.column_description,
                        "data_type": row.data_type,
                        "is_nullable": row.is_nullable,
                        "distinct_count": row.distinct_count,
                        "sample_values": row.sample_values,
                        "top_5_values": row.top_5_values
                    }
            
            return metadata if metadata["columns"] else None
            
        except Exception as e:
            logger.warning(f"Could not fetch metadata for {dataset_id}.{table_id}: {e}")
            return None
    
    def generate_enhanced_ddl(self, dataset_id: str, table_id: str) -> str:
        """Generate DDL with metadata as comments"""
        table_ref = f"{settings.BIGQUERY_PROJECT}.{dataset_id}.{table_id}"
        
        # Get table schema
        table = self.client.get_table(table_ref)
        
        # Get metadata from catalog
        metadata = self.get_table_metadata(dataset_id, table_id)
        
        # Build enhanced DDL
        ddl_parts = []
        
        # Table comment
        table_comment = ""
        if metadata and metadata["table_info"].get("description"):
            table_comment = metadata["table_info"]["description"]
            if metadata["table_info"].get("row_count"):
                table_comment += f" ({metadata['table_info']['row_count']} rows)"
        
        # Start DDL
        ddl_parts.append(f"-- Table: {table_ref}")
        if table_comment:
            ddl_parts.append(f"-- {table_comment}")
        ddl_parts.append(f"CREATE TABLE `{table_ref}` (")
        
        # Add columns with metadata
        column_definitions = []
        for field in table.schema:
            col_def = f"  {field.name} {field.field_type}"
            
            # Add column metadata as comment
            col_metadata = metadata["columns"].get(field.name) if metadata else None
            if col_metadata:
                comments = []
                
                if col_metadata.get("description"):
                    comments.append(col_metadata["description"])
                
                if col_metadata.get("sample_values"):
                    comments.append(f"Samples: {col_metadata['sample_values']}")
                
                if col_metadata.get("top_5_values"):
                    comments.append(f"Top values: {col_metadata['top_5_values']}")
                
                if comments:
                    col_def += f" -- {'; '.join(comments)}"
            
            column_definitions.append(col_def)
        
        ddl_parts.append(",\n".join(column_definitions))
        ddl_parts.append(")")
        
        # Add table-level comment
        if table_comment:
            ddl_parts.append(f"COMMENT '{table_comment}'")
        
        ddl_parts.append(";")
        
        return "\n".join(ddl_parts)
    
    def extract_and_train_ddl(self, dataset_id: str, table_id: str) -> bool:
        """Extract DDL and train Vanna with it"""
        try:
            logger.info(f"Processing {dataset_id}.{table_id}")
            
            # Generate enhanced DDL
            ddl = self.generate_enhanced_ddl(dataset_id, table_id)
            
            # Create documentation from metadata
            metadata = self.get_table_metadata(dataset_id, table_id)
            documentation = None
            
            if metadata and metadata["table_info"].get("description"):
                doc_parts = [
                    f"Table: {dataset_id}.{table_id}",
                    f"Description: {metadata['table_info']['description']}"
                ]
                
                if metadata["table_info"].get("business_domain"):
                    doc_parts.append(f"Business Domain: {metadata['table_info']['business_domain']}")
                
                if metadata["table_info"].get("grain_description"):
                    doc_parts.append(f"Grain: {metadata['table_info']['grain_description']}")
                
                documentation = "\n".join(doc_parts)
            
            # Train Vanna with DDL
            logger.info(f"Training Vanna with DDL for {dataset_id}.{table_id}")
            success = self.vanna.train(ddl=ddl)
            
            # Train with documentation if available
            if documentation:
                logger.info(f"Training Vanna with documentation for {dataset_id}.{table_id}")
                self.vanna.train(documentation=documentation)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to process {dataset_id}.{table_id}: {e}")
            return False
    
    def extract_all_ddl(self, limit: Optional[int] = None):
        """Extract DDL for all allowed tables"""
        datasets = self.get_datasets()
        
        total_processed = 0
        successful = 0
        failed = 0
        
        for dataset_id in datasets:
            if limit and total_processed >= limit:
                break
                
            try:
                # List tables in dataset
                dataset_ref = self.client.dataset(dataset_id)
                tables = list(self.client.list_tables(dataset_ref))
                
                for table in tables:
                    if limit and total_processed >= limit:
                        break
                    
                    if self.extract_and_train_ddl(dataset_id, table.table_id):
                        successful += 1
                    else:
                        failed += 1
                    
                    total_processed += 1
                    
            except Exception as e:
                logger.error(f"Failed to process dataset {dataset_id}: {e}")
        
        logger.info(f"\nExtraction complete!")
        logger.info(f"Total tables processed: {total_processed}")
        logger.info(f"Successful: {successful}")
        logger.info(f"Failed: {failed}")
        
        return {
            "total": total_processed,
            "successful": successful,
            "failed": failed
        }

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract BigQuery DDL for Vanna training")
    parser.add_argument("--dataset", help="Extract specific dataset only")
    parser.add_argument("--table", help="Extract specific table only (requires --dataset)")
    parser.add_argument("--limit", type=int, help="Limit number of tables to process")
    parser.add_argument("--dry-run", action="store_true", help="Show DDL without training")
    
    args = parser.parse_args()
    
    extractor = BigQueryDDLExtractor()
    
    if args.dataset and args.table:
        # Single table
        if args.dry_run:
            ddl = extractor.generate_enhanced_ddl(args.dataset, args.table)
            print(ddl)
        else:
            success = extractor.extract_and_train_ddl(args.dataset, args.table)
            sys.exit(0 if success else 1)
    
    elif args.dataset:
        # Single dataset
        logger.info(f"Processing dataset: {args.dataset}")
        # Implementation for single dataset
        
    else:
        # All datasets
        if args.dry_run:
            logger.info("Dry run - would process these datasets:")
            for dataset in extractor.get_datasets():
                print(f"  - {dataset}")
        else:
            extractor.extract_all_ddl(limit=args.limit)

if __name__ == "__main__":
    main()