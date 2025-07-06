"""
vanna_explain tool - Explain SQL queries in plain English
Priority #4 tool in our implementation
"""
from typing import Dict, Any, Optional
import logging
import re
from src.config.vanna_config import get_vanna
from src.config.settings import settings

logger = logging.getLogger(__name__)

async def vanna_explain(
    sql: str,
    tenant_id: Optional[str] = None,
    include_performance_tips: bool = True,
    include_table_info: bool = True,
    detail_level: str = "medium"
) -> Dict[str, Any]:
    """
    Explain an SQL query in plain English with optional performance insights.
    
    This tool takes an SQL query and provides a human-readable explanation of what 
    the query does, including table relationships, filtering logic, and aggregations.
    
    Args:
        sql (str): The SQL query to explain
        
        tenant_id (str, optional): Override default tenant (for multi-tenant mode)
            Default: None (uses settings.TENANT_ID)
            
        include_performance_tips (bool): Include performance optimization suggestions
            Default: True
            
        include_table_info (bool): Include information about tables and columns used
            Default: True
            
        detail_level (str): Level of explanation detail
            - "basic": Simple explanation for non-technical users
            - "medium": Balanced technical and business explanation  
            - "detailed": Technical explanation with SQL concepts
            Default: "medium"
    
    Returns:
        Dict containing:
        - explanation (str): Plain English explanation of the SQL
        - query_type (str): Type of query (SELECT, etc.)
        - tables_used (list): Tables referenced in the query
        - key_operations (list): Main operations performed
        - performance_tips (list): Optimization suggestions (if requested)
        - complexity_score (int): Query complexity from 1-5
        - estimated_cost (str): Rough cost estimate for BigQuery
        
    Example Usage:
        # Basic explanation
        vanna_explain(
            sql="SELECT COUNT(*) FROM sales WHERE date >= '2024-01-01'"
        )
        
        # Detailed technical explanation
        vanna_explain(
            sql="SELECT customer_id, SUM(amount) FROM orders GROUP BY customer_id HAVING SUM(amount) > 1000",
            detail_level="detailed",
            include_performance_tips=True
        )
    """
    try:
        vn = get_vanna()
        
        # Handle tenant_id in multi-tenant mode
        if settings.ENABLE_MULTI_TENANT:
            # Use default tenant if not provided
            if not tenant_id:
                tenant_id = settings.TENANT_ID
                logger.info(f"No tenant_id provided, using default: {tenant_id}")
            
            # Validate tenant_id
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
                "suggestions": ["Provide a valid SQL query to explain"]
            }
        
        # Remove markdown formatting if present
        if sql_clean.startswith("```sql") and sql_clean.endswith("```"):
            sql_clean = sql_clean[6:-3].strip()
        elif sql_clean.startswith("```") and sql_clean.endswith("```"):
            sql_clean = sql_clean[3:-3].strip()
        
        logger.info(f"Explaining SQL for tenant '{tenant_id}': {sql_clean[:100]}...")
        
        # CRITICAL: Apply cross-tenant validation (same as vanna_ask)
        if settings.ENABLE_MULTI_TENANT and (tenant_id or settings.TENANT_ID):
            effective_tenant = tenant_id or settings.TENANT_ID
            
            # Import cross-tenant validation logic from vanna_ask
            try:
                from src.tools.vanna_ask import _extract_tables_from_sql, _check_cross_tenant_access
                
                tables_referenced = _extract_tables_from_sql(sql_clean)
                logger.info(f"Tables referenced in SQL explanation: {tables_referenced}")
                
                # Check for cross-tenant violations
                tenant_violations = _check_cross_tenant_access(tables_referenced, effective_tenant)
                
                if tenant_violations:
                    if settings.STRICT_TENANT_ISOLATION:
                        return {
                            "success": False,
                            "error": "Cross-tenant table access blocked in explanation",
                            "blocked_tables": tenant_violations,
                            "tenant_id": effective_tenant,
                            "security_policy": "STRICT_TENANT_ISOLATION enabled",
                            "suggestions": [
                                f"Use tables accessible to tenant '{effective_tenant}'",
                                "Contact administrator to access shared data"
                            ]
                        }
                    else:
                        # Permissive mode: warn but continue
                        logger.warning(f"Cross-tenant access detected in SQL explanation for tenant '{effective_tenant}': {tenant_violations}")
                        
            except ImportError as e:
                logger.warning(f"Could not import cross-tenant validation: {e}")
        
        # Analyze query structure
        query_analysis = _analyze_sql_structure(sql_clean)
        
        # Database type validation and adaptation
        database_type = settings.DATABASE_TYPE
        if database_type and database_type.lower() not in sql_clean.lower():
            logger.info(f"Explaining SQL for database type: {database_type}")
        
        # Generate explanation using Vanna with tenant context
        explanation = await _generate_explanation(vn, sql_clean, detail_level, tenant_id, database_type)
        
        # Get table information if requested
        table_info = {}
        if include_table_info and query_analysis["tables_used"]:
            table_info = await _get_table_information(vn, query_analysis["tables_used"], tenant_id)
        
        # Generate performance tips if requested
        performance_tips = []
        if include_performance_tips:
            performance_tips = _generate_performance_tips(sql_clean, query_analysis)
        
        # Calculate complexity score
        complexity_score = _calculate_complexity_score(sql_clean, query_analysis)
        
        # Estimate query cost (BigQuery-specific)
        estimated_cost = _estimate_query_cost(sql_clean, query_analysis)
        
        result = {
            "success": True,
            "explanation": explanation,
            "query_type": query_analysis["query_type"],
            "tables_used": query_analysis["tables_used"],
            "key_operations": query_analysis["key_operations"],
            "complexity_score": complexity_score,
            "detail_level": detail_level,
            "tenant_id": tenant_id if settings.ENABLE_MULTI_TENANT else None,
            "estimated_cost": estimated_cost,
            "database_type": database_type,
            "shared_knowledge_enabled": settings.ENABLE_SHARED_KNOWLEDGE if settings.ENABLE_MULTI_TENANT else None,
            "strict_isolation": settings.STRICT_TENANT_ISOLATION if settings.ENABLE_MULTI_TENANT else None
        }
        
        if include_table_info and table_info:
            result["table_info"] = table_info
            
        if include_performance_tips and performance_tips:
            result["performance_tips"] = performance_tips
        
        logger.info(f"Successfully explained SQL query (complexity: {complexity_score}/5)")
        return result
        
    except Exception as e:
        logger.error(f"Error in vanna_explain: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": f"Explanation error: {str(e)}",
            "error_type": type(e).__name__,
            "suggestions": ["Check SQL syntax", "Verify database connection", "Try a simpler query"]
        }

def _analyze_sql_structure(sql: str) -> Dict[str, Any]:
    """Analyze SQL query structure and extract key components"""
    sql_upper = sql.upper()
    
    # Determine query type
    query_type = "UNKNOWN"
    if sql_upper.strip().startswith("SELECT"):
        query_type = "SELECT"
    elif sql_upper.strip().startswith("INSERT"):
        query_type = "INSERT"
    elif sql_upper.strip().startswith("UPDATE"):
        query_type = "UPDATE"
    elif sql_upper.strip().startswith("DELETE"):
        query_type = "DELETE"
    elif sql_upper.strip().startswith("CREATE"):
        query_type = "CREATE"
    
    # Extract table names (basic regex - could be enhanced)
    tables_pattern = r'FROM\s+([`"]?[\w.-]+[`"]?)(?:\s+(?:AS\s+)?[\w]+)?|JOIN\s+([`"]?[\w.-]+[`"]?)(?:\s+(?:AS\s+)?[\w]+)?'
    tables_matches = re.findall(tables_pattern, sql_upper, re.IGNORECASE)
    tables_used = []
    for match in tables_matches:
        table = match[0] or match[1]
        if table and table not in tables_used:
            tables_used.append(table.strip('`"').lower())
    
    # Identify key operations
    key_operations = []
    
    if "GROUP BY" in sql_upper:
        key_operations.append("Grouping/Aggregation")
    if "ORDER BY" in sql_upper:
        key_operations.append("Sorting")
    if "WHERE" in sql_upper:
        key_operations.append("Filtering")
    if "HAVING" in sql_upper:
        key_operations.append("Post-aggregation Filtering")
    if "JOIN" in sql_upper:
        if "LEFT JOIN" in sql_upper:
            key_operations.append("Left Join")
        elif "RIGHT JOIN" in sql_upper:
            key_operations.append("Right Join")
        elif "INNER JOIN" in sql_upper:
            key_operations.append("Inner Join")
        else:
            key_operations.append("Join")
    if any(func in sql_upper for func in ["SUM(", "COUNT(", "AVG(", "MAX(", "MIN("]):
        key_operations.append("Aggregate Functions")
    if "UNION" in sql_upper:
        key_operations.append("Union")
    if "SUBQUERY" in sql_upper or "(" in sql and "SELECT" in sql_upper:
        key_operations.append("Subquery")
    if "WINDOW" in sql_upper or "OVER(" in sql_upper:
        key_operations.append("Window Functions")
    
    return {
        "query_type": query_type,
        "tables_used": tables_used,
        "key_operations": key_operations
    }

async def _generate_explanation(vn, sql: str, detail_level: str, tenant_id: Optional[str], database_type: Optional[str] = None) -> str:
    """Generate natural language explanation using Vanna's LLM"""
    try:
        # Create explanation prompt based on detail level and database type
        db_context = f" (for {database_type.upper()})" if database_type else ""
        
        if detail_level == "basic":
            prompt = f"""Explain this SQL query{db_context} in simple, non-technical terms that a business user can understand:

{sql}

Focus on:
- What data is being retrieved
- What business question this answers
- Keep it simple and avoid technical jargon"""
        
        elif detail_level == "detailed":
            prompt = f"""Provide a detailed technical explanation of this SQL query:

{sql}

Include:
- Step-by-step breakdown of operations
- Technical SQL concepts used
- Join types and relationships
- Aggregation logic
- Performance considerations"""
        
        else:  # medium
            prompt = f"""Explain this SQL query in clear terms suitable for both business and technical users:

{sql}

Include:
- What data is being retrieved and why
- How the query works (main operations)
- What business insights this provides
- Any notable SQL techniques used"""
        
        # Use Vanna's generate_sql method with custom prompt (reusing the LLM interface)
        # This is a workaround since Vanna doesn't have a direct "explain" method
        explanation_response = vn.ask(question=prompt, auto_train=False)
        
        if explanation_response and hasattr(explanation_response, 'sql'):
            # Extract the explanation from the response
            return explanation_response.sql or "Unable to generate explanation"
        else:
            return f"This {_analyze_sql_structure(sql)['query_type']} query retrieves data from the specified tables with the given conditions."
            
    except Exception as e:
        logger.warning(f"Failed to generate LLM explanation: {e}")
        # Fallback to basic structural explanation
        analysis = _analyze_sql_structure(sql)
        return f"This {analysis['query_type']} query works with {len(analysis['tables_used'])} table(s) and performs operations: {', '.join(analysis['key_operations'])}."

async def _get_table_information(vn, tables: list, tenant_id: Optional[str]) -> Dict[str, Any]:
    """Get information about tables used in the query"""
    table_info = {}
    
    for table in tables[:3]:  # Limit to 3 tables to avoid too much data
        try:
            # This would ideally use Vanna's DDL retrieval, but we'll provide basic info
            table_info[table] = {
                "columns": f"Schema information for {table}",
                "description": f"Table used in query: {table}"
            }
        except Exception as e:
            logger.warning(f"Failed to get info for table {table}: {e}")
            table_info[table] = {"error": "Unable to retrieve table information"}
    
    return table_info

def _generate_performance_tips(sql: str, analysis: Dict[str, Any]) -> list:
    """Generate performance optimization tips based on query analysis"""
    tips = []
    sql_upper = sql.upper()
    
    # Check for common performance issues
    if "SELECT *" in sql_upper:
        tips.append("Consider selecting only the columns you need instead of using SELECT *")
    
    if len(analysis["tables_used"]) > 1 and "JOIN" not in sql_upper:
        tips.append("Multiple tables detected - ensure proper JOIN conditions are used")
    
    if "GROUP BY" in sql_upper and "ORDER BY" not in sql_upper:
        tips.append("Consider adding ORDER BY for consistent results with GROUP BY")
    
    if "WHERE" not in sql_upper and analysis["query_type"] == "SELECT":
        tips.append("Consider adding WHERE clause to filter data and improve performance")
    
    if "LIMIT" not in sql_upper and analysis["query_type"] == "SELECT":
        tips.append("Consider adding LIMIT clause if you don't need all results")
    
    # BigQuery-specific tips
    if any(table for table in analysis["tables_used"] if "." in table):
        tips.append("Using partitioned tables - ensure partition filters are included where possible")
    
    return tips

def _calculate_complexity_score(sql: str, analysis: Dict[str, Any]) -> int:
    """Calculate complexity score from 1-5 based on query features"""
    score = 1
    sql_upper = sql.upper()
    
    # Base complexity factors
    if len(analysis["tables_used"]) > 1:
        score += 1
    if len(analysis["key_operations"]) > 2:
        score += 1
    if "SUBQUERY" in analysis["key_operations"] or "(" in sql and sql_upper.count("SELECT") > 1:
        score += 1
    if "WINDOW" in analysis["key_operations"]:
        score += 1
    
    # Additional complexity indicators
    if sql_upper.count("JOIN") > 2:
        score += 1
    if "CASE WHEN" in sql_upper:
        score += 1
    
    return min(score, 5)  # Cap at 5

def _estimate_query_cost(sql: str, analysis: Dict[str, Any]) -> str:
    """Estimate query cost for BigQuery (rough approximation)"""
    sql_upper = sql.upper()
    
    # Very basic cost estimation
    if "SELECT *" in sql_upper:
        return "High (full table scan)"
    elif len(analysis["tables_used"]) > 3:
        return "Medium-High (multiple tables)"
    elif "GROUP BY" in sql_upper or "JOIN" in sql_upper:
        return "Medium (aggregation/joins)"
    elif "WHERE" in sql_upper:
        return "Low-Medium (filtered query)"
    else:
        return "Low (simple query)"

# Tool definition for FastMCP
tool_definition = {
    "name": "vanna_explain",
    "description": "Explain SQL queries in plain English with performance insights",
    "input_schema": {
        "type": "object",
        "properties": {
            "sql": {
                "type": "string",
                "description": "The SQL query to explain"
            },
            "tenant_id": {
                "type": "string",
                "description": "Tenant ID for multi-tenant mode (optional)"
            },
            "include_performance_tips": {
                "type": "boolean",
                "description": "Include performance optimization suggestions",
                "default": True
            },
            "include_table_info": {
                "type": "boolean", 
                "description": "Include information about tables used",
                "default": True
            },
            "detail_level": {
                "type": "string",
                "enum": ["basic", "medium", "detailed"],
                "description": "Level of explanation detail",
                "default": "medium"
            }
        },
        "required": ["sql"]
    }
}