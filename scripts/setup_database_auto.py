#!/usr/bin/env python3
"""
Automatic database setup using direct PostgreSQL connection
"""
import sys
import psycopg2
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from src.config.settings import settings
import logging

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_schema_sql(schema):
    """Generate SQL for creating Vanna schema and tables"""
    return f"""
-- Enable vector extension (must be done before creating schema)
CREATE EXTENSION IF NOT EXISTS vector;

-- Create schema if not exists
CREATE SCHEMA IF NOT EXISTS {schema};

-- Set search path
SET search_path TO {schema};

-- Training data table (Vanna's core)
CREATE TABLE IF NOT EXISTS {schema}.training_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    training_data_type VARCHAR(50) NOT NULL,
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
    user_feedback VARCHAR(20),
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Access control configuration
CREATE TABLE IF NOT EXISTS {schema}.access_control (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    control_type VARCHAR(20) NOT NULL,
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

-- Grant permissions
GRANT ALL ON SCHEMA {schema} TO postgres;
GRANT ALL ON ALL TABLES IN SCHEMA {schema} TO postgres;
GRANT ALL ON ALL SEQUENCES IN SCHEMA {schema} TO postgres;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA {schema} TO postgres;
"""

def setup_database():
    """Set up the database schema and tables"""
    schema = settings.VANNA_SCHEMA
    
    logger.info(f"Setting up database schema: {schema}")
    
    try:
        # Connect to database
        conn_string = settings.get_supabase_connection_string()
        conn = psycopg2.connect(conn_string)
        conn.autocommit = True  # Enable autocommit for DDL operations
        cursor = conn.cursor()
        
        logger.info("Connected to database")
        
        # First ensure vector extension is enabled
        try:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
            logger.info("pgvector extension enabled")
        except psycopg2.errors.DuplicateObject:
            logger.info("pgvector extension already exists")
        
        # Execute schema creation SQL
        schema_sql = create_schema_sql(schema)
        
        # Split SQL into individual statements, handling multi-line statements properly
        import re
        # Split by semicolon but not within strings or dollar-quoted blocks
        statements = re.split(r';\s*(?=(?:[^\']*\'[^\']*\')*[^\']*$)', schema_sql)
        statements = [stmt.strip() for stmt in statements if stmt.strip()]
        
        for i, statement in enumerate(statements):
            if statement and not statement.startswith('--'):
                try:
                    logger.debug(f"Executing statement {i+1}/{len(statements)}")
                    # Add semicolon back if not present
                    if not statement.rstrip().endswith(';'):
                        statement += ';'
                    cursor.execute(statement)
                except psycopg2.errors.DuplicateObject as e:
                    # Ignore duplicate object errors (already exists)
                    logger.debug(f"Object already exists: {str(e)[:50]}...")
                except Exception as e:
                    logger.error(f"Error executing statement: {e}")
                    logger.error(f"Statement: {statement[:100]}...")
                    raise
        
        logger.info("Schema and tables created successfully")
        
        # Initialize access control data
        if settings.ACCESS_CONTROL_MODE and settings.ACCESS_CONTROL_DATASETS:
            logger.info(f"Initializing {settings.ACCESS_CONTROL_MODE} access control")
            
            for dataset in settings.get_access_control_list():
                try:
                    cursor.execute(f"""
                        INSERT INTO {schema}.access_control (control_type, dataset_name, active)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (control_type, dataset_name) 
                        DO UPDATE SET active = EXCLUDED.active
                    """, (settings.ACCESS_CONTROL_MODE, dataset, True))
                    logger.info(f"Added {dataset} to {settings.ACCESS_CONTROL_MODE}")
                except Exception as e:
                    logger.error(f"Failed to add {dataset}: {e}")
        
        # Verify setup
        cursor.execute(f"""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = '{schema}'
            ORDER BY table_name
        """)
        tables = cursor.fetchall()
        
        logger.info(f"Created tables in schema '{schema}':")
        for table in tables:
            logger.info(f"  - {table[0]}")
        
        cursor.close()
        conn.close()
        
        logger.info("✅ Database setup completed successfully!")
        
    except Exception as e:
        logger.error(f"Failed to set up database: {e}")
        raise

def main():
    """Main function"""
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
    
    try:
        setup_database()
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()