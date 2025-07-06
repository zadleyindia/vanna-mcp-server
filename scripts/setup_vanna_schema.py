#!/usr/bin/env python3
"""
Setup Vanna schema with proper statement ordering
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

def execute_sql_statements(cursor, statements):
    """Execute SQL statements one by one"""
    for i, (name, sql) in enumerate(statements):
        try:
            logger.info(f"Executing: {name}")
            cursor.execute(sql)
        except psycopg2.errors.DuplicateObject as e:
            logger.debug(f"Object already exists: {name}")
        except Exception as e:
            logger.error(f"Error executing {name}: {e}")
            raise

def setup_database():
    """Set up the database schema and tables"""
    schema = settings.VANNA_SCHEMA
    
    logger.info(f"Setting up database schema: {schema}")
    
    try:
        # Connect to database
        conn_string = settings.get_supabase_connection_string()
        conn = psycopg2.connect(conn_string)
        conn.autocommit = True
        cursor = conn.cursor()
        
        logger.info("Connected to database")
        
        # Define SQL statements in proper order
        statements = [
            ("Enable vector extension", "CREATE EXTENSION IF NOT EXISTS vector"),
            
            ("Create schema", f"CREATE SCHEMA IF NOT EXISTS {schema}"),
            
            ("Create training_data table", f"""
                CREATE TABLE IF NOT EXISTS {schema}.training_data (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    training_data_type VARCHAR(50) NOT NULL,
                    content TEXT NOT NULL,
                    embedding vector(1536),
                    metadata JSONB DEFAULT '{{}}',
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """),
            
            ("Create query_history table", f"""
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
                )
            """),
            
            ("Create access_control table", f"""
                CREATE TABLE IF NOT EXISTS {schema}.access_control (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    control_type VARCHAR(20) NOT NULL,
                    dataset_name VARCHAR(255) NOT NULL,
                    active BOOLEAN DEFAULT true,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    UNIQUE(control_type, dataset_name)
                )
            """),
            
            ("Create embedding index", f"""
                CREATE INDEX IF NOT EXISTS idx_{schema}_training_embedding 
                ON {schema}.training_data USING ivfflat (embedding vector_cosine_ops)
                WHERE embedding IS NOT NULL
            """),
            
            ("Create training type index", f"""
                CREATE INDEX IF NOT EXISTS idx_{schema}_training_type 
                ON {schema}.training_data(training_data_type)
            """),
            
            ("Create query history index", f"""
                CREATE INDEX IF NOT EXISTS idx_{schema}_query_history_created 
                ON {schema}.query_history(created_at DESC)
            """),
            
            ("Create update trigger function", f"""
                CREATE OR REPLACE FUNCTION {schema}.update_updated_at_column()
                RETURNS TRIGGER AS $$
                BEGIN
                    NEW.updated_at = NOW();
                    RETURN NEW;
                END;
                $$ language 'plpgsql'
            """),
            
            ("Create update trigger", f"""
                CREATE TRIGGER update_training_data_updated_at 
                BEFORE UPDATE ON {schema}.training_data 
                FOR EACH ROW 
                EXECUTE FUNCTION {schema}.update_updated_at_column()
            """),
            
            ("Grant schema permissions", f"GRANT ALL ON SCHEMA {schema} TO postgres"),
            ("Grant table permissions", f"GRANT ALL ON ALL TABLES IN SCHEMA {schema} TO postgres"),
            ("Grant sequence permissions", f"GRANT ALL ON ALL SEQUENCES IN SCHEMA {schema} TO postgres"),
            ("Grant function permissions", f"GRANT ALL ON ALL FUNCTIONS IN SCHEMA {schema} TO postgres"),
        ]
        
        # Execute statements
        execute_sql_statements(cursor, statements)
        
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
            WHERE table_schema = %s
            ORDER BY table_name
        """, (schema,))
        tables = cursor.fetchall()
        
        logger.info(f"\nCreated tables in schema '{schema}':")
        for table in tables:
            logger.info(f"  ✓ {table[0]}")
        
        # Check indexes
        cursor.execute(f"""
            SELECT indexname 
            FROM pg_indexes 
            WHERE schemaname = %s
        """, (schema,))
        indexes = cursor.fetchall()
        
        if indexes:
            logger.info(f"\nCreated indexes:")
            for index in indexes:
                logger.info(f"  ✓ {index[0]}")
        
        cursor.close()
        conn.close()
        
        logger.info("\n✅ Database setup completed successfully!")
        logger.info(f"Schema '{schema}' is ready for Vanna")
        
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