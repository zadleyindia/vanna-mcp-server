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
from typing import Dict, Any, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from fastmcp import FastMCP
from src.config.settings import settings
from src.tools.vanna_ask import vanna_ask
from src.tools.vanna_train import vanna_train
from src.tools.vanna_suggest_questions import vanna_suggest_questions
from src.tools.vanna_list_tenants import vanna_list_tenants

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

# TODO: Add other tools as we implement them
# - vanna_explain
# - vanna_execute
# - vanna_get_schemas
# - vanna_get_training_data
# - vanna_remove_training
# - vanna_generate_followup

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
    from typing import Dict, Any, Optional
    
    # Run the server
    main()