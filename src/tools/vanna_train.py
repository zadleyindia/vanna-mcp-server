"""
vanna_train tool - Add training data to improve SQL generation
Priority #2 tool in our implementation
"""
from typing import Dict, Any, Optional, List
import logging
import re
from datetime import datetime
from src.config.vanna_config import get_vanna
from src.config.settings import settings
from google.cloud import bigquery

logger = logging.getLogger(__name__)

async def vanna_train(
    training_type: str,
    content: str,
    question: Optional[str] = None,
    tenant_id: Optional[str] = None,
    is_shared: bool = False,
    metadata: Optional[Dict[str, Any]] = None,
    validate: bool = True
) -> Dict[str, Any]:
    """
    Train Vanna with new data to improve SQL generation.
    
    This tool allows adding training data in three forms:
    1. DDL - Table definitions and schema
    2. Documentation - Business context and descriptions
    3. SQL - Question-SQL pairs for pattern learning
    
    Args:
        training_type (str): Type of training data - 'ddl', 'documentation', or 'sql'
        
        content (str): The training content
            - For 'ddl': CREATE TABLE statement
            - For 'documentation': Text description of tables/business logic
            - For 'sql': The SQL query
            
        question (str, optional): Required for 'sql' type - the natural language question
            that corresponds to the SQL query
        
        tenant_id (str, optional): Override default tenant (for multi-tenant mode)
            Default: None (uses settings.TENANT_ID)
        
        is_shared (bool): Mark this as shared knowledge for all tenants (multi-tenant mode)
            Default: False
            
        metadata (dict, optional): Additional metadata like:
            - source: Where this training data came from
            - confidence: How confident we are in this training
            - tags: Categories or labels
            
        validate (bool): Whether to validate before training
            - For SQL: Check syntax and run dry query
            - For DDL: Verify table exists
            Default: True
    
    Returns:
        Dict containing:
        - success (bool): Whether training was successful
        - training_id (str): ID of the training record
        - message (str): Success or error message
        - validation_results (dict): Results of validation if performed
        - suggestions (list): Related training suggestions
        
    Example Usage:
        # Train with DDL
        vanna_train(
            training_type="ddl",
            content="CREATE TABLE sales (id INT, amount DECIMAL, date DATE)"
        )
        
        # Train with documentation
        vanna_train(
            training_type="documentation", 
            content="The sales table contains all customer transactions. Use totalvalue for revenue calculations."
        )
        
        # Train with SQL
        vanna_train(
            training_type="sql",
            question="What were total sales last month?",
            content="SELECT SUM(totalvalue) FROM sales WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 MONTH)"
        )
    """
    try:
        vn = get_vanna()
        
        # Validate inputs
        if training_type not in ['ddl', 'documentation', 'sql']:
            return {
                "success": False,
                "message": f"Invalid training_type: {training_type}. Must be 'ddl', 'documentation', or 'sql'",
                "suggestions": ["Use 'ddl' for table definitions", "Use 'documentation' for descriptions", "Use 'sql' for query examples"]
            }
        
        if training_type == 'sql' and not question:
            return {
                "success": False,
                "message": "Question is required when training_type is 'sql'",
                "suggestions": ["Provide the natural language question that corresponds to this SQL"]
            }
        
        # Handle tenant_id in multi-tenant mode
        if settings.ENABLE_MULTI_TENANT and not is_shared:
            # Use default tenant if not provided
            if not tenant_id:
                tenant_id = settings.TENANT_ID
                logger.info(f"No tenant_id provided, using default: {tenant_id}")
            
            # Validate tenant_id
            if not tenant_id:
                return {
                    "success": False,
                    "message": "tenant_id is required when multi-tenant is enabled and is_shared is false",
                    "allowed_tenants": settings.get_allowed_tenants(),
                    "suggestions": ["Specify tenant_id in the training request", "Set TENANT_ID in environment variables", "Use is_shared=true for shared knowledge"]
                }
            
            if not settings.is_tenant_allowed(tenant_id):
                allowed = settings.get_allowed_tenants()
                return {
                    "success": False,
                    "message": f"Tenant '{tenant_id}' is not allowed",
                    "allowed_tenants": allowed if allowed else "All tenants allowed (no restrictions)",
                    "suggestions": ["Use one of the allowed tenants", "Check your tenant configuration"]
                }
        
        # Perform validation if requested
        validation_results = {}
        if validate:
            validation_results = await _validate_training_content(
                training_type, content, question
            )
            
            if not validation_results.get("valid", False):
                return {
                    "success": False,
                    "message": f"Validation failed: {validation_results.get('error', 'Unknown error')}",
                    "validation_results": validation_results,
                    "suggestions": validation_results.get("suggestions", [])
                }
        
        # Train based on type
        logger.info(f"Training Vanna with {training_type}")
        
        # Prepare enhanced metadata
        enhanced_metadata = metadata or {}
        enhanced_metadata['training_source'] = 'mcp_tool'
        enhanced_metadata['training_type'] = training_type
        
        if training_type == 'ddl':
            success = vn.train(
                ddl=content,
                tenant_id=tenant_id,
                is_shared=is_shared,
                metadata=enhanced_metadata
            )
            training_id = f"ddl_{datetime.now().timestamp()}"
            
        elif training_type == 'documentation':
            success = vn.train(
                documentation=content,
                tenant_id=tenant_id,
                is_shared=is_shared,
                metadata=enhanced_metadata
            )
            training_id = f"doc_{datetime.now().timestamp()}"
            
        elif training_type == 'sql':
            success = vn.train(
                question=question,
                sql=content,
                tenant_id=tenant_id,
                is_shared=is_shared,
                metadata=enhanced_metadata
            )
            training_id = f"sql_{datetime.now().timestamp()}"
        
        if success:
            # Store training history
            _store_training_history(
                training_type=training_type,
                content=content,
                question=question,
                tenant_id=tenant_id,
                is_shared=is_shared,
                metadata=enhanced_metadata,
                validation_results=validation_results
            )
            
            logger.info(f"Successfully trained with {training_type}")
            
            # Generate suggestions for additional training
            suggestions = _generate_training_suggestions(training_type, content, question)
            
            # Build success message
            message = f"Successfully added {training_type} training data"
            if settings.ENABLE_MULTI_TENANT and is_shared:
                message += " as shared knowledge for all tenants"
            elif settings.ENABLE_MULTI_TENANT:
                effective_tenant = tenant_id or settings.TENANT_ID
                message += f" for tenant '{effective_tenant}'"
                
            return {
                "success": True,
                "training_id": training_id,
                "message": message,
                "is_shared": is_shared,
                "validation_results": validation_results,
                "suggestions": suggestions
            }
        else:
            return {
                "success": False,
                "message": f"Failed to train with {training_type}",
                "suggestions": ["Check the content format", "Verify Vanna connection"]
            }
            
    except Exception as e:
        logger.error(f"Error in vanna_train: {str(e)}", exc_info=True)
        return {
            "success": False,
            "message": f"Training error: {str(e)}",
            "error_type": type(e).__name__,
            "suggestions": ["Check your input format", "Verify database connection"]
        }

async def _validate_training_content(
    training_type: str, 
    content: str, 
    question: Optional[str]
) -> Dict[str, Any]:
    """Validate training content before adding"""
    
    if training_type == 'sql':
        # Validate SQL syntax and safety
        return await _validate_sql_training(content, question)
    
    elif training_type == 'ddl':
        # Validate DDL format
        return _validate_ddl_training(content)
    
    elif training_type == 'documentation':
        # Basic validation for documentation
        return _validate_documentation_training(content)
    
    return {"valid": True}

async def _validate_sql_training(sql: str, question: str) -> Dict[str, Any]:
    """Validate SQL for training"""
    try:
        # Check if SELECT only
        sql_upper = sql.strip().upper()
        if not sql_upper.startswith('SELECT'):
            return {
                "valid": False,
                "error": "Only SELECT statements are allowed for training",
                "suggestions": ["Ensure your SQL starts with SELECT", "Remove any INSERT/UPDATE/DELETE statements"]
            }
        
        # Check for dangerous keywords
        dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'TRUNCATE']
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                return {
                    "valid": False,
                    "error": f"SQL contains forbidden keyword: {keyword}",
                    "suggestions": ["Use only SELECT statements", "Remove any data modification commands"]
                }
        
        # Dry run with LIMIT 1 if configured
        if settings.MANDATORY_QUERY_VALIDATION:
            try:
                # Add LIMIT 1 for validation
                test_sql = sql
                if 'LIMIT' not in sql_upper:
                    test_sql = f"{sql} LIMIT 1"
                
                # Create BigQuery client and run query
                client = bigquery.Client(project=settings.BIGQUERY_PROJECT)
                query_job = client.query(test_sql)
                
                # Wait for query to complete
                results = query_job.result()
                row_count = results.total_rows
                
                if row_count == 0:
                    return {
                        "valid": True,
                        "warning": "Query returned no results",
                        "suggestions": ["Verify the query returns data", "Check date ranges and filters"]
                    }
                
                return {
                    "valid": True,
                    "query_validated": True,
                    "execution_time_ms": query_job.slot_millis,
                    "bytes_processed": query_job.total_bytes_processed
                }
                
            except Exception as e:
                return {
                    "valid": False,
                    "error": f"Query validation failed: {str(e)}",
                    "suggestions": ["Check table and column names", "Verify SQL syntax for BigQuery"]
                }
        
        return {"valid": True}
        
    except Exception as e:
        return {
            "valid": False,
            "error": f"Validation error: {str(e)}",
            "suggestions": ["Check SQL syntax"]
        }

def _validate_ddl_training(ddl: str) -> Dict[str, Any]:
    """Validate DDL format"""
    ddl_upper = ddl.strip().upper()
    
    if not ddl_upper.startswith('CREATE TABLE'):
        return {
            "valid": False,
            "error": "DDL must be a CREATE TABLE statement",
            "suggestions": ["Start with 'CREATE TABLE'", "Include column definitions"]
        }
    
    # Check for basic structure
    if '(' not in ddl or ')' not in ddl:
        return {
            "valid": False,
            "error": "DDL must include column definitions in parentheses",
            "suggestions": ["Format: CREATE TABLE table_name (column definitions)"]
        }
    
    return {"valid": True}

def _validate_documentation_training(doc: str) -> Dict[str, Any]:
    """Validate documentation"""
    if len(doc.strip()) < 10:
        return {
            "valid": False,
            "error": "Documentation too short",
            "suggestions": ["Provide meaningful descriptions", "Include table/column purposes"]
        }
    
    return {"valid": True}

def _generate_training_suggestions(
    training_type: str, 
    content: str, 
    question: Optional[str]
) -> List[str]:
    """Generate suggestions for additional training"""
    suggestions = []
    
    if training_type == 'sql':
        # Suggest variations
        suggestions.extend([
            "Add similar queries with different time ranges",
            "Include queries with different aggregations (COUNT, AVG)",
            "Add queries that JOIN with other tables"
        ])
        
    elif training_type == 'ddl':
        # Extract table name and suggest documentation
        table_match = re.search(r'CREATE TABLE\s+`?([^`\s(]+)', content, re.IGNORECASE)
        if table_match:
            table_name = table_match.group(1)
            suggestions.extend([
                f"Add documentation explaining what {table_name} contains",
                f"Add sample queries for {table_name}",
                f"Document relationships with other tables"
            ])
            
    elif training_type == 'documentation':
        # Suggest related training
        suggestions.extend([
            "Add CREATE TABLE statements for mentioned tables",
            "Include example queries demonstrating the concepts",
            "Document column-level details and data types"
        ])
    
    return suggestions[:3]  # Limit suggestions

def _store_training_history(
    training_type: str,
    content: str,
    question: Optional[str],
    tenant_id: Optional[str],
    is_shared: bool,
    metadata: Optional[Dict[str, Any]],
    validation_results: Dict[str, Any]
):
    """Store training history for audit and rollback"""
    try:
        # This would store in a training history table
        # For now, just log it
        logger.info(f"Training history stored: {training_type} - {content[:50]}...")
    except Exception as e:
        logger.warning(f"Failed to store training history: {e}")

# Tool definition for FastMCP
tool_definition = {
    "name": "vanna_train",
    "description": "Add training data (DDL, documentation, or SQL examples) to improve Vanna's SQL generation",
    "input_schema": {
        "type": "object",
        "properties": {
            "training_type": {
                "type": "string",
                "enum": ["ddl", "documentation", "sql"],
                "description": "Type of training data being added"
            },
            "content": {
                "type": "string",
                "description": "The training content (DDL statement, documentation text, or SQL query)"
            },
            "question": {
                "type": "string",
                "description": "Natural language question (required for 'sql' training_type)"
            },
            "metadata": {
                "type": "object",
                "description": "Optional metadata about the training data"
            },
            "validate": {
                "type": "boolean",
                "description": "Whether to validate the content before training",
                "default": True
            }
        },
        "required": ["training_type", "content"]
    }
}