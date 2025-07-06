"""
vanna_suggest_questions tool - Get suggested questions based on training data
Priority #3 tool in our implementation
"""
from typing import Dict, Any, List, Optional
import logging
import random
from src.config.vanna_config import get_vanna
from src.config.settings import settings

logger = logging.getLogger(__name__)

async def vanna_suggest_questions(
    context: Optional[str] = None,
    limit: int = 5,
    include_metadata: bool = True
) -> Dict[str, Any]:
    """
    Get suggested questions based on the training data.
    
    This tool analyzes the training data and suggests relevant questions
    that users can ask. It's useful for:
    - Onboarding new users
    - Discovering available data
    - Understanding query patterns
    
    Args:
        context (str, optional): Context to filter suggestions
            - Table name: Get questions about a specific table
            - Dataset name: Get questions about a dataset
            - Topic: Get questions about a business topic
            Default: None (general suggestions)
            
        limit (int): Maximum number of suggestions to return
            Default: 5 (max: 20)
            
        include_metadata (bool): Include metadata about why each question was suggested
            Default: True
    
    Returns:
        Dict containing:
        - suggestions (list): List of suggested questions with metadata
        - total_available (int): Total number of suggestions available
        - context_used (str): The context that was applied
        - categories (list): Categories of available questions
        
    Example Usage:
        # Get general suggestions
        vanna_suggest_questions()
        
        # Get suggestions about a specific table
        vanna_suggest_questions(context="sales", limit=10)
        
        # Get suggestions without metadata
        vanna_suggest_questions(include_metadata=False)
    """
    try:
        vn = get_vanna()
        
        # Validate limit
        limit = min(max(1, limit), 20)
        
        logger.info(f"Getting question suggestions (context: {context}, limit: {limit})")
        
        # Get training data to generate suggestions
        # Vanna stores SQL-question pairs that we can use
        training_data = vn.get_training_data()
        
        suggestions = []
        categories = set()
        
        # Filter and categorize training data
        sql_questions = []
        for item in training_data:
            if item.get('question') and item.get('content'):
                # Check if matches context
                if context:
                    context_lower = context.lower()
                    question_lower = item['question'].lower()
                    sql_lower = item['content'].lower()
                    
                    # Check if context appears in question or SQL
                    if context_lower not in question_lower and context_lower not in sql_lower:
                        continue
                
                sql_questions.append({
                    'question': item['question'],
                    'sql': item['content'],
                    'id': item.get('id', 'unknown')
                })
                
                # Extract category from question
                if 'total' in item['question'].lower() or 'sum' in item['question'].lower():
                    categories.add('aggregations')
                elif 'by' in item['question'].lower():
                    categories.add('grouping')
                elif 'when' in item['question'].lower() or 'date' in item['question'].lower():
                    categories.add('time-based')
                elif 'top' in item['question'].lower() or 'most' in item['question'].lower():
                    categories.add('rankings')
                else:
                    categories.add('general')
        
        # Generate additional suggestions based on DDL
        ddl_suggestions = _generate_ddl_based_suggestions(vn, context)
        
        # Combine all suggestions
        all_suggestions = sql_questions + ddl_suggestions
        
        # Remove duplicates
        seen_questions = set()
        unique_suggestions = []
        for sugg in all_suggestions:
            if sugg['question'] not in seen_questions:
                seen_questions.add(sugg['question'])
                unique_suggestions.append(sugg)
        
        # Sort by relevance (if context provided) or randomly
        if context:
            # Sort by how well they match the context
            unique_suggestions.sort(
                key=lambda x: _calculate_relevance(x['question'], context),
                reverse=True
            )
        else:
            # Random shuffle for variety
            random.shuffle(unique_suggestions)
        
        # Take requested limit
        selected_suggestions = unique_suggestions[:limit]
        
        # Format suggestions
        formatted_suggestions = []
        for i, sugg in enumerate(selected_suggestions):
            suggestion_item = {
                "question": sugg['question'],
                "position": i + 1
            }
            
            if include_metadata:
                # Determine why this was suggested
                reasons = []
                
                if context:
                    if context.lower() in sugg['question'].lower():
                        reasons.append(f"Mentions '{context}'")
                    elif context.lower() in sugg.get('sql', '').lower():
                        reasons.append(f"Queries data related to '{context}'")
                
                if 'source' in sugg:
                    reasons.append(f"Based on {sugg['source']}")
                
                # Add category info
                question_lower = sugg['question'].lower()
                if 'total' in question_lower or 'sum' in question_lower:
                    reasons.append("Aggregation query")
                elif 'top' in question_lower:
                    reasons.append("Ranking query")
                
                suggestion_item['metadata'] = {
                    'reasons': reasons,
                    'category': _categorize_question(sugg['question']),
                    'training_id': sugg.get('id', 'generated')
                }
            
            formatted_suggestions.append(suggestion_item)
        
        # Get unique categories
        unique_categories = list(categories)
        unique_categories.sort()
        
        logger.info(f"Generated {len(formatted_suggestions)} suggestions")
        
        return {
            "success": True,
            "suggestions": formatted_suggestions,
            "total_available": len(unique_suggestions),
            "context_used": context or "general",
            "categories": unique_categories,
            "message": f"Found {len(formatted_suggestions)} relevant questions"
        }
        
    except Exception as e:
        logger.error(f"Error in vanna_suggest_questions: {str(e)}", exc_info=True)
        return {
            "success": False,
            "suggestions": [],
            "error": str(e),
            "message": "Failed to generate suggestions",
            "fallback_suggestions": [
                "What tables are available?",
                "Show me the schema for the sales table",
                "What are the total sales by month?",
                "List the top 10 customers by revenue",
                "Show me all columns in the customer table"
            ]
        }

def _generate_ddl_based_suggestions(vn, context: Optional[str] = None) -> List[Dict[str, str]]:
    """Generate suggestions based on available DDL"""
    suggestions = []
    
    try:
        # Get training data of type DDL
        training_data = vn.get_training_data()
        
        tables_seen = set()
        for item in training_data:
            if item.get('training_data_type') == 'ddl':
                # Extract table name from DDL
                ddl = item.get('content', '')
                import re
                table_match = re.search(r'CREATE TABLE\s+`?([^`\s(]+)', ddl, re.IGNORECASE)
                
                if table_match:
                    table_name = table_match.group(1)
                    
                    # Remove project and dataset prefix if present
                    if '.' in table_name:
                        table_name = table_name.split('.')[-1]
                    
                    if table_name not in tables_seen:
                        tables_seen.add(table_name)
                        
                        # Generate questions for this table
                        suggestions.extend([
                            {
                                'question': f"What columns are in the {table_name} table?",
                                'source': 'ddl',
                                'sql': ''
                            },
                            {
                                'question': f"Show me sample data from {table_name}",
                                'source': 'ddl', 
                                'sql': ''
                            },
                            {
                                'question': f"How many records are in {table_name}?",
                                'source': 'ddl',
                                'sql': ''
                            }
                        ])
        
        # Filter by context if provided
        if context and suggestions:
            context_lower = context.lower()
            suggestions = [s for s in suggestions if context_lower in s['question'].lower()]
        
    except Exception as e:
        logger.warning(f"Could not generate DDL-based suggestions: {e}")
    
    return suggestions

def _calculate_relevance(question: str, context: str) -> float:
    """Calculate relevance score for a question given context"""
    question_lower = question.lower()
    context_lower = context.lower()
    
    score = 0.0
    
    # Exact match in question
    if context_lower in question_lower:
        score += 1.0
        
        # Bonus for word boundaries
        if f" {context_lower} " in f" {question_lower} ":
            score += 0.5
    
    # Partial matches
    context_words = context_lower.split()
    for word in context_words:
        if len(word) > 3 and word in question_lower:  # Skip short words
            score += 0.3
    
    return score

def _categorize_question(question: str) -> str:
    """Categorize a question based on keywords"""
    question_lower = question.lower()
    
    if any(word in question_lower for word in ['total', 'sum', 'count', 'average', 'avg']):
        return 'aggregation'
    elif any(word in question_lower for word in ['top', 'most', 'best', 'highest', 'lowest']):
        return 'ranking'
    elif any(word in question_lower for word in ['by month', 'by year', 'by date', 'over time']):
        return 'time-series'
    elif any(word in question_lower for word in ['group by', 'by', 'per']):
        return 'grouping'
    elif any(word in question_lower for word in ['schema', 'columns', 'structure', 'describe']):
        return 'metadata'
    elif any(word in question_lower for word in ['sample', 'example', 'show me']):
        return 'exploration'
    else:
        return 'general'

# Tool definition for FastMCP
tool_definition = {
    "name": "vanna_suggest_questions",
    "description": "Get suggested questions based on available data and training patterns",
    "input_schema": {
        "type": "object",
        "properties": {
            "context": {
                "type": "string",
                "description": "Optional context to filter suggestions (table name, dataset, or topic)"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of suggestions to return (1-20)",
                "default": 5,
                "minimum": 1,
                "maximum": 20
            },
            "include_metadata": {
                "type": "boolean",
                "description": "Include metadata about why each question was suggested",
                "default": True
            }
        },
        "required": []
    }
}