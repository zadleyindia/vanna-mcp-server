"""
vanna_generate_followup tool - Generate intelligent follow-up questions
Priority #9 tool in our implementation
"""
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime
from src.config.vanna_config import get_vanna
from src.config.settings import settings
import re

logger = logging.getLogger(__name__)

async def vanna_generate_followup(
    original_question: str,
    sql_generated: str,
    tenant_id: Optional[str] = None,
    include_deeper_analysis: bool = True,
    include_related_tables: bool = True,
    max_suggestions: int = 5,
    focus_area: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate intelligent follow-up questions based on the original query and generated SQL.
    
    This tool analyzes the context of a previous question and its SQL to suggest
    meaningful follow-up questions that help users explore their data more deeply.
    
    Args:
        original_question (str): The original natural language question asked
            Example: "What are the top selling products?"
            
        sql_generated (str): The SQL query that was generated for the original question
            This helps understand what data was accessed and how
            
        tenant_id (str, optional): Override default tenant (for multi-tenant mode)
            Default: None (uses settings.TENANT_ID)
            
        include_deeper_analysis (bool): Include questions for deeper analysis
            Default: True
            Examples: trends over time, comparisons, breakdowns
            
        include_related_tables (bool): Include questions about related tables
            Default: True
            Suggests exploring joins with other tables
            
        max_suggestions (int): Maximum number of follow-up questions to generate
            Default: 5 (range: 1-10)
            
        focus_area (str, optional): Focus follow-ups on specific area
            Options: "temporal", "comparison", "aggregation", "detail", "related"
            Default: None (balanced mix)
    
    Returns:
        Dict containing:
        - followup_questions (list): List of suggested follow-up questions
        - question_categories (dict): Questions grouped by category
        - context_used (dict): Information about what was analyzed
        - tenant_id (str): Tenant context (if multi-tenant)
        - metadata (dict): Additional execution metadata
        
    Example Usage:
        # Generate follow-ups after a sales query
        vanna_generate_followup(
            original_question="What are the top selling products?",
            sql_generated="SELECT product_name, SUM(quantity) as total_sold FROM sales GROUP BY product_name ORDER BY total_sold DESC LIMIT 10"
        )
        
        # Focus on temporal analysis
        vanna_generate_followup(
            original_question="Show me revenue by region",
            sql_generated="SELECT region, SUM(revenue) FROM sales GROUP BY region",
            focus_area="temporal",
            max_suggestions=3
        )
    """
    try:
        vn = get_vanna()
        
        # 1. TENANT VALIDATION (MANDATORY)
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
                    "allowed_tenants": allowed if allowed else "All tenants allowed"
                }
        
        # 2. INPUT VALIDATION
        if not original_question or not original_question.strip():
            return {
                "success": False,
                "error": "Original question cannot be empty",
                "suggestions": ["Provide the original natural language question"]
            }
        
        if not sql_generated or not sql_generated.strip():
            return {
                "success": False,
                "error": "SQL query cannot be empty",
                "suggestions": ["Provide the generated SQL query"]
            }
        
        # Validate max_suggestions
        if max_suggestions < 1:
            max_suggestions = 1
        elif max_suggestions > 10:
            max_suggestions = 10
            
        # Validate focus_area
        valid_focus_areas = ["temporal", "comparison", "aggregation", "detail", "related", None]
        if focus_area and focus_area not in valid_focus_areas:
            focus_area = None
            logger.warning("Invalid focus_area provided, using balanced mix")
        
        # Clean SQL
        sql_clean = sql_generated.strip()
        if sql_clean.startswith("```sql") and sql_clean.endswith("```"):
            sql_clean = sql_clean[6:-3].strip()
        elif sql_clean.startswith("```") and sql_clean.endswith("```"):
            sql_clean = sql_clean[3:-3].strip()
        
        # 3. CROSS-TENANT VALIDATION (same as other tools)
        if settings.ENABLE_MULTI_TENANT and tenant_id:
            # Import cross-tenant validation
            try:
                from src.tools.vanna_ask import _extract_tables_from_sql, _check_cross_tenant_access
                
                tables_referenced = _extract_tables_from_sql(sql_clean)
                logger.info(f"Tables referenced in follow-up generation: {tables_referenced}")
                
                # Check for cross-tenant violations
                tenant_violations = _check_cross_tenant_access(tables_referenced, tenant_id)
                
                if tenant_violations and settings.STRICT_TENANT_ISOLATION:
                    return {
                        "success": False,
                        "error": "Cross-tenant table access blocked in follow-up generation",
                        "blocked_tables": tenant_violations,
                        "tenant_id": tenant_id,
                        "security_policy": "STRICT_TENANT_ISOLATION enabled",
                        "suggestions": [
                            f"Use tables accessible to tenant '{tenant_id}'",
                            "Contact administrator to access shared data"
                        ]
                    }
                    
            except ImportError as e:
                logger.warning(f"Could not import cross-tenant validation: {e}")
        
        # 4. DATABASE TYPE AWARENESS
        database_type = settings.DATABASE_TYPE
        logger.info(f"Generating follow-ups for database type: {database_type}, tenant: {tenant_id}")
        
        # 5. ANALYZE QUERY CONTEXT
        query_context = _analyze_query_context(original_question, sql_clean)
        
        # 6. GENERATE FOLLOW-UP QUESTIONS
        followup_questions = []
        question_categories = {
            "temporal": [],
            "comparison": [],
            "aggregation": [],
            "detail": [],
            "related": []
        }
        
        # Generate temporal questions
        if (not focus_area or focus_area == "temporal") and include_deeper_analysis:
            temporal_questions = _generate_temporal_questions(query_context, tenant_id)
            question_categories["temporal"] = temporal_questions
            followup_questions.extend(temporal_questions)
        
        # Generate comparison questions
        if (not focus_area or focus_area == "comparison") and include_deeper_analysis:
            comparison_questions = _generate_comparison_questions(query_context, tenant_id)
            question_categories["comparison"] = comparison_questions
            followup_questions.extend(comparison_questions)
        
        # Generate aggregation questions
        if not focus_area or focus_area == "aggregation":
            aggregation_questions = _generate_aggregation_questions(query_context, tenant_id)
            question_categories["aggregation"] = aggregation_questions
            followup_questions.extend(aggregation_questions)
        
        # Generate detail questions
        if not focus_area or focus_area == "detail":
            detail_questions = _generate_detail_questions(query_context, tenant_id)
            question_categories["detail"] = detail_questions
            followup_questions.extend(detail_questions)
        
        # Generate related table questions
        if (not focus_area or focus_area == "related") and include_related_tables:
            related_questions = await _generate_related_questions(vn, query_context, tenant_id)
            question_categories["related"] = related_questions
            followup_questions.extend(related_questions)
        
        # Limit and prioritize questions
        if len(followup_questions) > max_suggestions:
            # Prioritize based on relevance and diversity
            followup_questions = _prioritize_questions(followup_questions, max_suggestions, question_categories)
        
        # 7. PREPARE RESPONSE
        result = {
            "success": True,
            "followup_questions": followup_questions,
            "question_categories": {k: v for k, v in question_categories.items() if v},
            "total_generated": sum(len(v) for v in question_categories.values()),
            "context_used": {
                "original_question": original_question,
                "tables_identified": query_context["tables"],
                "operations_found": query_context["operations"],
                "has_aggregation": query_context["has_aggregation"],
                "has_filtering": query_context["has_filtering"],
                "focus_area": focus_area or "balanced"
            }
        }
        
        # 8. METADATA (MANDATORY)
        result.update({
            "tenant_id": tenant_id if settings.ENABLE_MULTI_TENANT else None,
            "database_type": database_type,
            "timestamp": datetime.now().isoformat(),
            "shared_knowledge_enabled": settings.ENABLE_SHARED_KNOWLEDGE if settings.ENABLE_MULTI_TENANT else None,
            "strict_isolation": settings.STRICT_TENANT_ISOLATION if settings.ENABLE_MULTI_TENANT else None
        })
        
        logger.info(f"Successfully generated {len(followup_questions)} follow-up questions")
        return result
        
    except Exception as e:
        logger.error(f"Error in vanna_generate_followup: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": f"Follow-up generation error: {str(e)}",
            "error_type": type(e).__name__,
            "suggestions": [
                "Check the SQL syntax",
                "Verify database connection",
                "Try with a simpler query"
            ]
        }

def _analyze_query_context(question: str, sql: str) -> Dict[str, Any]:
    """Analyze the question and SQL to understand context"""
    sql_upper = sql.upper()
    question_lower = question.lower()
    
    # Extract tables
    tables_pattern = r'FROM\s+([`"]?[\w.-]+[`"]?)(?:\s+(?:AS\s+)?\w+)?|JOIN\s+([`"]?[\w.-]+[`"]?)(?:\s+(?:AS\s+)?\w+)?'
    tables_matches = re.findall(tables_pattern, sql, re.IGNORECASE)
    tables = []
    for match in tables_matches:
        table = match[0] or match[1]
        if table and table.strip('`"').lower() not in tables:
            tables.append(table.strip('`"').lower())
    
    # Identify operations
    operations = []
    if "GROUP BY" in sql_upper:
        operations.append("grouping")
    if "ORDER BY" in sql_upper:
        operations.append("sorting")
    if "WHERE" in sql_upper:
        operations.append("filtering")
    if "JOIN" in sql_upper:
        operations.append("joining")
    if any(func in sql_upper for func in ["SUM(", "COUNT(", "AVG(", "MAX(", "MIN("]):
        operations.append("aggregation")
    
    # Identify metrics and dimensions
    metrics = []
    dimensions = []
    
    # Simple heuristic for metrics (aggregated values)
    if "sum" in question_lower or "total" in question_lower:
        metrics.append("sum")
    if "count" in question_lower or "number of" in question_lower:
        metrics.append("count")
    if "average" in question_lower or "avg" in question_lower:
        metrics.append("average")
    
    # Extract time-related keywords
    has_time = any(keyword in question_lower for keyword in ["month", "year", "date", "day", "week", "quarter"])
    
    return {
        "tables": tables,
        "operations": operations,
        "has_aggregation": "aggregation" in operations,
        "has_filtering": "filtering" in operations,
        "has_grouping": "grouping" in operations,
        "has_time": has_time,
        "metrics": metrics,
        "dimensions": dimensions
    }

def _generate_temporal_questions(context: Dict[str, Any], tenant_id: str) -> List[str]:
    """Generate time-based follow-up questions"""
    questions = []
    
    if not context["has_time"]:
        # Add time dimension if not present
        base_suggestion = "How does this change over time?"
        questions.append(base_suggestion)
        
        if context["has_aggregation"]:
            questions.append("What is the monthly trend for these values?")
            questions.append("Can you show the year-over-year comparison?")
    else:
        # Enhance existing time analysis
        questions.append("Can you break this down by quarter instead?")
        questions.append("What about the same period last year?")
        questions.append("Show me the moving average over the last 12 months")
    
    return questions[:3]  # Limit temporal questions

def _generate_comparison_questions(context: Dict[str, Any], tenant_id: str) -> List[str]:
    """Generate comparison-based follow-up questions"""
    questions = []
    
    if context["has_grouping"]:
        questions.append("How do the top 5 compare to the bottom 5?")
        questions.append("What's the percentage contribution of each group?")
        questions.append("Can you show the variance from the average?")
    else:
        questions.append("How does this compare across different categories?")
        questions.append("What are the outliers in this data?")
    
    return questions[:3]

def _generate_aggregation_questions(context: Dict[str, Any], tenant_id: str) -> List[str]:
    """Generate aggregation-based follow-up questions"""
    questions = []
    
    if context["has_aggregation"]:
        # Suggest different aggregations
        if "sum" in context["metrics"]:
            questions.append("What's the average instead of the total?")
        if "count" in context["metrics"]:
            questions.append("What's the sum of values for these items?")
        questions.append("Can you show both the total and the average?")
    else:
        # Suggest adding aggregations
        questions.append("What's the total across all records?")
        questions.append("How many unique values are there?")
        questions.append("What's the distribution of values?")
    
    return questions[:3]

def _generate_detail_questions(context: Dict[str, Any], tenant_id: str) -> List[str]:
    """Generate detail-oriented follow-up questions"""
    questions = []
    
    if context["has_filtering"]:
        questions.append("Can you show more details about the top result?")
        questions.append("What are the individual records that make up this total?")
    else:
        questions.append("Can you filter this to show only the significant values?")
        questions.append("What does this look like for a specific example?")
    
    if len(context["tables"]) == 1:
        questions.append("Are there related details in other tables?")
    
    return questions[:3]

async def _generate_related_questions(vn, context: Dict[str, Any], tenant_id: str) -> List[str]:
    """Generate questions about related tables"""
    questions = []
    
    # This would ideally look at the schema to find related tables
    # For now, we'll use generic suggestions
    if len(context["tables"]) == 1:
        questions.append("Can we include customer information with this data?")
        questions.append("Is there geographic data we can join to see regional patterns?")
        questions.append("Are there any related transactions we should consider?")
    else:
        questions.append("Can we add more context from additional tables?")
        questions.append("What other relationships exist in this data?")
    
    return questions[:2]

def _prioritize_questions(all_questions: List[str], max_count: int, categories: Dict[str, List[str]]) -> List[str]:
    """Prioritize questions for diversity and relevance"""
    prioritized = []
    
    # Take at least one from each non-empty category
    for category, questions in categories.items():
        if questions and len(prioritized) < max_count:
            prioritized.append(questions[0])
    
    # Fill remaining slots with highest quality questions
    for question in all_questions:
        if question not in prioritized and len(prioritized) < max_count:
            prioritized.append(question)
    
    return prioritized

# Tool definition for FastMCP
tool_definition = {
    "name": "vanna_generate_followup",
    "description": "Generate intelligent follow-up questions based on query context",
    "input_schema": {
        "type": "object",
        "properties": {
            "original_question": {
                "type": "string",
                "description": "The original natural language question"
            },
            "sql_generated": {
                "type": "string",
                "description": "The SQL query that was generated"
            },
            "tenant_id": {
                "type": "string",
                "description": "Tenant ID for multi-tenant mode (optional)"
            },
            "include_deeper_analysis": {
                "type": "boolean",
                "description": "Include questions for deeper analysis",
                "default": True
            },
            "include_related_tables": {
                "type": "boolean",
                "description": "Include questions about related tables",
                "default": True
            },
            "max_suggestions": {
                "type": "integer",
                "description": "Maximum number of suggestions (1-10)",
                "default": 5
            },
            "focus_area": {
                "type": "string",
                "enum": ["temporal", "comparison", "aggregation", "detail", "related"],
                "description": "Focus area for follow-up questions"
            }
        },
        "required": ["original_question", "sql_generated"]
    }
}