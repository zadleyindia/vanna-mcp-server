"""
vanna_batch_train_ddl tool - Auto-generate and train DDLs for tables with data
Supports both BigQuery and MS SQL Server
"""
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
from google.cloud import bigquery
import pyodbc
from src.config.vanna_config import get_vanna
from src.config.settings import settings
from src.tools.vanna_train import vanna_train
from src.tools.vanna_remove_training import vanna_remove_training
from src.tools.vanna_get_training_data import vanna_get_training_data

logger = logging.getLogger(__name__)

async def vanna_batch_train_ddl(
    dataset_id: str,
    tenant_id: Optional[str] = None,
    min_row_count: int = 1,
    include_row_counts: bool = True,
    table_pattern: Optional[str] = None,
    dry_run: bool = False,
    remove_existing: bool = True
) -> Dict[str, Any]:
    """
    Auto-generate and train DDLs for tables with data (BigQuery and MS SQL).
    
    This tool automatically:
    1. Queries system tables to find tables with row_count >= min_row_count
    2. Generates DDL statements for qualifying tables
    3. Removes existing DDLs for the dataset/database (optional)
    4. Trains Vanna with the new DDLs including row count metadata
    
    Args:
        dataset_id (str): Dataset/Database ID to process
            - BigQuery: "sales_data" or "project.sales_data"
            - MS SQL: database name like "zadley" or "schema.table_pattern" like "dbo.*"
            
        tenant_id (str, optional): Override default tenant for multi-tenant mode
            Default: Uses settings.TENANT_ID
            
        min_row_count (int): Minimum row count threshold
            Default: 1 (exclude empty tables)
            
        include_row_counts (bool): Include row count in DDL documentation
            Default: True
            
        table_pattern (str, optional): Filter tables by name pattern
            Example: "sales_*" to only process tables starting with "sales_"
            Default: None (process all tables)
            
        dry_run (bool): Preview what would be trained without making changes
            Default: False
            
        remove_existing (bool): Remove existing DDLs before adding new ones
            Default: True (replace mode)
    
    Returns:
        Dict containing:
        - success (bool): Whether operation succeeded
        - dataset_processed (str): Dataset that was processed
        - tables_trained (list): Tables with DDLs generated
        - tables_skipped (list): Tables skipped due to low row count
        - removed_count (int): Number of existing DDLs removed
        - errors (list): Any errors encountered
        - dry_run (bool): Whether this was a dry run
        
    Example Usage:
        # BigQuery - Train DDLs for all tables with data
        vanna_batch_train_ddl(
            dataset_id="sales_data",
            min_row_count=100
        )
        
        # MS SQL - Train DDLs for zadley database
        vanna_batch_train_ddl(
            dataset_id="zadley",
            min_row_count=100
        )
        
        # MS SQL - Train DDLs for specific schema
        vanna_batch_train_ddl(
            dataset_id="zadley.dbo",
            table_pattern="sales_*"
        )
    """
    try:
        # Validate inputs
        if not dataset_id:
            return {
                "success": False,
                "error": "dataset_id is required",
                "example": "Provide dataset_id like 'sales_data' (BigQuery) or 'zadley' (MS SQL)"
            }
        
        # Check database type
        database_type = settings.DATABASE_TYPE
        if database_type not in ["bigquery", "mssql"]:
            return {
                "success": False,
                "error": f"This tool only supports BigQuery and MS SQL databases",
                "current_database": database_type,
                "supported_databases": ["bigquery", "mssql"]
            }
        
        # Route to appropriate database handler
        if database_type == "bigquery":
            return await _handle_bigquery_batch_ddl(
                dataset_id=dataset_id,
                tenant_id=tenant_id,
                min_row_count=min_row_count,
                include_row_counts=include_row_counts,
                table_pattern=table_pattern,
                dry_run=dry_run,
                remove_existing=remove_existing
            )
        else:  # mssql
            return await _handle_mssql_batch_ddl(
                dataset_id=dataset_id,
                tenant_id=tenant_id,
                min_row_count=min_row_count,
                include_row_counts=include_row_counts,
                table_pattern=table_pattern,
                dry_run=dry_run,
                remove_existing=remove_existing
            )
        
    except Exception as e:
        logger.error(f"Error in vanna_batch_train_ddl: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": f"Batch DDL training error: {str(e)}",
            "error_type": type(e).__name__,
            "suggestions": [
                "Check dataset_id is correct",
                "Verify database permissions",
                "Ensure database configuration is correct"
            ]
        }

async def _handle_bigquery_batch_ddl(
    dataset_id: str,
    tenant_id: Optional[str],
    min_row_count: int,
    include_row_counts: bool,
    table_pattern: Optional[str],
    dry_run: bool,
    remove_existing: bool
) -> Dict[str, Any]:
    """Handle BigQuery batch DDL generation"""
    
    # Initialize BigQuery client
    try:
        client = bigquery.Client(project=settings.BIGQUERY_PROJECT)
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to initialize BigQuery client: {str(e)}",
            "suggestion": "Check BIGQUERY_PROJECT and credentials configuration"
        }
    
    # Parse dataset reference
    if "." in dataset_id:
        project_id, dataset_name = dataset_id.split(".", 1)
    else:
        project_id = settings.BIGQUERY_PROJECT
        dataset_name = dataset_id
    
    full_dataset_id = f"{project_id}.{dataset_name}"
    
    # Step 1: Query tables with row counts
    logger.info(f"Querying tables in dataset {full_dataset_id} with row_count >= {min_row_count}")
    
    query = f"""
    SELECT 
        table_catalog as project_id,
        table_schema as dataset_id,
        table_name,
        row_count,
        TIMESTAMP_MILLIS(creation_time) as created_at,
        TIMESTAMP_MILLIS(GREATEST(creation_time, IFNULL(last_modified_time, 0))) as last_modified
    FROM `{full_dataset_id}.INFORMATION_SCHEMA.TABLES`
    WHERE table_type = 'BASE TABLE'
      AND row_count >= {min_row_count}
    """
    
    if table_pattern:
        # Convert pattern to SQL LIKE pattern
        sql_pattern = table_pattern.replace("*", "%")
        query += f"\n  AND table_name LIKE '{sql_pattern}'"
    
    query += "\nORDER BY row_count DESC, table_name"
    
    try:
        query_job = client.query(query)
        tables = list(query_job.result())
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to query INFORMATION_SCHEMA: {str(e)}",
            "query": query,
            "suggestion": "Check dataset exists and you have permission to access it"
        }
    
    if not tables:
        return {
            "success": True,
            "dataset_processed": full_dataset_id,
            "database_type": "bigquery",
            "tables_trained": [],
            "tables_skipped": [],
            "message": f"No tables found with row_count >= {min_row_count}",
            "filters_applied": {
                "min_row_count": min_row_count,
                "table_pattern": table_pattern
            }
        }
    
    # Step 2: Remove existing DDLs if requested
    removed_count = await _remove_existing_ddls(dataset_name, tenant_id, remove_existing, dry_run)
    
    # Step 3: Generate and train DDLs
    tables_trained = []
    tables_skipped = []
    errors = []
    
    for table in tables:
        table_name = table.table_name
        row_count = table.row_count
        full_table_name = f"{table.dataset_id}.{table_name}"
        
        try:
            # Get table schema
            table_ref = client.dataset(table.dataset_id).table(table_name)
            table_obj = client.get_table(table_ref)
            
            # Generate DDL
            ddl = _generate_bigquery_ddl(table_obj, include_row_counts, row_count)
            
            if dry_run:
                logger.info(f"[DRY RUN] Would train DDL for {full_table_name} ({row_count:,} rows)")
                tables_trained.append({
                    "table": full_table_name,
                    "row_count": row_count,
                    "columns": len(table_obj.schema),
                    "ddl_preview": ddl[:200] + "..." if len(ddl) > 200 else ddl
                })
            else:
                # Train with the DDL
                train_result = await vanna_train(
                    training_type="ddl",
                    content=ddl,
                    tenant_id=tenant_id,
                    metadata={
                        "source": "batch_train_ddl",
                        "dataset": dataset_name,
                        "row_count": row_count,
                        "generated_at": datetime.now().isoformat()
                    }
                )
                
                if train_result.get("success"):
                    tables_trained.append({
                        "table": full_table_name,
                        "row_count": row_count,
                        "columns": len(table_obj.schema),
                        "training_id": train_result.get("training_id")
                    })
                    logger.info(f"Trained DDL for {full_table_name} ({row_count:,} rows)")
                else:
                    errors.append({
                        "table": full_table_name,
                        "error": train_result.get("error", "Unknown training error")
                    })
            
        except Exception as e:
            error_msg = f"Failed to process {full_table_name}: {str(e)}"
            logger.error(error_msg)
            errors.append({
                "table": full_table_name,
                "error": str(e)
            })
    
    # Step 4: Identify skipped tables
    tables_skipped = await _get_skipped_tables_bigquery(client, full_dataset_id, min_row_count, table_pattern)
    
    return _prepare_response(
        database_type="bigquery",
        dataset_processed=full_dataset_id,
        tables_trained=tables_trained,
        tables_skipped=tables_skipped,
        removed_count=removed_count,
        errors=errors,
        dry_run=dry_run,
        min_row_count=min_row_count
    )

async def _handle_mssql_batch_ddl(
    dataset_id: str,
    tenant_id: Optional[str],
    min_row_count: int,
    include_row_counts: bool,
    table_pattern: Optional[str],
    dry_run: bool,
    remove_existing: bool
) -> Dict[str, Any]:
    """Handle MS SQL batch DDL generation"""
    
    # Parse database/schema from dataset_id
    # Format: "database" or "database.schema"
    if "." in dataset_id:
        database_name, schema_name = dataset_id.split(".", 1)
    else:
        database_name = dataset_id
        schema_name = None  # Will query all schemas
    
    # Create connection
    try:
        conn_str = settings.get_mssql_connection_string()
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to connect to MS SQL: {str(e)}",
            "suggestion": "Check MS SQL connection settings and credentials"
        }
    
    try:
        # Step 1: Query tables with row counts
        logger.info(f"Querying tables in database {database_name} with row_count >= {min_row_count}")
        
        # Build query for MS SQL
        query = f"""
        USE [{database_name}];
        
        SELECT 
            DB_NAME() as database_name,
            s.name as schema_name,
            t.name as table_name,
            SUM(p.rows) as row_count,
            t.create_date as created_at,
            t.modify_date as last_modified
        FROM sys.tables t
        INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
        INNER JOIN sys.partitions p ON t.object_id = p.object_id
        WHERE p.index_id IN (0,1)  -- heap or clustered index
        """
        
        if schema_name:
            query += f"\n  AND s.name = '{schema_name}'"
        
        query += f"\nGROUP BY s.name, t.name, t.create_date, t.modify_date"
        query += f"\nHAVING SUM(p.rows) >= {min_row_count}"
        
        if table_pattern:
            # Convert pattern to SQL LIKE pattern
            sql_pattern = table_pattern.replace("*", "%")
            query += f"\n  AND t.name LIKE '{sql_pattern}'"
        
        query += "\nORDER BY SUM(p.rows) DESC, t.name"
        
        cursor.execute(query)
        tables = cursor.fetchall()
        
        if not tables:
            return {
                "success": True,
                "dataset_processed": dataset_id,
                "database_type": "mssql",
                "tables_trained": [],
                "tables_skipped": [],
                "message": f"No tables found with row_count >= {min_row_count}",
                "filters_applied": {
                    "min_row_count": min_row_count,
                    "schema": schema_name,
                    "table_pattern": table_pattern
                }
            }
        
        # Step 2: Remove existing DDLs if requested
        removed_count = await _remove_existing_ddls(database_name, tenant_id, remove_existing, dry_run)
        
        # Step 3: Generate and train DDLs
        tables_trained = []
        tables_skipped = []
        errors = []
        
        for table in tables:
            db_name, schema, table_name, row_count, created_at, modified_at = table
            full_table_name = f"{schema}.{table_name}"
            
            try:
                # Generate DDL
                ddl = _generate_mssql_ddl(cursor, db_name, schema, table_name, include_row_counts, row_count)
                
                if dry_run:
                    logger.info(f"[DRY RUN] Would train DDL for {full_table_name} ({row_count:,} rows)")
                    
                    # Get column count for preview
                    cursor.execute(f"""
                        SELECT COUNT(*) 
                        FROM INFORMATION_SCHEMA.COLUMNS 
                        WHERE TABLE_SCHEMA = '{schema}' 
                        AND TABLE_NAME = '{table_name}'
                    """)
                    column_count = cursor.fetchone()[0]
                    
                    tables_trained.append({
                        "table": full_table_name,
                        "database": db_name,
                        "row_count": row_count,
                        "columns": column_count,
                        "ddl_preview": ddl[:200] + "..." if len(ddl) > 200 else ddl
                    })
                else:
                    # Train with the DDL
                    train_result = await vanna_train(
                        training_type="ddl",
                        content=ddl,
                        tenant_id=tenant_id,
                        metadata={
                            "source": "batch_train_ddl",
                            "database": database_name,
                            "schema": schema,
                            "row_count": row_count,
                            "generated_at": datetime.now().isoformat()
                        }
                    )
                    
                    if train_result.get("success"):
                        tables_trained.append({
                            "table": full_table_name,
                            "database": db_name,
                            "row_count": row_count,
                            "training_id": train_result.get("training_id")
                        })
                        logger.info(f"Trained DDL for {full_table_name} ({row_count:,} rows)")
                    else:
                        errors.append({
                            "table": full_table_name,
                            "error": train_result.get("error", "Unknown training error")
                        })
                
            except Exception as e:
                error_msg = f"Failed to process {full_table_name}: {str(e)}"
                logger.error(error_msg)
                errors.append({
                    "table": full_table_name,
                    "error": str(e)
                })
        
        # Step 4: Identify skipped tables
        tables_skipped = await _get_skipped_tables_mssql(cursor, database_name, schema_name, min_row_count, table_pattern)
        
        return _prepare_response(
            database_type="mssql",
            dataset_processed=dataset_id,
            tables_trained=tables_trained,
            tables_skipped=tables_skipped,
            removed_count=removed_count,
            errors=errors,
            dry_run=dry_run,
            min_row_count=min_row_count
        )
        
    finally:
        cursor.close()
        conn.close()

def _generate_bigquery_ddl(table: bigquery.Table, include_row_counts: bool, row_count: int) -> str:
    """Generate DDL statement from BigQuery table object"""
    
    # Start with CREATE TABLE
    ddl_parts = [f"CREATE TABLE `{table.project}.{table.dataset_id}.{table.table_id}` ("]
    
    # Add columns
    column_defs = []
    for field in table.schema:
        column_def = f"  {field.name} {field.field_type}"
        
        # Add mode constraints
        if field.mode == "REQUIRED":
            column_def += " NOT NULL"
        elif field.mode == "REPEATED":
            column_def += " ARRAY"
        
        # Add description as comment if available
        if field.description:
            column_def += f" -- {field.description}"
        
        column_defs.append(column_def)
    
    ddl_parts.append(",\n".join(column_defs))
    ddl_parts.append(")")
    
    # Add table options
    options = []
    
    if table.description:
        options.append(f"-- Table Description: {table.description}")
    
    if include_row_counts:
        options.append(f"-- Row Count: {row_count:,}")
    
    if table.time_partitioning:
        partition_field = table.time_partitioning.field
        partition_type = table.time_partitioning.type_
        options.append(f"PARTITION BY {partition_type}({partition_field})")
    
    if table.clustering_fields:
        cluster_fields = ", ".join(table.clustering_fields)
        options.append(f"CLUSTER BY {cluster_fields}")
    
    # Combine all parts
    ddl = "\n".join(ddl_parts)
    if options:
        ddl += "\n" + "\n".join(options)
    
    return ddl

def _generate_mssql_ddl(cursor, database_name: str, schema_name: str, table_name: str, 
                        include_row_counts: bool, row_count: int) -> str:
    """Generate DDL statement for MS SQL table"""
    
    # Start with CREATE TABLE
    ddl_parts = [f"CREATE TABLE [{schema_name}].[{table_name}] ("]
    
    # Get column information
    cursor.execute(f"""
        SELECT 
            c.COLUMN_NAME,
            c.DATA_TYPE,
            c.CHARACTER_MAXIMUM_LENGTH,
            c.NUMERIC_PRECISION,
            c.NUMERIC_SCALE,
            c.IS_NULLABLE,
            c.COLUMN_DEFAULT,
            cc.CONSTRAINT_NAME
        FROM INFORMATION_SCHEMA.COLUMNS c
        LEFT JOIN INFORMATION_SCHEMA.CONSTRAINT_COLUMN_USAGE cc
            ON c.TABLE_SCHEMA = cc.TABLE_SCHEMA 
            AND c.TABLE_NAME = cc.TABLE_NAME 
            AND c.COLUMN_NAME = cc.COLUMN_NAME
        WHERE c.TABLE_SCHEMA = '{schema_name}' 
        AND c.TABLE_NAME = '{table_name}'
        ORDER BY c.ORDINAL_POSITION
    """)
    
    columns = cursor.fetchall()
    column_defs = []
    
    for col in columns:
        col_name, data_type, char_length, num_precision, num_scale, is_nullable, default, constraint = col
        
        # Build column definition
        column_def = f"  [{col_name}] {data_type}"
        
        # Add size/precision
        if char_length:
            column_def += f"({char_length})"
        elif num_precision and num_scale:
            column_def += f"({num_precision},{num_scale})"
        elif num_precision:
            column_def += f"({num_precision})"
        
        # Add NULL/NOT NULL
        if is_nullable == "NO":
            column_def += " NOT NULL"
        
        # Add default if exists
        if default:
            column_def += f" DEFAULT {default}"
        
        # Add primary key indicator
        if constraint and "PK" in constraint:
            column_def += " -- PRIMARY KEY"
        
        column_defs.append(column_def)
    
    ddl_parts.append(",\n".join(column_defs))
    
    # Add primary key constraint
    cursor.execute(f"""
        SELECT kc.CONSTRAINT_NAME, STRING_AGG(kc.COLUMN_NAME, ', ') WITHIN GROUP (ORDER BY kc.ORDINAL_POSITION)
        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE kc
        JOIN INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc 
            ON kc.CONSTRAINT_NAME = tc.CONSTRAINT_NAME
        WHERE tc.TABLE_SCHEMA = '{schema_name}' 
        AND tc.TABLE_NAME = '{table_name}'
        AND tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
        GROUP BY kc.CONSTRAINT_NAME
    """)
    
    pk_info = cursor.fetchone()
    if pk_info:
        pk_name, pk_columns = pk_info
        ddl_parts.append(f",\n  CONSTRAINT [{pk_name}] PRIMARY KEY ({pk_columns})")
    
    ddl_parts.append(")")
    
    # Add table options/comments
    options = []
    
    if include_row_counts:
        options.append(f"-- Row Count: {row_count:,}")
    
    # Add indexes info
    cursor.execute(f"""
        SELECT DISTINCT i.name, i.type_desc
        FROM sys.indexes i
        JOIN sys.tables t ON i.object_id = t.object_id
        JOIN sys.schemas s ON t.schema_id = s.schema_id
        WHERE s.name = '{schema_name}' 
        AND t.name = '{table_name}'
        AND i.is_primary_key = 0 
        AND i.type > 0
    """)
    
    indexes = cursor.fetchall()
    if indexes:
        options.append("-- Indexes: " + ", ".join([f"{idx[0]} ({idx[1]})" for idx in indexes]))
    
    # Combine all parts
    ddl = "\n".join(ddl_parts)
    if options:
        ddl += "\n" + "\n".join(options)
    
    return ddl

async def _remove_existing_ddls(dataset_name: str, tenant_id: Optional[str], 
                               remove_existing: bool, dry_run: bool) -> int:
    """Remove existing DDLs for a dataset/database"""
    removed_count = 0
    
    if remove_existing and not dry_run:
        logger.info(f"Removing existing DDLs for dataset/database {dataset_name}")
        
        # Get existing DDL training data
        existing_ddls = await vanna_get_training_data(
            tenant_id=tenant_id,
            training_type="ddl",
            search_query=f"{dataset_name}.",
            limit=100
        )
        
        if existing_ddls.get("success") and existing_ddls.get("training_data"):
            # Remove each existing DDL
            training_ids = [item["id"] for item in existing_ddls["training_data"]]
            if training_ids:
                removal_result = await vanna_remove_training(
                    training_ids=training_ids,
                    tenant_id=tenant_id,
                    confirm_removal=True,
                    reason=f"Batch DDL refresh for dataset {dataset_name}"
                )
                if removal_result.get("success"):
                    removed_count = removal_result.get("removed_count", 0)
    
    return removed_count

async def _get_skipped_tables_bigquery(client, full_dataset_id: str, min_row_count: int, 
                                      table_pattern: Optional[str]) -> List[Dict]:
    """Get BigQuery tables that were skipped due to low row count"""
    tables_skipped = []
    
    # Query all tables to find which were skipped
    all_tables_query = f"""
    SELECT table_name, row_count
    FROM `{full_dataset_id}.INFORMATION_SCHEMA.TABLES`
    WHERE table_type = 'BASE TABLE'
      AND row_count < {min_row_count}
    """
    
    if table_pattern:
        sql_pattern = table_pattern.replace("*", "%")
        all_tables_query += f"\n  AND table_name LIKE '{sql_pattern}'"
    
    try:
        skipped_result = client.query(all_tables_query)
        dataset_name = full_dataset_id.split(".")[-1]
        for skipped in skipped_result:
            tables_skipped.append({
                "table": f"{dataset_name}.{skipped.table_name}",
                "row_count": skipped.row_count
            })
    except:
        # Non-critical error, just log it
        logger.warning("Could not query skipped tables")
    
    return tables_skipped

async def _get_skipped_tables_mssql(cursor, database_name: str, schema_name: Optional[str], 
                                   min_row_count: int, table_pattern: Optional[str]) -> List[Dict]:
    """Get MS SQL tables that were skipped due to low row count"""
    tables_skipped = []
    
    # Query tables with low row counts
    query = f"""
    SELECT 
        s.name as schema_name,
        t.name as table_name,
        SUM(p.rows) as row_count
    FROM [{database_name}].sys.tables t
    INNER JOIN [{database_name}].sys.schemas s ON t.schema_id = s.schema_id
    INNER JOIN [{database_name}].sys.partitions p ON t.object_id = p.object_id
    WHERE p.index_id IN (0,1)
    """
    
    if schema_name:
        query += f"\n  AND s.name = '{schema_name}'"
    
    query += f"\nGROUP BY s.name, t.name"
    query += f"\nHAVING SUM(p.rows) < {min_row_count}"
    
    if table_pattern:
        sql_pattern = table_pattern.replace("*", "%")
        query += f"\n  AND t.name LIKE '{sql_pattern}'"
    
    try:
        cursor.execute(query)
        for skipped in cursor.fetchall():
            schema, table, row_count = skipped
            tables_skipped.append({
                "table": f"{schema}.{table}",
                "row_count": row_count
            })
    except:
        # Non-critical error, just log it
        logger.warning("Could not query skipped tables")
    
    return tables_skipped

def _prepare_response(database_type: str, dataset_processed: str, tables_trained: List[Dict],
                     tables_skipped: List[Dict], removed_count: int, errors: List[Dict],
                     dry_run: bool, min_row_count: int) -> Dict[str, Any]:
    """Prepare standardized response"""
    result = {
        "success": len(errors) == 0,
        "database_type": database_type,
        "dataset_processed": dataset_processed,
        "tables_trained": tables_trained,
        "tables_skipped": tables_skipped,
        "removed_count": removed_count,
        "errors": errors,
        "dry_run": dry_run,
        "summary": {
            "total_tables_processed": len(tables_trained),
            "total_rows_represented": sum(t.get("row_count", 0) for t in tables_trained),
            "min_row_count_used": min_row_count
        }
    }
    
    if dry_run:
        result["message"] = "This was a dry run. Use dry_run=False to actually train."
    else:
        result["message"] = f"Successfully trained DDLs for {len(tables_trained)} tables"
    
    return result

# Tool definition for FastMCP
tool_definition = {
    "name": "vanna_batch_train_ddl",
    "description": "Auto-generate and train DDLs for tables with data (BigQuery and MS SQL)",
    "input_schema": {
        "type": "object",
        "properties": {
            "dataset_id": {
                "type": "string",
                "description": "Dataset/Database ID - BigQuery: 'dataset_name', MS SQL: 'database' or 'database.schema'"
            },
            "tenant_id": {
                "type": "string",
                "description": "Tenant ID for multi-tenant mode (optional)"
            },
            "min_row_count": {
                "type": "integer",
                "description": "Minimum row count threshold (default: 1)",
                "default": 1
            },
            "include_row_counts": {
                "type": "boolean",
                "description": "Include row count in DDL documentation (default: true)",
                "default": True
            },
            "table_pattern": {
                "type": "string",
                "description": "Filter tables by name pattern (e.g., 'sales_*')"
            },
            "dry_run": {
                "type": "boolean",
                "description": "Preview without making changes (default: false)",
                "default": False
            },
            "remove_existing": {
                "type": "boolean",
                "description": "Remove existing DDLs before adding new ones (default: true)",
                "default": True
            }
        },
        "required": ["dataset_id"]
    }
}