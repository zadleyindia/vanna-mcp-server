### Available Tools

The server provides 13 comprehensive tools for SQL generation and management:

#### Core Tools

##### 1. `vanna_ask` - Convert Natural Language to SQL
```python
# Basic usage
result = vanna_ask(query="Show me total sales last month")

# Response includes SQL with proper dialect (BigQuery/MS SQL)
```

##### 2. `vanna_train` - Train with Documentation or SQL Examples
```python
# Train with documentation
vanna_train(
    training_type="documentation",
    content="Sales table contains all customer transactions"
)

# Train with SQL examples
vanna_train(
    training_type="sql",
    question="What were total sales last month?",
    content="SELECT SUM(amount) FROM sales WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 MONTH)"
)
```

##### 3. `vanna_batch_train_ddl` - Auto-Generate DDL from Database
```python
# Extract DDL for all tables with data
vanna_batch_train_ddl(
    dataset_id="sales_data",  # BigQuery dataset or MS SQL database
    min_row_count=100,        # Only tables with 100+ rows
    table_pattern="fact_*"    # Optional: filter tables
)
```

#### Query Tools

##### 4. `vanna_execute` - Execute SQL Queries
```python
# Execute query with results
result = vanna_execute(
    sql="SELECT * FROM sales",
    limit=1000,
    export_format="csv"  # Optional: csv, json, excel
)
```

##### 5. `vanna_explain` - Explain SQL in Plain English
```python
explanation = vanna_explain(
    sql="SELECT COUNT(*) FROM orders WHERE status = 'pending'",
    include_performance_tips=True
)
```

#### Discovery Tools

##### 6. `vanna_suggest_questions` - Get Question Suggestions
```python
suggestions = vanna_suggest_questions(
    context="sales analytics",
    limit=5
)
```

##### 7. `vanna_get_schemas` - View Database Structure
```python
schemas = vanna_get_schemas(
    table_filter="sales_*",
    include_metadata=True
)
```

##### 8. `vanna_generate_followup` - Generate Follow-up Questions
```python
followups = vanna_generate_followup(
    original_question="What were sales last month?",
    sql_generated="SELECT SUM(amount) FROM sales WHERE...",
    focus_area="temporal"  # temporal, comparison, aggregation
)
```

#### Management Tools

##### 9. `vanna_get_training_data` - Browse Training Data
```python
training_data = vanna_get_training_data(
    training_type="sql",  # Filter by type: ddl, documentation, sql
    search_query="sales",
    limit=50
)
```

##### 10. `vanna_remove_training` - Remove Training Data
```python
result = vanna_remove_training(
    training_ids=["id1", "id2"],
    reason="Outdated SQL syntax"
)
```

##### 11. `vanna_get_query_history` - View Query History
```python
history = vanna_get_query_history(
    limit=10,
    include_analytics=True
)
```

#### Administrative Tools

##### 12. `vanna_list_tenants` - Multi-Tenant Configuration
```python
config = vanna_list_tenants()
# Shows tenant configuration and allowed tenants
```

##### 13. `vanna_catalog_sync` - Sync Data Catalog (BigQuery)
```python
# Sync BigQuery Data Catalog metadata
result = vanna_catalog_sync(
    mode="full",  # full, incremental, status
    dataset_filter="SQL_*"
)
```

### Multi-Database Support

All tools support both **BigQuery** and **MS SQL Server**:
- Automatic SQL dialect translation
- Database-specific optimizations
- Consistent API across databases

### Security Features

- **Multi-tenant isolation**: Strict data boundaries
- **SQL injection prevention**: All queries validated
- **Audit logging**: Complete activity tracking
- **Role-based access**: Tenant-specific permissions