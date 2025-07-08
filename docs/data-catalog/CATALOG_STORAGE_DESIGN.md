# Catalog Storage Design for Vanna

## Current Problem with DDL Table

The existing `ddl` table in Vanna is designed for storing actual DDL statements (CREATE TABLE, etc.). Mixing catalog metadata into this table would:
- Confuse the purpose of the table
- Make it harder to manage different types of training data
- Complicate the embedding/retrieval process
- Break the clean separation of concerns

## Proposed Solution: Dedicated Catalog Tables

### Option 1: Single Catalog Metadata Table (Simple)

```sql
CREATE TABLE vannabq.catalog_metadata (
    id STRING DEFAULT GENERATE_UUID(),
    chunk_type STRING NOT NULL,  -- 'table_context', 'column_group', 'view_query', etc.
    chunk_content TEXT NOT NULL,  -- The actual text for embedding
    
    -- Source tracking
    source_type STRING DEFAULT 'catalog',
    source_id STRING NOT NULL,  -- table_fqdn, view_name, etc.
    source_version TIMESTAMP,  -- from catalog last_updated_ts
    catalog_hash STRING,  -- for change detection
    
    -- Metadata for filtering/retrieval
    table_fqdn STRING,  -- which table this relates to
    business_domain STRING,
    metadata JSON,  -- flexible additional metadata
    
    -- Embedding info
    embedding ARRAY<FLOAT64>,  -- vector embedding
    embedding_model STRING,
    
    -- Management
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    sync_status STRING DEFAULT 'current',  -- 'current', 'outdated', 'deleted'
    tenant_id STRING DEFAULT 'shared',  -- for multi-tenancy
    
    PRIMARY KEY (id)
)
PARTITION BY DATE(created_at)
CLUSTER BY chunk_type, table_fqdn;
```

### Option 2: Multiple Specialized Tables (Recommended)

```sql
-- 1. Table business context
CREATE TABLE vannabq.catalog_table_context (
    id STRING DEFAULT GENERATE_UUID(),
    table_fqdn STRING NOT NULL,
    context_text TEXT NOT NULL,  -- Combined business context
    
    -- Catalog source fields
    grain_description STRING,
    business_domain STRING,
    dataset_description STRING,
    owner_email STRING,
    refresh_cadence STRING,
    row_count INT64,
    
    -- Tracking
    catalog_version TIMESTAMP,
    catalog_hash STRING,
    embedding ARRAY<FLOAT64>,
    
    -- Management
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    sync_status STRING DEFAULT 'current',
    
    PRIMARY KEY (id),
    UNIQUE KEY (table_fqdn)
);

-- 2. Column metadata chunks
CREATE TABLE vannabq.catalog_column_chunks (
    id STRING DEFAULT GENERATE_UUID(),
    table_fqdn STRING NOT NULL,
    chunk_index INT64 NOT NULL,  -- which chunk group (1, 2, 3...)
    chunk_text TEXT NOT NULL,  -- Column descriptions and stats
    
    -- Metadata
    column_names ARRAY<STRING>,  -- columns in this chunk
    total_chunks INT64,  -- total chunks for this table
    
    -- Tracking
    catalog_version TIMESTAMP,
    catalog_hash STRING,
    embedding ARRAY<FLOAT64>,
    
    -- Management
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    sync_status STRING DEFAULT 'current',
    
    PRIMARY KEY (id),
    UNIQUE KEY (table_fqdn, chunk_index)
);

-- 3. View query patterns
CREATE TABLE vannabq.catalog_view_queries (
    id STRING DEFAULT GENERATE_UUID(),
    view_name STRING NOT NULL,
    query_text TEXT NOT NULL,  -- Full or chunked query
    chunk_index INT64 DEFAULT 1,
    
    -- Metadata
    view_type STRING,  -- 'standard', 'materialized'
    business_domain STRING,
    tables_referenced ARRAY<STRING>,
    query_pattern STRING,  -- 'aggregation', 'join', 'filter', etc.
    
    -- Tracking
    catalog_version TIMESTAMP,
    catalog_hash STRING,
    embedding ARRAY<FLOAT64>,
    
    -- Management
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    sync_status STRING DEFAULT 'current',
    
    PRIMARY KEY (id),
    UNIQUE KEY (view_name, chunk_index)
);

-- 4. Simplified schemas (instead of full DDL)
CREATE TABLE vannabq.catalog_schemas (
    id STRING DEFAULT GENERATE_UUID(),
    table_fqdn STRING NOT NULL,
    schema_text TEXT NOT NULL,  -- Simplified schema with descriptions
    
    -- Metadata
    column_count INT64,
    key_columns ARRAY<STRING>,
    
    -- Tracking
    catalog_version TIMESTAMP,
    catalog_hash STRING,
    embedding ARRAY<FLOAT64>,
    
    PRIMARY KEY (id),
    UNIQUE KEY (table_fqdn)
);
```

## Benefits of Separate Tables

### 1. **Clear Purpose**
- Each table has a specific type of information
- Easy to understand what's stored where
- Clean separation from actual DDL statements

### 2. **Optimized Retrieval**
```python
# Get business context for a table
context = query("SELECT * FROM catalog_table_context WHERE table_fqdn = ?")

# Get column information
columns = query("SELECT * FROM catalog_column_chunks WHERE table_fqdn = ? ORDER BY chunk_index")

# Find similar view patterns
patterns = vector_search("SELECT * FROM catalog_view_queries WHERE embedding <-> ? < 0.5")
```

### 3. **Efficient Updates**
```python
# Update only changed table contexts
UPDATE catalog_table_context 
SET context_text = ?, sync_status = 'current', updated_at = CURRENT_TIMESTAMP()
WHERE table_fqdn = ? AND catalog_hash != ?
```

### 4. **Better Embeddings**
- Each table optimized for its content type
- Can use different embedding strategies per table
- Easier to experiment with chunk sizes

### 5. **Catalog-Specific Features**
- Track catalog version per record
- Business domain filtering
- Source attribution

## Integration with Vanna

### Training Function Modifications

```python
def train_from_catalog():
    # Original DDL training (if needed)
    vanna.train(ddl=actual_ddl_statement)
    
    # New catalog training
    catalog_trainer = CatalogTrainer()
    
    # Add business context
    context = catalog_trainer.generate_table_context(table)
    store_in_catalog_table(context, 'catalog_table_context')
    
    # Add column information
    column_chunks = catalog_trainer.chunk_columns(table, columns)
    store_in_catalog_table(column_chunks, 'catalog_column_chunks')
    
    # Add view patterns
    if is_view(table):
        view_chunks = catalog_trainer.chunk_view_query(view_sql)
        store_in_catalog_table(view_chunks, 'catalog_view_queries')
```

### Query Enhancement

```python
def enhance_prompt_with_catalog(question):
    # Extract entities from question
    entities = extract_entities(question)
    
    # Get relevant catalog information
    context_parts = []
    
    # Business context
    table_context = query_catalog_table_context(entities.tables)
    context_parts.append(table_context)
    
    # Column details if needed
    if needs_column_info(question):
        column_info = query_catalog_column_chunks(entities.tables)
        context_parts.append(column_info)
    
    # Similar view patterns
    similar_views = find_similar_view_patterns(question)
    context_parts.append(similar_views)
    
    # Build enhanced prompt
    enhanced_prompt = f"""
    Question: {question}
    
    Context from Data Catalog:
    {format_context(context_parts)}
    """
    
    return enhanced_prompt
```

## Migration Strategy

### If Using Existing DDL Table

```sql
-- 1. Create new catalog tables
CREATE TABLE vannabq.catalog_table_context ...
CREATE TABLE vannabq.catalog_column_chunks ...
CREATE TABLE vannabq.catalog_view_queries ...
CREATE TABLE vannabq.catalog_schemas ...

-- 2. Migrate catalog-sourced data from ddl table
INSERT INTO vannabq.catalog_schemas
SELECT 
    GENERATE_UUID() as id,
    source_id as table_fqdn,
    ddl as schema_text,
    source_version as catalog_version,
    catalog_hash,
    embedding,
    created_at,
    'migrated' as sync_status
FROM vannabq.ddl
WHERE source_type = 'catalog';

-- 3. Remove catalog data from ddl table
DELETE FROM vannabq.ddl WHERE source_type = 'catalog';

-- 4. Update ddl table to remove catalog columns
ALTER TABLE vannabq.ddl 
DROP COLUMN source_type,
DROP COLUMN source_id,
DROP COLUMN catalog_hash;
```

## Recommended Approach

1. **Use Option 2**: Multiple specialized tables
2. **Keep DDL table clean**: Only for actual DDL statements
3. **Separate concerns**: Business context, schemas, columns, and queries in different tables
4. **Optimize for retrieval**: Each table structured for its specific use case

This approach provides:
- Better organization
- Easier maintenance
- More flexible embedding strategies
- Cleaner integration with Vanna's existing structure
- Clear separation between DDL and catalog metadata