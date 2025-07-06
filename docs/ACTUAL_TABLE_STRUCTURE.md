# Actual Table Structure Used by Vanna MCP Server

## Overview
After analyzing the codebase, here's the actual table structure being used vs what was planned.

## Tables Actually Used (in public schema)

### 1. langchain_pg_collection
Created and managed by LangChain/Vanna for storing collection metadata.

```sql
-- Stores different types of training data collections
-- Examples: 'ddl', 'documentation', 'sql'
CREATE TABLE public.langchain_pg_collection (
    uuid UUID PRIMARY KEY,
    name VARCHAR,
    cmetadata JSON,
    ...
);
```

### 2. langchain_pg_embedding  
Created and managed by LangChain/Vanna for storing embeddings and training data.

```sql
-- Stores actual training data with embeddings
CREATE TABLE public.langchain_pg_embedding (
    id TEXT PRIMARY KEY,
    collection_id UUID REFERENCES langchain_pg_collection(uuid),
    embedding VECTOR,
    document TEXT,
    cmetadata JSONB,  -- This is where tenant_id, database_type etc. are stored
    ...
);
```

### Metadata Structure in cmetadata Column
```json
{
  "database_type": "bigquery",
  "tenant_id": "customer1",        // Only in multi-tenant mode
  "database_name": "bigquerylascout",
  "schema_name": "SQL_ZADLEY",
  "table_name": "sales",
  "training_source": "mcp_tool",
  "training_type": "ddl",
  "timestamp": "2025-01-05 10:30:00"
}
```

## Tables NOT Used (exist in vannabq schema but unused)

### 1. training_data
- **Purpose**: Was meant to store training data
- **Status**: NOT USED - Vanna uses langchain_pg_embedding instead
- **Code References**: Only in setup scripts, no runtime usage

### 2. query_history
- **Purpose**: Was meant to store query history for analytics
- **Status**: NOT USED - Only has stub function that logs to console
- **Code References**: `_store_query_history()` in vanna_ask.py (doesn't actually store)

### 3. access_control
- **Purpose**: Was meant to enforce dataset-level access control
- **Status**: PARTIALLY USED - Data is inserted during setup but never queried
- **Code References**: Setup scripts insert data, but no runtime enforcement

## Why This Happened

1. **Vanna Integration**: Vanna comes with its own storage layer (pgvector via LangChain)
2. **Schema Configuration**: Our fork supports configurable schemas via `VANNA_SCHEMA` setting
3. **Design Evolution**: Original design had custom tables, but implementation used Vanna defaults with schema flexibility

## Current Architecture

```
┌─────────────────────────────────────┐
│         MCP Server Instance         │
│    (e.g., vanna-bigquery-mcp)      │
└─────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│        Vanna + LangChain            │
│   (Multi-tenant via metadata)      │
└─────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│     PostgreSQL (Supabase)           │
│                                     │
│  {VANNA_SCHEMA} (configurable):     │
│  - vanna_collections                │
│  - vanna_embeddings                 │
│    └── cmetadata (JSONB):           │
│        - database_type              │
│        - tenant_id                  │
│        - other metadata             │
└─────────────────────────────────────┘
```

## Recommendations

1. **Keep schema flexibility** - Our fork supports configurable schemas via `VANNA_SCHEMA`
2. **Use consistent schema** - Query history table should use same `VANNA_SCHEMA` setting
3. **Update documentation** - Clarify that we're not limited to public schema like original Vanna

## Migration Script

Run the consolidation script to clean up:
```bash
python scripts/consolidate_to_public_schema.py
```

This will:
- Show what's in each schema
- Let you decide whether to drop vannabq
- Clean up any leftover redirect views/functions

## Future Considerations

If you need the planned features:

1. **Query History**: 
   - Option 1: Implement using Vanna's tables with metadata
   - Option 2: Use application-level logging
   - Option 3: Create a separate analytics service

2. **Access Control**:
   - Currently handled by `ALLOWED_TENANTS` configuration
   - Could be enhanced with database-level row security

3. **Custom Training Data**:
   - Vanna's storage is sufficient for current needs
   - Metadata filtering provides the needed flexibility