# Schema Support in Forked Vanna

## Overview

We've successfully enhanced our forked Vanna to support custom PostgreSQL schemas, removing the limitation of being restricted to the public schema.

## What Was The Problem?

The original Vanna uses LangChain's PGVector implementation, which:
- Creates tables (`langchain_pg_collection`, `langchain_pg_embedding`) in the public schema
- Has no configuration option for custom schemas
- Hardcodes table references without schema qualification

## Our Solution

### 1. Created SchemaAwarePGVectorStore

In our forked Vanna (`vanna-fork/src/vanna/pgvector/pgvector_with_schema.py`), we created a new implementation that:

- **Accepts schema configuration**: `config={"schema": "my_custom_schema"}`
- **Creates schema-specific tables**: 
  - `{schema}.vanna_collections`
  - `{schema}.vanna_embeddings`
- **Uses schema-qualified queries**: All SQL uses `schema.table` notation
- **Maintains compatibility**: Works as drop-in replacement

### 2. Key Features

```python
# Use any schema you want!
vn = SchemaAwarePGVectorStore(config={
    "connection_string": "postgresql://...",
    "schema": "vanna_production"  # Your custom schema
})

# Everything works the same, but in your schema
vn.add_ddl("CREATE TABLE users (...)")
vn.add_question_sql("Show all users", "SELECT * FROM users")
```

### 3. Benefits

1. **Schema Isolation**: Different projects/environments can use different schemas
2. **Better Organization**: Keep Vanna tables separate from application tables
3. **Multi-Instance Support**: Run multiple Vanna instances in one database
4. **Security**: Use PostgreSQL schema permissions for access control

## Implementation Details

### Table Structure

Instead of LangChain's tables in public schema:
```sql
-- LangChain's approach (public schema only)
public.langchain_pg_collection
public.langchain_pg_embedding
```

Our implementation creates:
```sql
-- Our approach (any schema)
my_schema.vanna_collections
my_schema.vanna_embeddings
```

### How It Works

1. **Direct PostgreSQL Connection**: Uses psycopg2 instead of relying on LangChain
2. **Schema Creation**: Automatically creates schema if it doesn't exist
3. **Proper Indexes**: Creates GIN indexes for JSONB metadata
4. **Vector Operations**: Handles pgvector operations with proper type casting

## Usage Examples

### Basic Usage

```python
from vanna.pgvector import SchemaAwarePGVectorStore
from vanna.openai import OpenAI_Chat

class CustomSchemaVanna(OpenAI_Chat, SchemaAwarePGVectorStore):
    def __init__(self, schema_name="vanna_custom"):
        OpenAI_Chat.__init__(self, config={"api_key": "sk-..."})
        SchemaAwarePGVectorStore.__init__(self, config={
            "connection_string": "postgresql://...",
            "schema": schema_name
        })

# Use it
vn = CustomSchemaVanna(schema_name="project_analytics")
```

### Multi-Environment Setup

```python
# Development
dev_vanna = CustomSchemaVanna(schema_name="vanna_dev")

# Staging
staging_vanna = CustomSchemaVanna(schema_name="vanna_staging")

# Production
prod_vanna = CustomSchemaVanna(schema_name="vanna_prod")
```

### With Our MCP Server

Update configuration to use custom schema:

```json
{
  "VANNA_SCHEMA": "vanna_bigquery",  // Now this actually works!
  "DATABASE_TYPE": "bigquery"
}
```

## Migration from Public Schema

If you have existing data in the public schema:

```sql
-- Create new schema
CREATE SCHEMA vanna_prod;

-- Copy collections
INSERT INTO vanna_prod.vanna_collections 
SELECT * FROM public.langchain_pg_collection;

-- Copy embeddings
INSERT INTO vanna_prod.vanna_embeddings
SELECT * FROM public.langchain_pg_embedding;

-- Verify and switch
```

## Comparison

### Before (Limited to Public)
- ❌ All instances share public schema
- ❌ Table name conflicts possible
- ❌ No schema-level permissions
- ❌ Messy database organization

### After (Schema Support)
- ✅ Each instance in its own schema
- ✅ Clean separation of concerns
- ✅ Schema-level access control
- ✅ Better multi-tenant support

## Technical Notes

1. **Backward Compatible**: Defaults to public schema if not specified
2. **Performance**: Same performance as original (uses same indexes)
3. **Dependencies**: Requires psycopg2 (already in requirements)
4. **Vector Type**: Handles pgvector type casting properly

## Future Enhancements

1. **Schema Migrations**: Tool to migrate between schemas
2. **Cross-Schema Queries**: Support for querying across schemas
3. **Schema Templates**: Pre-configured schemas for common use cases
4. **Auto-Cleanup**: Remove old schemas automatically

## Conclusion

By forking Vanna and implementing SchemaAwarePGVectorStore, we've removed a significant limitation. You can now:

- Use any PostgreSQL schema
- Run multiple isolated Vanna instances
- Better organize your database
- Implement proper access control

This enhancement makes Vanna more suitable for production environments where schema isolation is important.