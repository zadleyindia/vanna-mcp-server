-- SQL to create query_history table in Supabase
-- Run this in your Supabase SQL Editor
-- Note: Based on MCP logs, the schema is 'vannabq'

-- Enable vector extension (if not already enabled)
CREATE EXTENSION IF NOT EXISTS vector;

-- Create schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS vannabq;

-- Set search path
SET search_path TO vannabq;

-- Create query history table for analytics (separate from Vanna's training data)
CREATE TABLE IF NOT EXISTS vannabq.query_history (
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
CREATE INDEX IF NOT EXISTS idx_vannabq_query_history_created 
    ON vannabq.query_history(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_vannabq_query_history_tenant 
    ON vannabq.query_history(tenant_id);

CREATE INDEX IF NOT EXISTS idx_vannabq_query_history_confidence 
    ON vannabq.query_history(confidence_score DESC);

-- Grant permissions (adjust as needed)
GRANT ALL ON SCHEMA vannabq TO postgres;
GRANT ALL ON vannabq.query_history TO postgres;

-- Verify table was created
SELECT table_schema, table_name, column_name, data_type 
FROM information_schema.columns 
WHERE table_schema = 'vannabq' AND table_name = 'query_history' 
ORDER BY ordinal_position;