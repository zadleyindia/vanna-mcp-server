#!/usr/bin/env python3
"""
Vanna MCP Server - Main entry point
Provides natural language to SQL capabilities for BigQuery using Vanna AI
"""
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List, Union

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from fastmcp import FastMCP
from src.config.settings import settings
from src.tools.vanna_ask import vanna_ask
from src.tools.vanna_train import vanna_train
from src.tools.vanna_suggest_questions import vanna_suggest_questions
from src.tools.vanna_list_tenants import vanna_list_tenants
from src.tools.vanna_get_query_history import vanna_get_query_history
from src.tools.vanna_explain import vanna_explain
from src.tools.vanna_execute import vanna_execute
from src.tools.vanna_get_schemas import vanna_get_schemas
from src.tools.vanna_get_training_data import vanna_get_training_data
from src.tools.vanna_remove_training import vanna_remove_training
from src.tools.vanna_generate_followup import vanna_generate_followup
from src.tools.vanna_catalog_sync import vanna_catalog_sync
from src.tools.vanna_batch_train_ddl import vanna_batch_train_ddl

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr),
        logging.FileHandler(settings.LOG_FILE) if settings.LOG_FILE else logging.NullHandler()
    ]
)

logger = logging.getLogger(__name__)

# Create FastMCP server instance
mcp = FastMCP("Vanna MCP Server")

# Initialize configuration
# FastMCP passes config through environment variables when started by Claude
# The "config" field in settings.json becomes environment variables
from src.config.mcp_config import MCPConfigAdapter

# Log startup mode
if any(key in os.environ for key in ['OPENAI_API_KEY', 'SUPABASE_URL', 'BIGQUERY_PROJECT']):
    logger.info("Running under MCP with configuration from Claude")
    # Configuration is already in environment variables from MCP
else:
    logger.info("Running in development mode, using .env file")

# Register tools
@mcp.tool(name="vanna_ask", description="Convert natural language questions to SQL queries with multi-tenant support")
async def handle_vanna_ask(
    query: str,
    tenant_id: Optional[str] = None,
    include_shared: Optional[bool] = None,
    include_explanation: bool = True,
    include_confidence: bool = True,
    auto_train: bool = False
) -> Dict[str, Any]:
    """
    Convert natural language questions to SQL queries.
    
    Args:
        query: Natural language question about your data
        tenant_id: Override default tenant (for multi-tenant mode)
        include_shared: Override shared knowledge setting
        include_explanation: Include plain English explanation of the SQL
        include_confidence: Include confidence score for the generated SQL
        auto_train: Automatically train on successful queries
    """
    return await vanna_ask(
        query=query,
        tenant_id=tenant_id,
        include_shared=include_shared,
        include_explanation=include_explanation,
        include_confidence=include_confidence,
        auto_train=auto_train
    )

# Register vanna_train tool
@mcp.tool(name="vanna_train", description="Train Vanna with DDL, documentation, or SQL examples")
async def handle_vanna_train(
    training_type: str,
    content: str,
    question: Optional[str] = None,
    tenant_id: Optional[str] = None,
    is_shared: bool = False,
    metadata: Optional[Dict[str, Any]] = None,
    validate: bool = True
) -> Dict[str, Any]:
    """
    Train Vanna with new data.
    
    Args:
        training_type: Type of training data ('ddl', 'documentation', or 'sql')
        content: The training content (DDL statement, documentation, or SQL query)
        question: For SQL training, the natural language question
        tenant_id: Override default tenant (for multi-tenant mode)
        is_shared: Mark this as shared knowledge for all tenants
        metadata: Additional metadata to store
        validate: Whether to validate the training data
    """
    return await vanna_train(
        training_type=training_type,
        content=content,
        question=question,
        tenant_id=tenant_id,
        is_shared=is_shared,
        metadata=metadata,
        validate=validate
    )

# Register vanna_suggest_questions tool
@mcp.tool(name="vanna_suggest_questions", description="Get suggested questions based on available data")
async def handle_vanna_suggest_questions(
    context: Optional[str] = None,
    limit: int = 5,
    include_metadata: bool = True
) -> Dict[str, Any]:
    """
    Get suggested questions to ask about your data.
    
    Args:
        context: Optional context to tailor suggestions
        limit: Number of suggestions to return
        include_metadata: Include metadata about suggestions
    """
    return await vanna_suggest_questions(
        context=context,
        limit=limit,
        include_metadata=include_metadata
    )

# Register vanna_list_tenants tool
@mcp.tool(name="vanna_list_tenants", description="List allowed tenants and multi-tenant configuration")
async def handle_vanna_list_tenants() -> Dict[str, Any]:
    """
    List allowed tenants and current multi-tenant configuration.
    
    Returns:
        Configuration details including allowed tenants
    """
    return await vanna_list_tenants()

# Register vanna_get_query_history tool
@mcp.tool(name="vanna_get_query_history", description="View query history and analytics")
async def handle_vanna_get_query_history(
    tenant_id: Optional[str] = None,
    limit: int = 10,
    include_analytics: bool = True
) -> Dict[str, Any]:
    """
    Get query history and analytics.
    
    Args:
        tenant_id: Filter by specific tenant (optional)
        limit: Number of recent queries to return
        include_analytics: Include aggregate analytics
    """
    return await vanna_get_query_history(
        tenant_id=tenant_id,
        limit=limit,
        include_analytics=include_analytics
    )

# Register vanna_explain tool
@mcp.tool(name="vanna_explain", description="Explain SQL queries in plain English with performance insights")
async def handle_vanna_explain(
    sql: str,
    tenant_id: Optional[str] = None,
    include_performance_tips: bool = True,
    include_table_info: bool = True,
    detail_level: str = "medium"
) -> Dict[str, Any]:
    """
    Explain an SQL query in plain English.
    
    Args:
        sql: The SQL query to explain
        tenant_id: Tenant ID for multi-tenant mode (optional)
        include_performance_tips: Include performance optimization suggestions
        include_table_info: Include information about tables used
        detail_level: Level of explanation detail ('basic', 'medium', 'detailed')
    """
    return await vanna_explain(
        sql=sql,
        tenant_id=tenant_id,
        include_performance_tips=include_performance_tips,
        include_table_info=include_table_info,
        detail_level=detail_level
    )

# Register vanna_execute tool
@mcp.tool(name="vanna_execute", description="Execute SQL queries with result formatting and visualization options")
async def handle_vanna_execute(
    sql: str,
    tenant_id: Optional[str] = None,
    response_format: str = "full",
    limit: Optional[int] = None,
    include_metadata: bool = True,
    create_visualization: bool = False,
    chart_type: str = "auto",
    export_format: Optional[str] = None
) -> Dict[str, Any]:
    """
    Execute SQL queries and return formatted results.
    
    Args:
        sql: The SQL query to execute (SELECT only)
        tenant_id: Tenant ID for multi-tenant mode (optional)
        response_format: Format for response data ('full', 'data_only', 'summary')
        limit: Maximum number of rows to return
        include_metadata: Include execution metadata
        create_visualization: Generate chart visualization
        chart_type: Type of chart to create ('auto', 'bar', 'line', 'scatter', 'pie', 'table')
        export_format: Export data format ('csv', 'json', 'excel')
    """
    return await vanna_execute(
        sql=sql,
        tenant_id=tenant_id,
        response_format=response_format,
        limit=limit,
        include_metadata=include_metadata,
        create_visualization=create_visualization,
        chart_type=chart_type,
        export_format=export_format
    )

# Register vanna_get_schemas tool
@mcp.tool(name="vanna_get_schemas", description="Display database structure and schemas accessible to the tenant")
async def handle_vanna_get_schemas(
    tenant_id: Optional[str] = None,
    include_metadata: bool = True,
    include_sample_values: bool = False,
    table_filter: Optional[str] = None,
    format_output: str = "hierarchical"
) -> Dict[str, Any]:
    """
    Get database schemas and table structures.
    
    Args:
        tenant_id: Override default tenant (for multi-tenant mode)
        include_metadata: Include detailed metadata
        include_sample_values: Include sample values for columns
        table_filter: Filter tables by name pattern (supports * wildcard)
        format_output: Output format ('hierarchical', 'flat', 'detailed')
    """
    return await vanna_get_schemas(
        tenant_id=tenant_id,
        include_metadata=include_metadata,
        include_sample_values=include_sample_values,
        table_filter=table_filter,
        format_output=format_output
    )

# Register vanna_get_training_data tool
@mcp.tool(name="vanna_get_training_data", description="View and manage existing training data with filtering and search")
async def handle_vanna_get_training_data(
    tenant_id: Optional[str] = None,
    training_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    include_shared: Optional[bool] = None,
    search_query: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc"
) -> Dict[str, Any]:
    """
    Retrieve existing training data with filtering and search.
    
    Args:
        tenant_id: Override default tenant (for multi-tenant mode)
        training_type: Filter by type ('ddl', 'documentation', 'sql')
        limit: Maximum items to return (max: 100)
        offset: Items to skip for pagination
        include_shared: Include shared knowledge
        search_query: Search within content
        sort_by: Field to sort by
        sort_order: Sort direction ('asc' or 'desc')
    """
    return await vanna_get_training_data(
        tenant_id=tenant_id,
        training_type=training_type,
        limit=limit,
        offset=offset,
        include_shared=include_shared,
        search_query=search_query,
        sort_by=sort_by,
        sort_order=sort_order
    )

# Register vanna_remove_training tool
@mcp.tool(name="vanna_remove_training", description="Remove incorrect or outdated training data with safety checks")
async def handle_vanna_remove_training(
    training_ids: Union[str, List[str]],
    tenant_id: Optional[str] = None,
    confirm_removal: bool = True,
    reason: Optional[str] = None,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Remove incorrect or outdated training data.
    
    Args:
        training_ids: Single ID or list of training data IDs to remove
        tenant_id: Override default tenant (for multi-tenant mode)
        confirm_removal: Safety flag to confirm deletion
        reason: Reason for removal (for audit trail)
        dry_run: Preview removal without deleting
    """
    return await vanna_remove_training(
        training_ids=training_ids,
        tenant_id=tenant_id,
        confirm_removal=confirm_removal,
        reason=reason,
        dry_run=dry_run
    )

# Register vanna_generate_followup tool
@mcp.tool(name="vanna_generate_followup", description="Generate intelligent follow-up questions based on query context")
async def handle_vanna_generate_followup(
    original_question: str,
    sql_generated: str,
    tenant_id: Optional[str] = None,
    include_deeper_analysis: bool = True,
    include_related_tables: bool = True,
    max_suggestions: int = 5,
    focus_area: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate intelligent follow-up questions.
    
    Args:
        original_question: The original natural language question
        sql_generated: The SQL query that was generated
        tenant_id: Override default tenant (for multi-tenant mode)
        include_deeper_analysis: Include deeper analysis questions
        include_related_tables: Include related table questions
        max_suggestions: Maximum suggestions to return (1-10)
        focus_area: Focus area (temporal, comparison, aggregation, detail, related)
    """
    return await vanna_generate_followup(
        original_question=original_question,
        sql_generated=sql_generated,
        tenant_id=tenant_id,
        include_deeper_analysis=include_deeper_analysis,
        include_related_tables=include_related_tables,
        max_suggestions=max_suggestions,
        focus_area=focus_area
    )

@mcp.tool(name="vanna_catalog_sync", description="Synchronize Data Catalog with Vanna training data")
async def handle_vanna_catalog_sync(
    source: str = "bigquery",
    mode: str = "incremental", 
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
    """
    return await vanna_catalog_sync(
        source=source,
        mode=mode,
        dataset_filter=dataset_filter,
        json_path=json_path,
        dry_run=dry_run,
        chunk_size=chunk_size,
        include_views=include_views,
        include_column_stats=include_column_stats
    )

@mcp.tool(name="vanna_batch_train_ddl", description="Auto-generate and train DDLs for BigQuery tables with data")
async def handle_vanna_batch_train_ddl(
    dataset_id: str,
    tenant_id: Optional[str] = None,
    min_row_count: int = 1,
    include_row_counts: bool = True,
    table_pattern: Optional[str] = None,
    dry_run: bool = False,
    remove_existing: bool = True
) -> Dict[str, Any]:
    """
    Auto-generate and train DDLs for BigQuery tables with data
    
    Args:
        dataset_id: BigQuery dataset ID (e.g., 'sales_data' or 'project.sales_data')
        tenant_id: Tenant ID for multi-tenant mode (optional)
        min_row_count: Minimum row count threshold (default: 1)
        include_row_counts: Include row count in DDL documentation (default: true)
        table_pattern: Filter tables by name pattern (e.g., 'sales_*')
        dry_run: Preview without making changes (default: false)
        remove_existing: Remove existing DDLs before adding new ones (default: true)
    """
    return await vanna_batch_train_ddl(
        dataset_id=dataset_id,
        tenant_id=tenant_id,
        min_row_count=min_row_count,
        include_row_counts=include_row_counts,
        table_pattern=table_pattern,
        dry_run=dry_run,
        remove_existing=remove_existing
    )

async def initialize_server():
    """Initialize server and validate configuration"""
    logger.info("Initializing Vanna MCP Server...")
    
    # Validate configuration
    config_status = settings.validate_config()
    
    if not config_status['valid']:
        logger.error("Configuration errors found:")
        for error in config_status['errors']:
            logger.error(f"  - {error}")
        sys.exit(1)
    
    if config_status['warnings']:
        for warning in config_status['warnings']:
            logger.warning(f"Configuration warning: {warning}")
    
    logger.info(f"Configuration valid. Using schema: {settings.VANNA_SCHEMA}")
    
    # Initialize Vanna connection
    try:
        from src.config.vanna_config import get_vanna
        vn = get_vanna()
        logger.info("Vanna initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Vanna: {e}")
        sys.exit(1)
    
    logger.info("Vanna MCP Server ready!")
    # Don't call get_tools() here since it's async and we're in sync context

def main():
    """Main entry point"""
    try:
        # Initialize server synchronously
        asyncio.run(initialize_server())
        
        # Run the MCP server (it handles its own event loop)
        logger.info("Starting MCP server...")
        mcp.run()
        
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    # Import required for type hints
    from typing import Dict, Any, Optional, List, Union
    
    # Run the server
    main()