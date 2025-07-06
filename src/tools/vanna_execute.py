"""
vanna_execute tool - Execute SQL queries with result formatting and visualization
Priority #5 tool in our implementation
"""
from typing import Dict, Any, Optional, List
import logging
import json
import base64
import io
import asyncio
from datetime import datetime, date
from decimal import Decimal
from google.cloud import bigquery
from src.config.vanna_config import get_vanna
from src.config.settings import settings

# Optional visualization imports
try:
    import plotly.graph_objects as go
    import plotly.express as px
    import pandas as pd
    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("Plotly/Pandas not available - visualization features disabled")

logger = logging.getLogger(__name__)

async def vanna_execute(
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
    Execute SQL queries and return formatted results with optional visualization.
    
    This tool executes SQL queries against the configured database and provides
    flexible result formatting including data export and chart generation.
    
    Args:
        sql (str): The SQL query to execute
        
        tenant_id (str, optional): Override default tenant (for multi-tenant mode)
            Default: None (uses settings.TENANT_ID)
            
        response_format (str): Format for response data
            - "full": Complete response with metadata and data
            - "data_only": Just the query results
            - "summary": Summary statistics only
            Default: "full"
            
        limit (int, optional): Maximum number of rows to return
            Default: None (no limit, but will warn for large results)
            
        include_metadata (bool): Include execution metadata (timing, row count, etc.)
            Default: True
            
        create_visualization (bool): Generate chart visualization of results
            Default: False (requires plotly)
            
        chart_type (str): Type of chart to create
            - "auto": Automatically detect best chart type
            - "bar": Bar chart
            - "line": Line chart  
            - "scatter": Scatter plot
            - "pie": Pie chart
            - "table": Data table
            Default: "auto"
            
        export_format (str, optional): Export data format
            - "csv": CSV format
            - "json": JSON format
            - "excel": Excel format (requires openpyxl)
            Default: None (no export)
    
    Returns:
        Dict containing:
        - success (bool): Whether execution was successful
        - data (list): Query results (if any)
        - row_count (int): Number of rows returned
        - execution_time_ms (float): Query execution time
        - columns (list): Column names and types
        - visualization (dict): Chart data (if requested)
        - export_data (str): Exported data (if requested)
        - summary (dict): Data summary statistics
        
    Example Usage:
        # Simple execution
        vanna_execute(
            sql="SELECT COUNT(*) as order_count FROM orders"
        )
        
        # With visualization
        vanna_execute(
            sql="SELECT category, SUM(amount) as total FROM sales GROUP BY category",
            create_visualization=True,
            chart_type="bar"
        )
        
        # Data export
        vanna_execute(
            sql="SELECT * FROM customers LIMIT 100",
            export_format="csv",
            response_format="data_only"
        )
    """
    try:
        vn = get_vanna()
        
        # Handle tenant_id in multi-tenant mode
        if settings.ENABLE_MULTI_TENANT:
            if not tenant_id:
                tenant_id = settings.TENANT_ID
                logger.info(f"No tenant_id provided, using default: {tenant_id}")
            
            if not tenant_id:
                return {
                    "success": False,
                    "error": "tenant_id is required when multi-tenant is enabled",
                    "allowed_tenants": settings.get_allowed_tenants()
                }
            
            if not settings.is_tenant_allowed(tenant_id):
                allowed = settings.get_allowed_tenants()
                return {
                    "success": False,
                    "error": f"Tenant '{tenant_id}' is not allowed",
                    "allowed_tenants": allowed if allowed else "All tenants allowed (no restrictions)"
                }
        
        # Validate and clean SQL
        sql_clean = sql.strip()
        if not sql_clean:
            return {
                "success": False,
                "error": "SQL query cannot be empty",
                "suggestions": ["Provide a valid SQL query to execute"]
            }
        
        # Remove markdown formatting if present
        if sql_clean.startswith("```sql") and sql_clean.endswith("```"):
            sql_clean = sql_clean[6:-3].strip()
        elif sql_clean.startswith("```") and sql_clean.endswith("```"):
            sql_clean = sql_clean[3:-3].strip()
        
        # Validate SQL safety (SELECT only)
        if not _is_safe_sql(sql_clean):
            return {
                "success": False,
                "error": "Only SELECT queries are allowed for execution",
                "suggestions": ["Ensure your query starts with SELECT", "Remove any data modification commands"]
            }
        
        # Apply limit if specified
        if limit:
            sql_clean = _apply_limit(sql_clean, limit)
        
        logger.info(f"Executing SQL for tenant '{tenant_id}': {sql_clean[:100]}...")
        
        # Execute query
        start_time = datetime.now()
        execution_result = await _execute_query(sql_clean)
        execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        if not execution_result["success"]:
            return {
                "success": False,
                "error": execution_result["error"],
                "execution_time_ms": execution_time_ms,
                "suggestions": ["Check SQL syntax", "Verify table and column names", "Check data types"]
            }
        
        data = execution_result["data"]
        columns = execution_result["columns"]
        row_count = len(data)
        
        logger.info(f"Query executed successfully: {row_count} rows in {execution_time_ms:.2f}ms")
        
        # Build response based on format
        result = {
            "success": True,
            "row_count": row_count,
            "sql_executed": sql_clean
        }
        
        # Add execution metadata if requested
        if include_metadata:
            result.update({
                "execution_time_ms": execution_time_ms,
                "columns": columns,
                "tenant_id": tenant_id if settings.ENABLE_MULTI_TENANT else None,
                "database": settings.DATABASE_TYPE,
                "timestamp": datetime.now().isoformat()
            })
        
        # Handle different response formats
        if response_format == "data_only":
            result["data"] = data
        elif response_format == "summary":
            result["summary"] = _generate_data_summary(data, columns)
        else:  # full
            result["data"] = data
            result["summary"] = _generate_data_summary(data, columns)
        
        # Generate visualization if requested
        if create_visualization and VISUALIZATION_AVAILABLE and data:
            try:
                chart_result = await _create_visualization(data, columns, chart_type)
                result["visualization"] = chart_result
            except Exception as e:
                logger.warning(f"Failed to create visualization: {e}")
                result["visualization_error"] = str(e)
        elif create_visualization and not VISUALIZATION_AVAILABLE:
            result["visualization_error"] = "Visualization not available - install plotly and pandas"
        
        # Handle data export if requested
        if export_format and data:
            try:
                from src.utils.export_utils import export_to_json, export_to_csv, export_to_excel, create_download_instructions
                
                if export_format == "json":
                    export_result = export_to_json(data, "query_results")
                elif export_format == "csv":
                    export_result = export_to_csv(data, "query_results")
                elif export_format == "excel":
                    export_result = export_to_excel(data, "query_results")
                else:
                    export_result = {"success": False, "error": f"Unsupported format: {export_format}"}
                
                result["export"] = export_result
                if export_result.get("success"):
                    result["download_instructions"] = create_download_instructions(export_result)
                    
            except Exception as e:
                logger.warning(f"Failed to export data: {e}")
                result["export_error"] = str(e)
        
        # Store query history (successful execution)
        try:
            from src.tools.vanna_ask import _store_query_history_simple
            await _store_query_history_simple(
                query=f"EXECUTED: {sql_clean[:100]}...",
                sql=sql_clean,
                execution_time_ms=execution_time_ms,
                confidence=1.0,  # Manual execution = high confidence
                effective_tenant=tenant_id or "default"
            )
        except Exception as e:
            logger.warning(f"Failed to store execution history: {e}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in vanna_execute: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": f"Execution error: {str(e)}",
            "error_type": type(e).__name__,
            "suggestions": ["Check SQL syntax", "Verify database connection", "Check permissions"]
        }

def _is_safe_sql(sql: str) -> bool:
    """Validate that SQL is safe for execution (SELECT only)"""
    sql_upper = sql.strip().upper()
    
    # Must start with SELECT
    if not sql_upper.startswith("SELECT"):
        return False
    
    # Check for dangerous keywords
    dangerous_keywords = [
        'DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'TRUNCATE',
        'CREATE', 'GRANT', 'REVOKE', 'MERGE', 'REPLACE', 'CALL',
        'EXECUTE', 'EXEC'
    ]
    
    for keyword in dangerous_keywords:
        if keyword in sql_upper:
            return False
    
    return True

def _apply_limit(sql: str, limit: int) -> str:
    """Apply LIMIT clause to SQL if not already present"""
    sql_upper = sql.upper()
    
    if "LIMIT" not in sql_upper:
        return f"{sql.rstrip(';')} LIMIT {limit}"
    
    return sql

async def _execute_query(sql: str) -> Dict[str, Any]:
    """Execute SQL query using BigQuery client"""
    try:
        # Use BigQuery client for execution
        client = bigquery.Client(project=settings.BIGQUERY_PROJECT)
        
        # Configure job
        job_config = bigquery.QueryJobConfig()
        job_config.use_query_cache = True
        job_config.use_legacy_sql = False
        
        # Execute query
        query_job = client.query(sql, job_config=job_config)
        results = query_job.result()
        
        # Convert results to list of dictionaries
        data = []
        columns = []
        
        if results.total_rows > 0:
            # Get column information
            columns = [
                {
                    "name": field.name,
                    "type": field.field_type,
                    "mode": field.mode
                }
                for field in results.schema
            ]
            
            # Convert rows to serializable format
            for row in results:
                row_dict = {}
                for i, value in enumerate(row):
                    column_name = columns[i]["name"]
                    row_dict[column_name] = _serialize_value(value)
                data.append(row_dict)
        
        return {
            "success": True,
            "data": data,
            "columns": columns,
            "total_rows": results.total_rows,
            "bytes_processed": query_job.total_bytes_processed
        }
        
    except Exception as e:
        logger.error(f"Query execution failed: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "data": [],
            "columns": []
        }

def _serialize_value(value) -> Any:
    """Convert BigQuery values to JSON-serializable format"""
    if value is None:
        return None
    elif isinstance(value, (datetime, date)):
        return value.isoformat()
    elif isinstance(value, Decimal):
        return float(value)
    elif isinstance(value, bytes):
        return base64.b64encode(value).decode('utf-8')
    else:
        return value

def _generate_data_summary(data: List[Dict], columns: List[Dict]) -> Dict[str, Any]:
    """Generate summary statistics for the data"""
    if not data:
        return {"message": "No data to summarize"}
    
    summary = {
        "row_count": len(data),
        "column_count": len(columns),
        "columns": [col["name"] for col in columns]
    }
    
    # Basic statistics for numeric columns
    numeric_stats = {}
    for col in columns:
        col_name = col["name"]
        if col["type"] in ["INTEGER", "FLOAT", "NUMERIC"]:
            values = [row.get(col_name) for row in data if row.get(col_name) is not None]
            if values:
                numeric_stats[col_name] = {
                    "count": len(values),
                    "min": min(values),
                    "max": max(values),
                    "avg": sum(values) / len(values)
                }
    
    if numeric_stats:
        summary["numeric_stats"] = numeric_stats
    
    return summary

async def _create_visualization(data: List[Dict], columns: List[Dict], chart_type: str) -> Dict[str, Any]:
    """Create chart visualization using Plotly"""
    if not VISUALIZATION_AVAILABLE:
        raise Exception("Visualization libraries not available")
    
    df = pd.DataFrame(data)
    
    # Auto-detect chart type if requested
    if chart_type == "auto":
        chart_type = _detect_chart_type(df, columns)
    
    fig = None
    
    try:
        if chart_type == "bar":
            # Bar chart for categorical data
            if len(df.columns) >= 2:
                x_col = df.columns[0]
                y_col = df.columns[1]
                fig = px.bar(df, x=x_col, y=y_col, title=f"{y_col} by {x_col}")
            
        elif chart_type == "line":
            # Line chart for time series or numeric progression
            if len(df.columns) >= 2:
                x_col = df.columns[0]
                y_col = df.columns[1]
                fig = px.line(df, x=x_col, y=y_col, title=f"{y_col} over {x_col}")
            
        elif chart_type == "scatter":
            # Scatter plot for correlation
            if len(df.columns) >= 2:
                x_col = df.columns[0]
                y_col = df.columns[1]
                fig = px.scatter(df, x=x_col, y=y_col, title=f"{y_col} vs {x_col}")
            
        elif chart_type == "pie":
            # Pie chart for proportions
            if len(df.columns) >= 2:
                names_col = df.columns[0]
                values_col = df.columns[1]
                fig = px.pie(df, names=names_col, values=values_col, title=f"Distribution of {values_col}")
        
        elif chart_type == "table":
            # Data table
            fig = go.Figure(data=[go.Table(
                header=dict(values=list(df.columns)),
                cells=dict(values=[df[col] for col in df.columns])
            )])
            fig.update_layout(title="Data Table")
        
        if fig:
            # Convert to JSON for transmission
            chart_json = fig.to_json()
            return {
                "chart_type": chart_type,
                "chart_data": json.loads(chart_json),
                "chart_html": fig.to_html(include_plotlyjs='cdn'),
                "success": True
            }
        else:
            return {
                "success": False,
                "error": f"Could not create {chart_type} chart with available data"
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Chart creation failed: {str(e)}"
        }

def _detect_chart_type(df: pd.DataFrame, columns: List[Dict]) -> str:
    """Auto-detect appropriate chart type based on data"""
    if len(df.columns) < 2:
        return "table"
    
    # Check column types
    first_col_type = columns[0]["type"] if columns else "STRING"
    second_col_type = columns[1]["type"] if len(columns) > 1 else "STRING"
    
    # If second column is numeric
    if second_col_type in ["INTEGER", "FLOAT", "NUMERIC"]:
        # If first column looks like categories
        if first_col_type == "STRING" or df[df.columns[0]].nunique() < 20:
            return "bar"
        # If first column is date/time
        elif "DATE" in first_col_type or "TIME" in first_col_type:
            return "line"
        else:
            return "scatter"
    
    # Default to table for complex data
    return "table"


# Tool definition for FastMCP
tool_definition = {
    "name": "vanna_execute",
    "description": "Execute SQL queries with result formatting and visualization options",
    "input_schema": {
        "type": "object",
        "properties": {
            "sql": {
                "type": "string",
                "description": "The SQL query to execute (SELECT only)"
            },
            "tenant_id": {
                "type": "string",
                "description": "Tenant ID for multi-tenant mode (optional)"
            },
            "response_format": {
                "type": "string",
                "enum": ["full", "data_only", "summary"],
                "description": "Format for response data",
                "default": "full"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of rows to return",
                "minimum": 1,
                "maximum": 10000
            },
            "include_metadata": {
                "type": "boolean",
                "description": "Include execution metadata",
                "default": True
            },
            "create_visualization": {
                "type": "boolean",
                "description": "Generate chart visualization",
                "default": False
            },
            "chart_type": {
                "type": "string",
                "enum": ["auto", "bar", "line", "scatter", "pie", "table"],
                "description": "Type of chart to create",
                "default": "auto"
            },
            "export_format": {
                "type": "string",
                "enum": ["csv", "json", "excel"],
                "description": "Export data format"
            }
        },
        "required": ["sql"]
    }
}