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

-- Drop existing tables if needed (be careful in production!)
-- DROP TABLE IF EXISTS {schema}.training_data CASCADE;
-- DROP TABLE IF EXISTS {schema}.query_history CASCADE;
-- DROP TABLE IF EXISTS {schema}.access_control CASCADE;

-- Training data table (Vanna's core)
CREATE TABLE IF NOT EXISTS {schema}.training_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    training_data_type VARCHAR(50) NOT NULL, -- 'ddl', 'documentation', 'sql'
    content TEXT NOT NULL,
    embedding vector(1536),
    metadata JSONB DEFAULT '{{}}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Query history for learning
CREATE TABLE IF NOT EXISTS {schema}.query_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question TEXT NOT NULL,
    generated_sql TEXT NOT NULL,
    executed BOOLEAN DEFAULT false,
    execution_time_ms INTEGER,
    row_count INTEGER,
    user_feedback VARCHAR(20), -- 'correct', 'incorrect'
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Access control configuration
CREATE TABLE IF NOT EXISTS {schema}.access_control (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    control_type VARCHAR(20) NOT NULL, -- 'whitelist' or 'blacklist'
    dataset_name VARCHAR(255) NOT NULL,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(control_type, dataset_name)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_{schema}_training_embedding 
    ON {schema}.training_data USING ivfflat (embedding vector_cosine_ops)
    WHERE embedding IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_{schema}_training_type 
    ON {schema}.training_data(training_data_type);

CREATE INDEX IF NOT EXISTS idx_{schema}_query_history_created 
    ON {schema}.query_history(created_at DESC);

-- Create update trigger for updated_at
CREATE OR REPLACE FUNCTION {schema}.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_training_data_updated_at 
    BEFORE UPDATE ON {schema}.training_data 
    FOR EACH ROW 
    EXECUTE FUNCTION {schema}.update_updated_at_column();

-- Grant permissions (adjust as needed)
GRANT ALL ON SCHEMA {schema} TO postgres;
GRANT ALL ON ALL TABLES IN SCHEMA {schema} TO postgres;
GRANT ALL ON ALL SEQUENCES IN SCHEMA {schema} TO postgres;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA {schema} TO postgres;
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