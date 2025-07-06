#!/usr/bin/env python3
"""
Setup database schema for Vanna MCP Server
Creates the necessary tables in Supabase
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from supabase import create_client, Client
from src.config.settings import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_schema_sql() -> str:
    """Generate SQL for creating the schema and tables"""
    schema = settings.VANNA_SCHEMA
    
    return f"""
-- Create schema if not exists
CREATE SCHEMA IF NOT EXISTS {schema};

-- Enable vector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Set search path
SET search_path TO {schema};

-- Query history table for analytics (separate from Vanna's training data)
CREATE TABLE IF NOT EXISTS {schema}.query_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question TEXT NOT NULL,
    generated_sql TEXT NOT NULL,
    execution_time_ms INTEGER,
    confidence_score NUMERIC(3,2), -- 0.00 to 1.00
    tenant_id VARCHAR(255),
    database_type VARCHAR(50),
    executed BOOLEAN DEFAULT false,
    row_count INTEGER,
    error_message TEXT,
    user_feedback VARCHAR(20), -- 'correct', 'incorrect', 'helpful', etc.
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for query history performance
CREATE INDEX IF NOT EXISTS idx_{schema.replace('.', '_')}_query_history_created 
    ON {schema}.query_history(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_{schema.replace('.', '_')}_query_history_tenant 
    ON {schema}.query_history(tenant_id);

CREATE INDEX IF NOT EXISTS idx_{schema.replace('.', '_')}_query_history_confidence 
    ON {schema}.query_history(confidence_score DESC);

-- Note: Vanna creates its own tables (vanna_collections, vanna_embeddings)
-- This script only creates our additional query_history table

-- Grant permissions (adjust as needed)
GRANT ALL ON SCHEMA {schema} TO postgres;
GRANT ALL ON ALL TABLES IN SCHEMA {schema} TO postgres;
GRANT ALL ON ALL SEQUENCES IN SCHEMA {schema} TO postgres;
"""

def initialize_access_control(supabase: Client):
    """Initialize access control with configured datasets"""
    schema = settings.VANNA_SCHEMA
    mode = settings.ACCESS_CONTROL_MODE
    datasets = settings.get_access_control_list()
    
    if not datasets:
        logger.info("No access control datasets configured")
        return
    
    logger.info(f"Initializing {mode} access control for datasets: {datasets}")
    
    for dataset in datasets:
        try:
            result = supabase.table(f"{schema}.access_control").upsert({
                "control_type": mode,
                "dataset_name": dataset,
                "active": True
            }, on_conflict="control_type,dataset_name").execute()
            logger.info(f"Added {dataset} to {mode}")
        except Exception as e:
            logger.error(f"Failed to add {dataset}: {e}")

def main():
    """Main setup function"""
    # Validate configuration
    config_status = settings.validate_config()
    
    if not config_status['valid']:
        logger.error("Configuration errors found:")
        for error in config_status['errors']:
            logger.error(f"  - {error}")
        sys.exit(1)
    
    if config_status['warnings']:
        logger.warning("Configuration warnings:")
        for warning in config_status['warnings']:
            logger.warning(f"  - {warning}")
    
    logger.info(f"Setting up schema: {settings.VANNA_SCHEMA}")
    
    # Create Supabase client
    supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    
    # Generate and execute schema SQL
    schema_sql = create_schema_sql()
    
    # Note: Supabase doesn't support direct SQL execution through the Python client
    # You'll need to run this SQL in the Supabase SQL editor or use psql
    
    print("\n" + "="*60)
    print("IMPORTANT: Supabase Python client doesn't support DDL execution.")
    print("Please run the following SQL in your Supabase SQL editor:")
    print("="*60 + "\n")
    print(schema_sql)
    print("\n" + "="*60)
    print("After running the SQL, press Enter to continue with access control setup...")
    input()
    
    # Initialize access control
    try:
        initialize_access_control(supabase)
        logger.info("Access control initialization complete")
    except Exception as e:
        logger.error(f"Failed to initialize access control: {e}")
        sys.exit(1)
    
    logger.info("Database setup complete!")
    logger.info(f"Schema '{settings.VANNA_SCHEMA}' is ready for use")

if __name__ == "__main__":
    main()