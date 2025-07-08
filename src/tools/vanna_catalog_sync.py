"""
Vanna Catalog Sync Tool - Synchronize Data Catalog with Vanna training data
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..config.settings import settings
from ..catalog_integration.querier import CatalogQuerier
from ..catalog_integration.chunker import CatalogChunker
from ..catalog_integration.storage import CatalogStorage

logger = logging.getLogger(__name__)

async def vanna_catalog_sync(
    source: str = "bigquery",  # "bigquery" or "json"
    mode: str = "incremental",  # "incremental", "full", "init", "status"
    dataset_filter: Optional[str] = None,
    json_path: Optional[str] = None,
    dry_run: bool = False,
    chunk_size: Optional[int] = None,
    include_views: Optional[bool] = None,
    include_column_stats: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Synchronize Data Catalog with Vanna training data
    
    Args:
        source: Data source - "bigquery" (query catalog tables) or "json" (load from file)
        mode: Sync mode - "incremental", "full", "init" (setup tables), "status"
        dataset_filter: Filter specific dataset (e.g., "SQL_ZADLEY")
        json_path: Path to catalog JSON file (required if source="json")
        dry_run: If true, show what would be synced without making changes
        chunk_size: Override default column chunk size
        include_views: Override config for including view SQL patterns
        include_column_stats: Override config for including column statistics
    
    Returns:
        Dictionary with sync results and statistics
    """
    
    # Check if catalog integration is enabled
    if not settings.CATALOG_ENABLED:
        return {
            "success": False,
            "error": "Catalog integration is not enabled. Set CATALOG_ENABLED=true in config.",
            "recommendation": "Add CATALOG_ENABLED=true to your environment variables"
        }
    
    # Validate inputs
    if source == "json" and not json_path:
        return {
            "success": False,
            "error": "json_path is required when source='json'",
            "example": "Use: json_path='/path/to/catalog.json'"
        }
    
    # Use config defaults with overrides
    chunk_size = chunk_size or settings.CATALOG_CHUNK_SIZE
    include_views = include_views if include_views is not None else settings.CATALOG_INCLUDE_VIEWS
    include_column_stats = include_column_stats if include_column_stats is not None else settings.CATALOG_INCLUDE_COLUMN_STATS
    
    try:
        # Initialize services
        querier = CatalogQuerier()
        chunker = CatalogChunker(
            max_chunk_tokens=settings.CATALOG_MAX_TOKENS,
            column_batch_size=chunk_size
        )
        storage = CatalogStorage()
        
        # Handle different modes
        if mode == "init":
            return await _initialize_catalog_tables(storage)
        
        elif mode == "status":
            return await _get_catalog_status(storage)
        
        elif mode in ["incremental", "full"]:
            return await _sync_catalog_data(
                querier=querier,
                chunker=chunker,
                storage=storage,
                source=source,
                mode=mode,
                dataset_filter=dataset_filter,
                json_path=json_path,
                dry_run=dry_run,
                include_views=include_views,
                include_column_stats=include_column_stats
            )
        
        else:
            return {
                "success": False,
                "error": f"Unknown mode: {mode}",
                "valid_modes": ["init", "status", "incremental", "full"]
            }
    
    except Exception as e:
        logger.error(f"Catalog sync failed: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "troubleshooting": [
                "Check BigQuery permissions for catalog project",
                "Verify catalog dataset exists",
                "Ensure OpenAI API key is valid",
                "Check network connectivity"
            ]
        }

async def _initialize_catalog_tables(storage: CatalogStorage) -> Dict[str, Any]:
    """Initialize catalog storage tables"""
    
    logger.info("Initializing catalog tables...")
    
    try:
        results = await storage.initialize_tables()
        
        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)
        
        return {
            "success": success_count == total_count,
            "mode": "init",
            "tables_created": results,
            "summary": f"Created {success_count}/{total_count} tables successfully",
            "next_steps": [
                "Run with mode='full' to perform initial sync",
                "Set CATALOG_ENABLED=true in your config",
                "Optionally set CATALOG_DATASET_FILTER to limit scope"
            ]
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to initialize tables: {str(e)}"
        }

async def _get_catalog_status(storage: CatalogStorage) -> Dict[str, Any]:
    """Get current catalog sync status"""
    
    try:
        status = await storage.get_sync_status()
        
        # Calculate summary statistics
        total_records = 0
        outdated_records = 0
        
        for table_name, table_status in status.items():
            for sync_status, info in table_status.items():
                total_records += info['count']
                if sync_status == 'outdated':
                    outdated_records += info['count']
        
        return {
            "success": True,
            "mode": "status",
            "tables": status,
            "summary": {
                "total_records": total_records,
                "outdated_records": outdated_records,
                "sync_health": "good" if outdated_records == 0 else "needs_sync"
            },
            "recommendations": [
                "Run mode='incremental' to update outdated records" if outdated_records > 0 else "Catalog is up to date",
                "Run mode='full' for complete refresh if needed"
            ]
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to get status: {str(e)}"
        }

async def _sync_catalog_data(
    querier: CatalogQuerier,
    chunker: CatalogChunker,
    storage: CatalogStorage,
    source: str,
    mode: str,
    dataset_filter: Optional[str],
    json_path: Optional[str],
    dry_run: bool,
    include_views: bool,
    include_column_stats: bool
) -> Dict[str, Any]:
    """Perform catalog data synchronization"""
    
    start_time = datetime.now()
    
    # Track what we're going to sync
    sync_plan = {
        "datasets": 0,
        "tables": 0,
        "views": 0,
        "column_chunks": 0,
        "view_chunks": 0,
        "summary_chunks": 0
    }
    
    try:
        # Fetch catalog data
        logger.info(f"Fetching catalog data from {source}...")
        
        if source == "bigquery":
            datasets, all_tables = await querier.fetch_catalog_data(dataset_filter)
        else:  # source == "json"
            datasets, all_tables = await querier.fetch_from_json(json_path)
        
        sync_plan["datasets"] = len(datasets)
        sync_plan["tables"] = len([t for t in all_tables if t.get('object_type') != 'VIEW'])
        sync_plan["views"] = len([t for t in all_tables if t.get('object_type') == 'VIEW'])
        
        logger.info(f"Found {sync_plan['datasets']} datasets, {sync_plan['tables']} tables, {sync_plan['views']} views")
        
        if dry_run:
            # Calculate what would be chunked
            for dataset in datasets:
                for table in dataset.get('tables', []):
                    columns = table.get('columns', [])
                    if columns and include_column_stats:
                        column_chunks = len(chunker.chunk_columns(table, columns))
                        sync_plan["column_chunks"] += column_chunks
                    
                    if table.get('query') and include_views:
                        view_chunks = len(chunker.chunk_view_query(table))
                        sync_plan["view_chunks"] += view_chunks
                
                sync_plan["summary_chunks"] += 1  # One per dataset
            
            return {
                "success": True,
                "mode": mode,
                "dry_run": True,
                "plan": sync_plan,
                "estimated_chunks": (
                    sync_plan["datasets"] +  # table contexts
                    sync_plan["column_chunks"] +
                    sync_plan["view_chunks"] +
                    sync_plan["summary_chunks"]
                ),
                "message": "This is what would be synced. Run with dry_run=false to execute."
            }
        
        # Perform actual sync
        sync_results = {
            "datasets_processed": 0,
            "tables_synced": 0,
            "column_chunks_created": 0,
            "view_chunks_created": 0,
            "summary_chunks_created": 0,
            "errors": []
        }
        
        # Process each dataset
        for dataset in datasets:
            try:
                dataset_tables = dataset.get('tables', [])
                
                # Create dataset summary
                summary_chunk = chunker.create_dataset_summary(dataset, dataset_tables)
                if not dry_run:
                    await storage.store_dataset_summary(summary_chunk)
                    sync_results["summary_chunks_created"] += 1
                
                # Process each table/view
                for table in dataset_tables:
                    try:
                        # Store table context
                        table_context = chunker.chunk_table_context(table, dataset)
                        if not dry_run:
                            await storage.store_table_context(table_context)
                            sync_results["tables_synced"] += 1
                        
                        # Store column information if available
                        columns = table.get('columns', [])
                        if columns and include_column_stats:
                            column_chunks = chunker.chunk_columns(table, columns)
                            if not dry_run and column_chunks:
                                await storage.store_column_chunks(column_chunks)
                                sync_results["column_chunks_created"] += len(column_chunks)
                        
                        # Store view queries if available
                        if table.get('query') and include_views:
                            view_chunks = chunker.chunk_view_query(table)
                            if not dry_run and view_chunks:
                                await storage.store_view_queries(view_chunks)
                                sync_results["view_chunks_created"] += len(view_chunks)
                    
                    except Exception as e:
                        error_msg = f"Failed to sync table {table.get('table_fqdn', 'unknown')}: {str(e)}"
                        logger.error(error_msg)
                        sync_results["errors"].append(error_msg)
                
                sync_results["datasets_processed"] += 1
                
            except Exception as e:
                error_msg = f"Failed to sync dataset {dataset.get('dataset_id', 'unknown')}: {str(e)}"
                logger.error(error_msg)
                sync_results["errors"].append(error_msg)
        
        # Clean up outdated records if full sync
        if mode == "full" and not dry_run:
            deleted_counts = await storage.delete_outdated_records()
            sync_results["deleted_outdated"] = deleted_counts
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        return {
            "success": len(sync_results["errors"]) == 0,
            "mode": mode,
            "source": source,
            "dataset_filter": dataset_filter,
            "duration_seconds": round(duration, 2),
            "results": sync_results,
            "configuration": {
                "chunk_size": chunker.column_batch_size,
                "max_tokens": chunker.max_chunk_tokens,
                "include_views": include_views,
                "include_column_stats": include_column_stats
            },
            "next_steps": [
                "Use vanna_ask to test enhanced query generation",
                "Check logs for any embedding generation issues",
                "Run mode='status' to verify sync completed"
            ] if sync_results["errors"] == 0 else [
                "Review errors and fix underlying issues",
                "Consider running mode='incremental' to retry failed items"
            ]
        }
        
    except Exception as e:
        logger.error(f"Sync operation failed: {str(e)}", exc_info=True)
        raise