"""
BigQuery schema definitions for catalog integration tables
"""

# Table for dataset-level context
CATALOG_DATASETS_SCHEMA = """
CREATE TABLE IF NOT EXISTS `{project}.{dataset}.catalog_datasets` (
    dataset_id STRING NOT NULL,
    project_id STRING NOT NULL,
    business_domain STRING,
    dataset_type STRING,
    owner_email STRING,
    description STRING,
    source_system STRING,
    refresh_cadence STRING,
    total_tables INT64,
    total_rows INT64,
    catalog_version TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY DATE(created_at)
CLUSTER BY dataset_id, business_domain;
"""

# Table for table/view business context
CATALOG_TABLE_CONTEXT_SCHEMA = """
CREATE TABLE IF NOT EXISTS `{project}.{dataset}.catalog_table_context` (
    id STRING DEFAULT GENERATE_UUID(),
    table_fqdn STRING NOT NULL,
    dataset_id STRING NOT NULL,
    table_id STRING NOT NULL,
    object_type STRING,  -- 'TABLE' or 'VIEW'
    
    -- Business context
    context_chunk STRING NOT NULL,  -- Combined business metadata
    business_domain STRING,
    grain_description STRING,
    
    -- Statistics
    row_count INT64,
    column_count INT64,
    last_updated TIMESTAMP,
    
    -- Tracking
    catalog_version TIMESTAMP,
    catalog_hash STRING,
    sync_status STRING DEFAULT 'current',
    
    -- Embedding
    embedding ARRAY<FLOAT64>,
    embedding_model STRING,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY DATE(created_at)
CLUSTER BY table_fqdn, dataset_id;
"""

# Table for column metadata chunks
CATALOG_COLUMN_CHUNKS_SCHEMA = """
CREATE TABLE IF NOT EXISTS `{project}.{dataset}.catalog_column_chunks` (
    id STRING DEFAULT GENERATE_UUID(),
    table_fqdn STRING NOT NULL,
    chunk_index INT64 NOT NULL,
    
    -- Chunk content
    column_chunk STRING NOT NULL,  -- Formatted column information
    column_names ARRAY<STRING>,  -- Columns in this chunk
    
    -- Statistics summary
    has_pii BOOLEAN DEFAULT FALSE,
    null_percentage FLOAT64,
    
    -- Tracking
    catalog_version TIMESTAMP,
    catalog_hash STRING,
    sync_status STRING DEFAULT 'current',
    
    -- Embedding
    embedding ARRAY<FLOAT64>,
    embedding_model STRING,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY DATE(created_at)
CLUSTER BY table_fqdn;
"""

# Table for view SQL patterns
CATALOG_VIEW_QUERIES_SCHEMA = """
CREATE TABLE IF NOT EXISTS `{project}.{dataset}.catalog_view_queries` (
    id STRING DEFAULT GENERATE_UUID(),
    view_fqdn STRING NOT NULL,
    chunk_index INT64 DEFAULT 1,
    
    -- Query content
    query_chunk STRING NOT NULL,
    query_type STRING,  -- 'full', 'select', 'joins', 'where', etc.
    
    -- Metadata
    tables_referenced ARRAY<STRING>,
    complexity_score INT64,  -- Based on query analysis
    
    -- Tracking
    catalog_version TIMESTAMP,
    catalog_hash STRING,
    sync_status STRING DEFAULT 'current',
    
    -- Embedding
    embedding ARRAY<FLOAT64>,
    embedding_model STRING,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY DATE(created_at)
CLUSTER BY view_fqdn;
"""

# Summary table for quick lookups
CATALOG_SUMMARY_SCHEMA = """
CREATE TABLE IF NOT EXISTS `{project}.{dataset}.catalog_summary` (
    id STRING DEFAULT GENERATE_UUID(),
    summary_type STRING,  -- 'dataset_tables', 'domain_overview', etc.
    summary_key STRING,
    
    -- Content
    summary_chunk STRING NOT NULL,
    metadata STRING,  -- JSON stored as string
    
    -- Tracking
    catalog_version TIMESTAMP,
    
    -- Embedding
    embedding ARRAY<FLOAT64>,
    embedding_model STRING,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY DATE(created_at)
CLUSTER BY summary_type, summary_key;
"""

# All schemas in order of creation
CATALOG_SCHEMAS = [
    ("catalog_datasets", CATALOG_DATASETS_SCHEMA),
    ("catalog_table_context", CATALOG_TABLE_CONTEXT_SCHEMA),
    ("catalog_column_chunks", CATALOG_COLUMN_CHUNKS_SCHEMA),
    ("catalog_view_queries", CATALOG_VIEW_QUERIES_SCHEMA),
    ("catalog_summary", CATALOG_SUMMARY_SCHEMA)
]