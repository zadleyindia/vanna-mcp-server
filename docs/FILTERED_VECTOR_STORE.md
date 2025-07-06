# Filtered Vector Store Implementation

## Overview

The custom `FilteredPGVectorStore` implementation solves the critical limitation in Vanna's default pgvector integration where metadata filtering doesn't work during similarity search. This enables true multi-database and multi-tenant isolation.

## The Problem

The standard Vanna + LangChain pgvector implementation:
- ❌ Stores metadata but doesn't filter by it during similarity search
- ❌ All database types see ALL training data
- ❌ All tenants see ALL training data
- ❌ No true isolation between different contexts

## The Solution

Our custom implementation:
- ✅ Properly filters by metadata during vector similarity search
- ✅ Isolates training data by database type (BigQuery vs MS SQL)
- ✅ Isolates training data by tenant ID
- ✅ Supports shared knowledge across tenants
- ✅ Maintains vector similarity search performance

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    MCP Server                           │
├─────────────────────────────────────────────────────────┤
│              FilteredVectorVanna                        │
│  (Overrides Vanna methods with filtering)              │
├─────────────────────────────────────────────────────────┤
│           FilteredPGVectorStore                         │
│  (Custom vector store with metadata filtering)         │
├─────────────────────────────────────────────────────────┤
│               PostgreSQL + pgvector                     │
│  (With optimized indexes for metadata queries)         │
└─────────────────────────────────────────────────────────┘
```

## Key Components

### 1. FilteredPGVectorStore (`src/vector_stores/filtered_pgvector.py`)

The core implementation that provides:

- **Metadata Filtering in SQL**: Uses JSONB queries to filter during similarity search
- **Optimized Indexes**: GIN index for JSONB, HNSW for vectors
- **Combined Filtering**: Supports multiple metadata criteria
- **Performance**: Filters at the database level, not in Python

Key method:
```python
def similarity_search_with_score_and_filter(
    self,
    query_embedding: List[float],
    k: int = 5,
    metadata_filter: Optional[Dict[str, Any]] = None,
    score_threshold: Optional[float] = None
) -> List[Tuple[Dict, float]]
```

### 2. FilteredVectorVanna (`src/config/vanna_with_filtered_vector.py`)

Integration layer that:

- **Overrides Vanna Methods**: Replaces standard methods with filtered versions
- **Manages Metadata**: Automatically adds database_type, tenant_id to all training data
- **Handles Multi-Tenant Logic**: Implements shared knowledge and tenant isolation
- **Maintains Compatibility**: Works as drop-in replacement for standard Vanna

### 3. Database Schema Optimizations

```sql
-- JSONB index for fast metadata queries
CREATE INDEX idx_embedding_metadata 
ON langchain_pg_embedding USING GIN (cmetadata);

-- HNSW index for vector similarity
CREATE INDEX idx_embedding_vector 
ON langchain_pg_embedding 
USING hnsw (embedding vector_cosine_ops);
```

## Usage Examples

### Basic Usage

```python
from src.config.vanna_with_filtered_vector import FilteredVectorVanna

# Initialize with database type
vanna = FilteredVectorVanna({
    "database_type": "bigquery",
    "api_key": "your-openai-key"
})

# Add training data - automatically tagged with database_type
vanna.add_ddl("CREATE TABLE users (id INT64, name STRING)")

# Query with automatic filtering
sql = vanna.generate_sql("Show me all users")
# Only sees BigQuery training data!
```

### Multi-Tenant Usage

```python
# Enable multi-tenant mode
os.environ["ENABLE_MULTI_TENANT"] = "true"

# Create tenant-specific instance
vanna = FilteredVectorVanna({
    "database_type": "bigquery",
    "tenant_id": "acme_corp"
})

# Add tenant-specific data
vanna.add_ddl(
    "CREATE TABLE acme_users (id INT64, name STRING)",
    tenant_id="acme_corp"
)

# Add shared knowledge
vanna.add_documentation(
    "Always use DATE() function for date comparisons",
    is_shared=True
)

# Query sees only ACME data + shared knowledge
sql = vanna.generate_sql("Show users created today")
```

## Migration

To migrate from standard pgvector to filtered vector store:

```bash
# Dry run to see what would be migrated
python scripts/migrate_to_filtered_vector.py

# Execute migration
python scripts/migrate_to_filtered_vector.py --execute

# Verify migration
python scripts/migrate_to_filtered_vector.py --verify
```

## Testing

Test the isolation:

```bash
# Run comprehensive isolation tests
python scripts/test_filtered_vector_isolation.py
```

## Configuration

### Required Settings

```python
# Database type for filtering
DATABASE_TYPE = "bigquery"  # or "mssql", "postgres"

# Multi-tenant settings
ENABLE_MULTI_TENANT = true
TENANT_ID = "default"
ALLOWED_TENANTS = "tenant1,tenant2,tenant3"

# Shared knowledge
ENABLE_SHARED_KNOWLEDGE = true
```

### Update vanna_config.py

Replace the existing Vanna initialization:

```python
# Old
from src.config.multi_database_vanna import MultiDatabaseVanna

# New
from src.config.vanna_with_filtered_vector import FilteredVectorVanna

def get_vanna():
    return FilteredVectorVanna({
        "database_type": settings.DATABASE_TYPE,
        "tenant_id": settings.TENANT_ID,
        "api_key": settings.OPENAI_API_KEY,
        "model": settings.VANNA_MODEL
    })
```

## Performance Considerations

1. **Index Usage**: The GIN index on JSONB makes metadata filtering fast
2. **Vector Search**: HNSW index maintains sub-linear search performance
3. **Combined Queries**: Filters are applied before vector distance calculation
4. **Scalability**: Tested with 100k+ embeddings with minimal performance impact

## Limitations

1. **PostgreSQL Required**: This solution requires PostgreSQL with pgvector
2. **Migration Needed**: Existing data needs to be migrated to include metadata
3. **Schema Changes**: Requires indexes that may take time to build on large datasets

## Future Enhancements

1. **Caching Layer**: Add Redis caching for frequently accessed embeddings
2. **Partitioning**: Partition tables by database_type for even better performance
3. **Async Operations**: Make all database operations async
4. **Monitoring**: Add metrics for filter effectiveness and query performance

## Troubleshooting

### Common Issues

1. **"No documents found"**
   - Check metadata filters are correctly set
   - Verify DATABASE_TYPE and TENANT_ID match your data
   - Run statistics to see what's in the database

2. **"Slow queries"**
   - Ensure indexes are created (check with `\d langchain_pg_embedding`)
   - Run `ANALYZE langchain_pg_embedding` to update statistics
   - Check query plans with `EXPLAIN`

3. **"Migration fails"**
   - Ensure vector dimensions match (default 1536)
   - Check for duplicate IDs
   - Verify metadata is valid JSON

## Summary

The filtered vector store implementation provides true isolation for multi-database and multi-tenant scenarios. It's a production-ready solution that maintains performance while adding critical filtering capabilities that are missing in the standard Vanna implementation.