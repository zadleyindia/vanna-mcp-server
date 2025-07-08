# Data Catalog Integration Action Plan

## Executive Summary

This document outlines the complete plan for integrating the BigQuery Data Catalog with Vanna MCP Server. Based on analysis of the actual catalog JSON (8MB, 298 tables/views across 8 datasets), we'll implement a multi-table storage strategy with intelligent chunking for optimal embedding performance.

## Goals

1. **Primary**: Enable Vanna to understand business context and table relationships from the catalog
2. **Secondary**: Improve SQL generation accuracy using column statistics and view patterns
3. **Tertiary**: Provide real-time context enhancement for natural language queries

## Data Analysis Summary

### Catalog Structure
- **8 Datasets**: Mix of raw SQL, marts, transforms, and metadata
- **298 Objects**: 229 tables, 69 views
- **Rich Metadata**: Business descriptions, owners, refresh patterns
- **Column Profiling**: Detailed statistics including nulls, cardinality, samples
- **View SQL**: Complete query definitions for pattern learning

### Key Challenges
1. **Large View Queries**: Some views contain thousands of lines of SQL
2. **Many Columns**: Tables with 60+ columns need intelligent chunking
3. **Hierarchical Data**: Dataset → Table → Column relationships must be preserved
4. **Update Tracking**: Need to detect and sync catalog changes efficiently

## Implementation Plan

### Phase 1: Foundation (Week 1)

#### 1.1 Create Catalog Storage Tables

```sql
-- Table for dataset-level context
CREATE TABLE vannabq.catalog_datasets (
    dataset_id STRING NOT NULL,
    project_id STRING NOT NULL,
    business_domain STRING,
    dataset_type STRING,
    owner_email STRING,
    description TEXT,
    source_system STRING,
    refresh_cadence STRING,
    total_tables INT64,
    total_rows INT64,
    catalog_version TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (dataset_id)
);

-- Table for table/view business context
CREATE TABLE vannabq.catalog_table_context (
    id STRING DEFAULT GENERATE_UUID(),
    table_fqdn STRING NOT NULL,
    dataset_id STRING NOT NULL,
    table_id STRING NOT NULL,
    object_type STRING,  -- 'TABLE' or 'VIEW'
    
    -- Business context
    context_chunk TEXT NOT NULL,  -- Combined business metadata
    business_domain STRING,
    grain_description TEXT,
    
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
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    
    PRIMARY KEY (id),
    UNIQUE KEY (table_fqdn)
);

-- Table for column metadata chunks
CREATE TABLE vannabq.catalog_column_chunks (
    id STRING DEFAULT GENERATE_UUID(),
    table_fqdn STRING NOT NULL,
    chunk_index INT64 NOT NULL,
    
    -- Chunk content
    column_chunk TEXT NOT NULL,  -- Formatted column information
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
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    
    PRIMARY KEY (id),
    UNIQUE KEY (table_fqdn, chunk_index)
);

-- Table for view SQL patterns
CREATE TABLE vannabq.catalog_view_queries (
    id STRING DEFAULT GENERATE_UUID(),
    view_fqdn STRING NOT NULL,
    chunk_index INT64 DEFAULT 1,
    
    -- Query content
    query_chunk TEXT NOT NULL,
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
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    
    PRIMARY KEY (id),
    UNIQUE KEY (view_fqdn, chunk_index)
);

-- Summary table for quick lookups
CREATE TABLE vannabq.catalog_summary (
    id STRING DEFAULT GENERATE_UUID(),
    summary_type STRING,  -- 'dataset_tables', 'domain_overview', etc.
    summary_key STRING,
    
    -- Content
    summary_chunk TEXT NOT NULL,
    metadata JSON,
    
    -- Tracking
    catalog_version TIMESTAMP,
    
    -- Embedding
    embedding ARRAY<FLOAT64>,
    embedding_model STRING,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    
    PRIMARY KEY (id),
    UNIQUE KEY (summary_type, summary_key)
);
```

#### 1.2 Create Chunking Service

```python
class CatalogChunker:
    def __init__(self, max_chunk_tokens=1500):
        self.max_chunk_tokens = max_chunk_tokens
        
    def chunk_table_context(self, table, dataset):
        """Create business context chunk for a table"""
        
    def chunk_columns(self, table, columns, batch_size=20):
        """Create column description chunks"""
        
    def chunk_view_query(self, view):
        """Intelligently chunk large SQL queries"""
        
    def create_dataset_summary(self, dataset):
        """Create overview chunk for dataset"""
```

#### 1.3 Create Sync Tool

```python
@mcp_server.tool()
async def vanna_catalog_sync(
    source: str = "bigquery",  # or "json"
    mode: str = "incremental",  # or "full"
    dataset_filter: Optional[str] = None,
    dry_run: bool = False,
    chunk_size: int = 20  # columns per chunk
) -> Dict[str, Any]:
    """Sync Data Catalog with Vanna"""
```

### Phase 2: Core Integration (Week 2)

#### 2.1 Implement Catalog Querying

```python
class CatalogQuerier:
    def __init__(self):
        self.bq_client = bigquery.Client()
        
    async def fetch_catalog_data(self, dataset_filter=None):
        """Query catalog tables from BigQuery"""
        
    async def fetch_from_json(self, json_path):
        """Alternative: Load from exported JSON"""
```

#### 2.2 Implement Chunking Logic

```python
def create_table_context_chunk(table, dataset):
    """Generate comprehensive table context"""
    return f"""
Table: {table['table_fqdn']}
Type: {table['object_type']}
Description: {table.get('grain_description', 'No description available')}

Dataset Context:
- Dataset: {dataset['dataset_id']}
- Purpose: {dataset.get('description', '')}
- Domain: {dataset.get('business_domain', 'General')}
- Owner: {dataset.get('owner_email', '')}
- Source: {dataset.get('source_system', '')}
- Updates: {dataset.get('refresh_cadence', '')}

Table Statistics:
- Rows: {table.get('row_count_last_audit', 0):,}
- Columns: {table.get('column_count', 0)}
- Last Updated: {format_timestamp(table.get('last_updated_ts'))}
"""

def create_column_chunks(table, columns, chunk_size=20):
    """Create manageable column description chunks"""
    chunks = []
    
    for i in range(0, len(columns), chunk_size):
        column_batch = columns[i:i+chunk_size]
        chunk_text = f"Table: {table['table_fqdn']} - Columns {i+1} to {i+len(column_batch)}\n\n"
        
        for col in column_batch:
            chunk_text += format_column_info(col)
        
        chunks.append(chunk_text)
    
    return chunks

def chunk_view_query(view):
    """Smart chunking for SQL queries"""
    sql = view.get('query', '')
    
    if len(sql) < 2000:  # Small query, keep as one chunk
        return [format_view_context(view, sql)]
    
    # Split by major clauses
    return split_sql_intelligently(sql, view)
```

#### 2.3 Implement Storage Logic

```python
class CatalogStorage:
    def __init__(self, vanna_instance):
        self.vanna = vanna_instance
        self.bq_client = bigquery.Client()
        
    async def store_table_context(self, table_chunk, metadata):
        """Store table business context with embedding"""
        
    async def store_column_chunks(self, column_chunks, metadata):
        """Store column information chunks"""
        
    async def store_view_query(self, view_chunks, metadata):
        """Store view SQL patterns"""
        
    async def update_embeddings(self, table_name):
        """Generate and store embeddings for chunks"""
```

### Phase 3: Enhancement Features (Week 3)

#### 3.1 Real-time Context Retrieval

```python
async def enhance_prompt_with_catalog(question: str, tenant_id: str = None):
    """Enhance user question with catalog context"""
    
    # Extract mentioned tables
    entities = extract_entities(question)
    
    # Get relevant context
    context_parts = []
    
    # 1. Table business context
    table_contexts = await get_table_contexts(entities.tables)
    context_parts.extend(table_contexts)
    
    # 2. Column details if needed
    if needs_column_details(question):
        column_info = await get_column_info(entities.tables)
        context_parts.extend(column_info)
    
    # 3. Similar query patterns
    similar_patterns = await find_similar_queries(question)
    context_parts.extend(similar_patterns)
    
    return build_enhanced_prompt(question, context_parts)
```

#### 3.2 Change Detection

```python
class CatalogChangeDetector:
    async def detect_changes(self):
        """Compare catalog with stored data"""
        
    async def generate_sync_plan(self, changes):
        """Create efficient update plan"""
        
    async def apply_changes(self, sync_plan):
        """Update only changed items"""
```

#### 3.3 Query Pattern Learning

```python
class ViewPatternAnalyzer:
    def extract_patterns(self, view_sql):
        """Extract reusable SQL patterns"""
        
    def categorize_query(self, sql):
        """Classify query type for better retrieval"""
        
    def find_similar_patterns(self, user_question):
        """Find relevant view patterns"""
```

### Phase 4: Production Readiness (Week 4)

#### 4.1 Monitoring & Metrics

```python
class CatalogSyncMonitor:
    async def check_sync_health(self):
        """Monitor catalog sync status"""
        
    async def report_metrics(self):
        """Track usage and performance"""
```

#### 4.2 Performance Optimization

- Implement caching for frequently accessed metadata
- Batch embedding generation
- Optimize chunk sizes based on retrieval performance
- Add indexes for common query patterns

#### 4.3 Testing & Validation

- Unit tests for chunking logic
- Integration tests with sample catalog data
- Performance benchmarks
- End-to-end testing with real queries

## Success Metrics

### Immediate (Week 1-2)
- ✓ Catalog tables created
- ✓ Basic sync tool functional
- ✓ 100+ tables synced with context
- ✓ Chunking produces <2000 token chunks

### Short-term (Week 3-4)
- ✓ Real-time context enhancement working
- ✓ Query accuracy improved by 30%+
- ✓ View patterns being used
- ✓ Change detection operational

### Long-term (Month 2+)
- ✓ Full catalog synced (298 tables)
- ✓ Automated sync running daily
- ✓ 50%+ improvement in SQL quality
- ✓ User satisfaction increased

## Risk Mitigation

### Risk 1: Large Data Volume
- **Mitigation**: Implement progressive sync, start with high-value tables

### Risk 2: Embedding Cost
- **Mitigation**: Batch processing, caching, selective embedding

### Risk 3: Sync Complexity
- **Mitigation**: Robust error handling, detailed logging, dry-run mode

### Risk 4: Query Performance
- **Mitigation**: Proper indexing, connection pooling, async operations

## Next Steps

1. **Review & Approve**: Confirm this plan meets requirements
2. **Create Tables**: Set up BigQuery tables for catalog storage
3. **Implement Phase 1**: Build foundation components
4. **Test with Sample**: Use provided JSON for initial testing
5. **Iterate**: Refine based on results

## Conclusion

This plan provides a structured approach to integrating the Data Catalog with Vanna, leveraging the rich metadata to significantly improve SQL generation quality. The phased approach ensures quick wins while building toward a comprehensive solution.