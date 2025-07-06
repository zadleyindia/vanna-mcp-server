# Multi-Database Architecture for Vanna MCP

## Scenario 1: Multiple Database Types (BigQuery + MS SQL Server)

### Option A: Separate Collections in Same Vector Store
```python
# Each database gets its own collection in pgvector
collections = {
    'bigquery_ddl': 'DDL from BigQuery tables',
    'bigquery_sql': 'SQL examples for BigQuery',
    'mssql_ddl': 'DDL from MS SQL Server tables',
    'mssql_sql': 'SQL examples for MS SQL Server'
}

# When training:
vn.train(ddl=bigquery_ddl, collection_name='bigquery_ddl')
vn.train(ddl=mssql_ddl, collection_name='mssql_ddl')

# When asking questions:
# Add metadata to filter by database
vn.ask("Show total sales", filter={"database": "bigquery"})
vn.ask("Show total sales", filter={"database": "mssql"})
```

### Option B: Separate Vanna Instances
```python
# vanna_config.py
class VannaMultiDB:
    def __init__(self):
        self.instances = {
            'bigquery': VannaBigQuery(),
            'mssql': VannaMSSQL()
        }
    
    def ask(self, question, database='bigquery'):
        return self.instances[database].ask(question)
```

### Option C: Metadata-Based Filtering
```python
# Store database info in metadata
training_data = {
    "content": "CREATE TABLE sales...",
    "metadata": {
        "database_type": "bigquery",
        "project": "bigquerylascout",
        "dataset": "SQL_ZADLEY"
    }
}

# Filter during similarity search
similar = vn.get_similar(question, filter={"database_type": "bigquery"})
```

## Scenario 2: Multi-Tenant Architecture

### Option A: Schema Per Tenant
```
public/
├── tenant1_langchain_pg_collection
├── tenant1_langchain_pg_embedding
├── tenant2_langchain_pg_collection
├── tenant2_langchain_pg_embedding
└── shared_langchain_pg_collection  # Shared knowledge
```

### Option B: Collection Per Tenant
```python
# Each tenant gets collections
tenant_collections = {
    'tenant1': ['tenant1_ddl', 'tenant1_sql', 'tenant1_docs'],
    'tenant2': ['tenant2_ddl', 'tenant2_sql', 'tenant2_docs'],
    'shared': ['shared_ddl', 'shared_best_practices']
}

# Filter by tenant
vn.ask(question, collections=['tenant1_ddl', 'tenant1_sql', 'shared_ddl'])
```

### Option C: Metadata Filtering
```python
# All data in same tables, filtered by metadata
training_data = {
    "content": "CREATE TABLE ...",
    "metadata": {
        "tenant_id": "tenant1",
        "database": "bigquery",
        "access_level": "private"
    }
}

# Query with tenant filter
vn.ask(question, filter={
    "$or": [
        {"tenant_id": "tenant1"},
        {"access_level": "public"}
    ]
})
```

## Recommended Architecture for Your Use Case

### 1. Database Structure
```sql
-- Enhanced tables for multi-database/multi-tenant
CREATE TABLE training_data (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(100),
    database_type VARCHAR(50),  -- 'bigquery', 'mssql', 'postgres'
    database_name VARCHAR(255),  -- actual database/project name
    schema_name VARCHAR(255),
    table_name VARCHAR(255),
    training_data_type VARCHAR(50),
    content TEXT,
    embedding vector(1536),
    metadata JSONB,
    access_level VARCHAR(20) DEFAULT 'private',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for filtering
CREATE INDEX idx_training_tenant_db 
ON training_data(tenant_id, database_type);
```

### 2. Configuration Enhancement
```python
# settings.py
class Settings:
    # Multi-database support
    DATABASES = {
        'bigquery': {
            'type': 'bigquery',
            'project': 'bigquerylascout',
            'credentials': GOOGLE_APPLICATION_CREDENTIALS
        },
        'mssql': {
            'type': 'mssql',
            'connection_string': MSSQL_CONNECTION_STRING
        }
    }
    
    # Multi-tenant support
    TENANT_ISOLATION = True  # Enable tenant filtering
    SHARED_KNOWLEDGE_ENABLED = True  # Allow shared training data
```

### 3. Enhanced Vanna Integration
```python
class MultiDatabaseVanna(VannaBase):
    def ask(self, question: str, context: Dict[str, Any] = None):
        """
        Context can include:
        - database: 'bigquery' or 'mssql'
        - tenant_id: 'tenant1'
        - include_shared: True/False
        """
        # Build filter
        filter = {}
        if context:
            if 'database' in context:
                filter['database_type'] = context['database']
            if 'tenant_id' in context:
                filter['tenant_id'] = context['tenant_id']
        
        # Get similar questions with filter
        similar = self.get_similar_question_sql(question, filter=filter)
        
        # Generate SQL appropriate for the database type
        if context.get('database') == 'mssql':
            sql = self.generate_mssql_sql(question, similar)
        else:
            sql = self.generate_bigquery_sql(question, similar)
        
        return sql
```

## Implementation Strategy

### Phase 1: Multi-Database
1. Add database_type field to training data
2. Update training scripts to tag data with source database
3. Modify ask() to filter by database
4. Add SQL dialect conversion if needed

### Phase 2: Multi-Tenant
1. Add tenant_id to all tables
2. Implement tenant context in MCP tools
3. Add access control checks
4. Enable shared knowledge base

### Phase 3: Advanced Features
1. Cross-database JOIN detection and prevention
2. Automatic SQL dialect translation
3. Tenant-specific model fine-tuning
4. Usage tracking per tenant/database

## Best Practices

1. **Always filter at the vector search level** - don't retrieve all then filter
2. **Use metadata extensively** - it's indexed and fast
3. **Consider separate models** for very different SQL dialects
4. **Implement proper access control** - never mix tenant data
5. **Plan for scale** - collections can get large with multiple databases/tenants

## Example MCP Tool Update

```python
@mcp.tool(name="vanna_ask", description="Ask questions about your data")
async def handle_vanna_ask(
    query: str,
    database: str = "bigquery",  # New parameter
    tenant_id: Optional[str] = None,  # New parameter
    include_shared: bool = True,  # New parameter
    **kwargs
):
    context = {
        'database': database,
        'tenant_id': tenant_id or get_current_tenant(),
        'include_shared': include_shared
    }
    
    return await vanna_ask(query, context=context, **kwargs)
```