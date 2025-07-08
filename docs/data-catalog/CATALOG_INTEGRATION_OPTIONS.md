# Catalog Integration Options for Vanna

## Overview

We have rich metadata in BigQuery's Data Catalog tables. Here are our options for using this data to train Vanna.

## Option 1: Direct BigQuery Queries (Recommended)

### Approach
Query the catalog tables directly from Vanna, no intermediate storage needed.

### Implementation
```python
async def train_from_catalog_direct():
    """Query catalog tables directly and train Vanna"""
    
    # Query 1: Get table metadata with business context
    tables_query = """
    SELECT 
        t.table_fqdn,
        t.grain_description,
        t.business_domain,
        t.row_count,
        d.description as dataset_description,
        d.owner_email
    FROM `bigquerylascoot.metadata_data_dictionary.Table_Metadata` t
    JOIN `bigquerylascoot.metadata_data_dictionary.Dataset_Metadata` d
        ON t.dataset_id = d.dataset_id
    WHERE t.status = 'In Use' 
        AND t.exists_flag = TRUE
        AND t.dataset_id = @tenant_dataset  -- Multi-tenant filtering
    """
    
    # Query 2: Get column details
    columns_query = """
    SELECT 
        c.table_id,
        c.column_name,
        c.data_type,
        c.description,
        c.distinct_count,
        c.null_count,
        c.top_5_values
    FROM `bigquerylascoot.metadata_data_dictionary.Column_Metadata` c
    WHERE c.exists_flag = TRUE
        AND c.table_id = @table_id
    """
    
    # Query 3: Get view SQL patterns
    views_query = """
    SELECT 
        v.view_name,
        v.sql_query
    FROM `bigquerylascoot.metadata_data_dictionary.View_Definitions` v
    WHERE v.dataset_id = @tenant_dataset
    """
    
    # Process and train
    for table in query_results:
        # Generate enhanced DDL
        ddl = generate_ddl_with_comments(table, columns)
        
        # Create documentation
        doc = create_business_documentation(table)
        
        # Train with metadata tracking
        vanna.train(
            ddl=ddl,
            metadata={
                'source': 'catalog',
                'source_id': table.table_fqdn,
                'catalog_version': table.last_updated_ts
            }
        )
```

### Pros
- Always current data
- No storage duplication
- Respects catalog access controls
- Can filter by tenant/domain
- Real-time updates

### Cons
- Requires BigQuery access for every training
- Slightly slower than local cache

## Option 2: JSON Export Integration

### Approach
Use the existing JSON export functionality, download and process periodically.

### Implementation
```python
async def train_from_catalog_json():
    """Download JSON export and train Vanna"""
    
    # Download latest export from Google Drive
    json_data = await download_catalog_json()
    
    # Parse and process
    catalog = json.loads(json_data)
    
    for dataset in catalog['catalog']:
        for table in dataset['tables']:
            # Generate training data
            ddl = build_ddl_from_json(table)
            doc = build_documentation_from_json(table)
            
            # Train with source tracking
            vanna.train(
                ddl=ddl,
                documentation=doc,
                metadata={
                    'source': 'catalog_json',
                    'export_timestamp': catalog['export_timestamp']
                }
            )
```

### Pros
- Offline capability
- Fast processing
- Version control possible
- Can process in batches

### Cons
- Data can be stale
- Requires Drive access
- Additional sync step

## Option 3: Hybrid Approach (Best of Both)

### Approach
Cache catalog data in Vanna's schema with periodic refresh.

### Implementation
```python
# Create cache tables in Vanna's schema
CREATE TABLE vannabq.catalog_cache AS
SELECT 
    t.*,
    d.description as dataset_description,
    CURRENT_TIMESTAMP() as cache_timestamp
FROM `bigquerylascoot.metadata_data_dictionary.Table_Metadata` t
JOIN `bigquerylascoot.metadata_data_dictionary.Dataset_Metadata` d
    ON t.dataset_id = d.dataset_id
WHERE t.status = 'In Use';

# Use cached data for training
async def train_from_catalog_cache():
    """Use cached catalog data for efficient training"""
    
    # Check cache freshness
    cache_age = await get_cache_age()
    if cache_age > timedelta(hours=24):
        await refresh_catalog_cache()
    
    # Query from cache (faster, same project)
    query = """
    SELECT * FROM vannabq.catalog_cache
    WHERE business_domain = @domain
    """
    
    # Process and train...
```

### Pros
- Fast queries (same project)
- Controlled refresh schedule
- Can add indexes/partitions
- Backup capability

### Cons
- Storage duplication
- Need to manage cache

## Option 4: Real-time Enhancement Only

### Approach
Don't pre-train from catalog, enhance queries in real-time.

### Implementation
```python
async def enhance_query_with_catalog(question: str):
    """Enhance user question with catalog context"""
    
    # Extract table references
    tables = extract_table_references(question)
    
    # Get real-time context
    context_query = """
    SELECT 
        table_id,
        grain_description,
        business_domain,
        row_count
    FROM `bigquerylascoot.metadata_data_dictionary.Table_Metadata`
    WHERE table_id IN UNNEST(@tables)
    """
    
    # Build enhanced prompt
    enhanced_prompt = build_prompt_with_context(question, context)
    
    return vanna.generate_sql(enhanced_prompt)
```

### Pros
- No pre-training needed
- Always current
- Minimal storage
- Dynamic adaptation

### Cons
- Slower response time
- Requires BigQuery access per query
- May miss patterns

## Recommended Implementation Plan

### Phase 1: Direct Query Approach
Start with Option 1 for immediate value:

```python
# New MCP tool
@mcp_server.tool()
async def vanna_sync_catalog(
    mode: str = "incremental",  # full, incremental, tables_only
    dataset_filter: Optional[str] = None,
    dry_run: bool = False
) -> Dict[str, Any]:
    """Sync training data from Data Catalog"""
    
    if mode == "full":
        # Clear existing catalog-sourced training
        await clear_catalog_training()
        
    # Get data from catalog
    tables = await query_catalog_tables(dataset_filter)
    
    trained_count = 0
    for table in tables:
        if not dry_run:
            await train_table_from_catalog(table)
        trained_count += 1
    
    return {
        'success': True,
        'mode': mode,
        'tables_processed': trained_count
    }
```

### Phase 2: Add Caching
Implement Option 3 for performance:

```python
# Cache frequently accessed metadata
CREATE TABLE vannabq.catalog_metadata_cache (
    table_fqdn STRING,
    metadata JSON,
    cache_timestamp TIMESTAMP,
    PRIMARY KEY (table_fqdn)
)
PARTITION BY DATE(cache_timestamp)
CLUSTER BY table_fqdn;
```

### Phase 3: Real-time Enhancement
Add Option 4 for dynamic context:

```python
# Modify vanna_ask to include catalog lookup
async def vanna_ask_enhanced(question: str):
    # Get base SQL
    sql = vanna.generate_sql(question)
    
    # Enhance with catalog stats
    enhanced_sql = await add_catalog_hints(sql)
    
    return enhanced_sql
```

## Storage Considerations

### What Gets Stored in Vanna

1. **Enhanced DDL** (with catalog metadata as comments)
```sql
-- Table: bigquerylascoot.sales.orders
-- Description: One row per customer order
-- Business Domain: sales
-- Owner: sales-team@company.com
-- Row Count: 1,234,567 (as of 2024-01-15)
CREATE TABLE orders (
    order_id INT64,  -- Primary key, unique order identifier
    customer_id INT64,  -- References customers.customer_id
    order_date DATE,  -- Order placement date
    ...
);
```

2. **Business Documentation**
```
Table: orders
Purpose: Tracks all customer orders with line items
Grain: One row per order
Update Frequency: Real-time
Data Quality Notes: 
- order_date is never null
- status has only 5 possible values: [pending, processing, shipped, delivered, cancelled]
```

3. **SQL Patterns** (from views)
```sql
-- Example: Monthly sales summary
SELECT 
    DATE_TRUNC(order_date, MONTH) as month,
    SUM(total_amount) as revenue,
    COUNT(DISTINCT customer_id) as unique_customers
FROM orders
WHERE status = 'delivered'
GROUP BY 1
```

### Metadata Tracking
Each training record includes:
- `source_type`: 'catalog'
- `source_id`: table FQDN
- `catalog_version`: timestamp
- `sync_status`: current/outdated

## Decision Matrix

| Approach | Speed | Freshness | Storage | Complexity | Recommended For |
|----------|-------|-----------|---------|------------|-----------------|
| Direct Query | Medium | Excellent | None | Low | Default choice |
| JSON Export | Fast | Good | Medium | Medium | Offline scenarios |
| Hybrid Cache | Fast | Good | High | High | High-volume usage |
| Real-time Only | Slow | Excellent | None | Low | Proof of concept |

## Conclusion

**Recommended Approach**: Start with **Direct Query** (Option 1) for immediate implementation, then add **Hybrid Caching** (Option 3) for performance optimization based on usage patterns.

This gives us:
1. Always-fresh catalog data
2. Efficient training updates
3. Multi-tenant support
4. Clear tracking of catalog-sourced data
5. Ability to handle catalog changes gracefully