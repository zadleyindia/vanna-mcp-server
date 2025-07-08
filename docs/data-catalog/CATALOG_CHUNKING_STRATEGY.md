# Catalog Data Chunking Strategy for Embeddings

## Overview

The catalog contains different types of information that need different chunking strategies for optimal embedding performance.

## Data Types and Chunking Approaches

### 1. **Table-Level Metadata**

**Content**: Table descriptions, business context, ownership
**Current Size**: ~976 tables

#### Option A: One Chunk Per Table (Recommended)
```python
chunk = {
    "content": f"""
    Table: {table.table_fqdn}
    Description: {table.grain_description}
    Business Domain: {table.business_domain}
    Dataset Context: {dataset.description}
    Owner: {dataset.owner_email}
    Update Frequency: {dataset.refresh_cadence}
    Row Count: {table.row_count:,}
    """,
    "metadata": {
        "type": "table_context",
        "table_id": table.table_fqdn,
        "domain": table.business_domain
    }
}
```

**Pros**: 
- Natural boundaries
- Complete context per table
- ~976 chunks (manageable)

**Cons**:
- Some tables might have very long descriptions

#### Option B: Table + Columns Combined
```python
chunk = {
    "content": f"""
    Table: {table.table_fqdn}
    Description: {table.grain_description}
    
    Columns:
    - order_id (INT64): Unique order identifier, never null
    - customer_id (INT64): References customers.customer_id
    - order_date (DATE): Order placement date
    [... up to N columns]
    """,
    "metadata": {
        "type": "table_schema",
        "table_id": table.table_fqdn
    }
}
```

**Challenge**: Some tables have 100+ columns, making chunks too large

### 2. **Column-Level Metadata**

**Content**: Column statistics, samples, descriptions
**Volume**: ~10,000-50,000 columns across all tables

#### Option A: Batch Columns by Table
```python
# Chunk columns in groups of 10-20 per table
chunk = {
    "content": f"""
    Table: {table_name} - Column Group 1/5
    
    Columns:
    1. order_id (INT64):
       - Description: Unique order identifier
       - Distinct values: 1,234,567
       - Null count: 0
       - Top values: Not applicable (unique)
    
    2. customer_id (INT64):
       - Description: Customer reference
       - Distinct values: 45,678
       - Null count: 1,234 (0.1%)
       - Top values: [12345, 67890, 11111, 22222, 33333]
    
    [... continue for 10-20 columns]
    """,
    "metadata": {
        "type": "column_group",
        "table_id": table_name,
        "column_group": 1,
        "columns": ["order_id", "customer_id", ...]
    }
}
```

#### Option B: Important Columns Only
```python
# Only chunk columns with business descriptions or high cardinality
if column.description or column.distinct_count > 1000:
    chunk_column(column)
```

### 3. **View SQL Queries**

**Content**: Complete SQL queries for views
**Volume**: Hundreds of views, varying complexity

#### Option A: One View Per Chunk
```python
chunk = {
    "content": f"""
    View: {view.view_name}
    Type: {view.view_type}
    Domain: {table.business_domain}
    
    SQL Query:
    {view.sql_query}
    """,
    "metadata": {
        "type": "view_query",
        "view_name": view.view_name,
        "tables_used": extract_tables(view.sql_query)
    }
}
```

#### Option B: Split Complex Queries
```python
# For queries > 1000 tokens, split into logical sections
if len(tokenize(view.sql_query)) > 1000:
    sections = split_query_logical(view.sql_query)
    for i, section in enumerate(sections):
        chunk = {
            "content": f"View: {view.view_name} (Part {i+1}/{len(sections)})\n{section}",
            "metadata": {"type": "view_query_part", "part": i+1}
        }
```

### 4. **DDL Statements**

**Generated from catalog, not stored in catalog**

#### Approach: Compact DDL
```python
# Generate minimal DDL focused on structure
chunk = {
    "content": f"""
    CREATE TABLE {table.table_fqdn} (
        order_id INT64,  -- {col.description}
        customer_id INT64,  -- {col.description}
        order_date DATE,  -- {col.description}
        total_amount NUMERIC,  -- {col.description}
        [... key columns only]
    );
    -- Table: {table.grain_description}
    -- Domain: {table.business_domain}
    -- Rows: {table.row_count:,}
    """,
    "metadata": {
        "type": "ddl",
        "table_id": table.table_fqdn
    }
}
```

## Recommended Chunking Strategy

### Phase 1: Core Context (High Priority)
1. **Table Context Chunks**: One per table with business metadata
2. **Simplified DDL Chunks**: Schema with column descriptions
3. **View Pattern Chunks**: Common query patterns extracted from views

### Phase 2: Detailed Metadata (Medium Priority)
1. **Column Statistics**: Grouped by table, 20 columns per chunk
2. **Complex Views**: Full SQL for training

### Phase 3: Samples and Patterns (Low Priority)
1. **Value Examples**: Top values for categorical columns
2. **Query Patterns**: Extracted JOIN patterns, filters, aggregations

## Implementation Example

```python
class CatalogChunker:
    def __init__(self, max_chunk_size=2000):
        self.max_chunk_size = max_chunk_size
    
    def chunk_table_metadata(self, table, dataset):
        """Create comprehensive table context chunk"""
        content = self._build_table_context(table, dataset)
        
        if len(content) > self.max_chunk_size:
            # Split into overview and details
            return [
                self._create_chunk(content[:self.max_chunk_size], "table_overview", table.table_fqdn),
                self._create_chunk(content[self.max_chunk_size:], "table_details", table.table_fqdn)
            ]
        
        return [self._create_chunk(content, "table_context", table.table_fqdn)]
    
    def chunk_columns(self, table_id, columns, batch_size=20):
        """Chunk columns in batches"""
        chunks = []
        for i in range(0, len(columns), batch_size):
            batch = columns[i:i+batch_size]
            content = self._build_column_content(table_id, batch)
            chunks.append(
                self._create_chunk(
                    content, 
                    "column_group", 
                    table_id,
                    {"group": i//batch_size + 1, "columns": [c.name for c in batch]}
                )
            )
        return chunks
    
    def chunk_view_query(self, view):
        """Chunk view SQL intelligently"""
        sql_lines = view.sql_query.split('\n')
        
        if len(view.sql_query) < self.max_chunk_size:
            return [self._create_chunk(
                f"View: {view.view_name}\n\nSQL:\n{view.sql_query}",
                "view_query",
                view.view_name
            )]
        
        # Split by major clauses
        chunks = []
        current_chunk = f"View: {view.view_name}\n\n"
        
        for line in sql_lines:
            if any(clause in line.upper() for clause in ['SELECT', 'FROM', 'WHERE', 'GROUP BY', 'ORDER BY']):
                if len(current_chunk) > 100:  # Not just the header
                    chunks.append(self._create_chunk(current_chunk, "view_query_part", view.view_name))
                    current_chunk = f"View: {view.view_name} (continued)\n\n"
            
            current_chunk += line + '\n'
            
            if len(current_chunk) > self.max_chunk_size * 0.8:
                chunks.append(self._create_chunk(current_chunk, "view_query_part", view.view_name))
                current_chunk = f"View: {view.view_name} (continued)\n\n"
        
        if current_chunk:
            chunks.append(self._create_chunk(current_chunk, "view_query_part", view.view_name))
        
        return chunks
```

## Chunking Priorities for Vanna

### High-Value Chunks (Train First)
1. **Business Context**: Table descriptions with domain knowledge
2. **Schema Essentials**: DDL with column purposes
3. **Query Examples**: Simple, complete view queries

### Medium-Value Chunks
1. **Column Details**: Statistics for important columns
2. **Complex Queries**: Analytical view patterns
3. **Relationships**: Implicit FK relationships from column names

### Low-Value Chunks (Optional)
1. **Sample Data**: Actual values (may not help SQL generation)
2. **Audit Metadata**: Update timestamps, row counts
3. **Technical Details**: Partition info, clustering

## Estimated Chunk Counts

Based on catalog size:
- **Table Context**: ~976 chunks (1 per table)
- **DDL Schemas**: ~976 chunks (1 per table)
- **Column Groups**: ~2,500-5,000 chunks (depends on columns per table)
- **View Queries**: ~500-1,000 chunks (depends on complexity)
- **Hevo Queries**: ~200-500 chunks

**Total**: ~5,000-8,000 chunks for full catalog

## Optimization Strategies

### 1. **Selective Training**
```python
# Only train on tables accessed in last 90 days
if table.last_accessed > datetime.now() - timedelta(days=90):
    train_table(table)
```

### 2. **Progressive Enhancement**
```python
# Start with core tables, add more over time
priority_domains = ['sales', 'customers', 'products']
if table.business_domain in priority_domains:
    train_immediately(table)
```

### 3. **Smart Chunking**
```python
# Combine related information
chunk = {
    "content": f"""
    The {table.name} table contains {table.description}.
    It has {table.column_count} columns including {key_columns}.
    Common queries filter by {common_filters} and join with {related_tables}.
    """,
    "metadata": {"type": "table_summary", "table_id": table.table_fqdn}
}
```

## Conclusion

The recommended approach:
1. Start with one chunk per table for business context
2. Create focused DDL chunks with descriptions
3. Keep view queries as single chunks where possible
4. Group columns in batches of 20 for detailed stats
5. Monitor embedding performance and adjust chunk size as needed

This strategy balances comprehensive coverage with efficient retrieval.