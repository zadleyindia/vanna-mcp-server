# Vanna MCP Server

A production-ready Model Context Protocol (MCP) server that provides natural language to SQL conversion using Vanna AI, with enterprise-grade multi-tenant support and cross-database compatibility.

## 🚀 Features

- **Natural Language to SQL**: Convert plain English questions to optimized SQL queries
- **Query History & Analytics**: Track all SQL queries with performance metrics and confidence scores
- **Multi-Tenant Isolation**: Enterprise-grade tenant isolation with strict security boundaries
- **Multi-Database Support**: Full support for BigQuery and MS SQL Server with automatic SQL dialect translation
- **Shared Knowledge Base**: Share common business logic across tenants while maintaining data isolation
- **MCP Integration**: Seamlessly integrates with Claude Desktop and other MCP-compatible clients
- **Production Ready**: Battle-tested with comprehensive error handling and logging

## 📋 Prerequisites

- Python 3.8+
- PostgreSQL with pgvector extension (for vector storage)
- Supabase account (for managed PostgreSQL)
- OpenAI API key (for embeddings)
- Database credentials for your target database (BigQuery, PostgreSQL, etc.)

## 🔧 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/vanna-mcp-server.git
cd vanna-mcp-server
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables

Create a `.env` file in the project root:

```bash
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_DB_PASSWORD=your_database_password

# Database Configuration
DATABASE_TYPE=bigquery  # Options: bigquery, postgresql, mysql, mssql

# BigQuery (if using BigQuery)
BIGQUERY_PROJECT=your_project_id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json

# Multi-Tenant Configuration (optional)
ENABLE_MULTI_TENANT=true
TENANT_ID=default_tenant
ALLOWED_TENANTS=tenant1,tenant2,tenant3
ENABLE_SHARED_KNOWLEDGE=true
STRICT_TENANT_ISOLATION=true
```

### 5. Initialize Database Schema

```bash
python scripts/setup_database.py
```

## 🚀 Quick Start

### Configure Claude Desktop

Add to your Claude Desktop configuration (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "vanna-mcp": {
      "command": "python",
      "args": ["/path/to/vanna-mcp-server/server.py"],
      "env": {
        "OPENAI_API_KEY": "your_openai_api_key",
        "SUPABASE_URL": "https://your-project.supabase.co",
        "SUPABASE_KEY": "your_supabase_anon_key",
        "SUPABASE_DB_PASSWORD": "your_database_password",
        "DATABASE_TYPE": "bigquery",
        "BIGQUERY_PROJECT": "your_project_id",
        "ENABLE_MULTI_TENANT": "true",
        "TENANT_ID": "default_tenant"
      }
    }
  }
}
```

## 📚 Usage

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
suggestions = vanna_suggest_questions(context="sales analytics", limit=5)
```

##### 7. `vanna_get_schemas` - View Database Structure
```python
schemas = vanna_get_schemas(table_filter="sales_*", include_metadata=True)
```

##### 8. `vanna_generate_followup` - Generate Follow-up Questions
```python
followups = vanna_generate_followup(
    original_question="What were sales last month?",
    sql_generated="SELECT SUM(amount) FROM sales WHERE..."
)
```

#### Management Tools

##### 9. `vanna_get_training_data` - Browse Training Data
```python
training_data = vanna_get_training_data(training_type="sql", search_query="sales")
```

##### 10. `vanna_remove_training` - Remove Training Data
```python
result = vanna_remove_training(training_ids=["id1", "id2"], reason="Outdated")
```

##### 11. `vanna_get_query_history` - View Query History
```python
history = vanna_get_query_history(limit=10, include_analytics=True)
```

#### Administrative Tools

##### 12. `vanna_list_tenants` - Multi-Tenant Configuration
```python
config = vanna_list_tenants()
```

##### 13. `vanna_catalog_sync` - Sync Data Catalog (BigQuery)
```python
result = vanna_catalog_sync(mode="full", dataset_filter="SQL_*")
```

## 🏢 Multi-Tenant Configuration

### Enabling Multi-Tenant Mode

Set these environment variables:

```bash
ENABLE_MULTI_TENANT=true
TENANT_ID=default_tenant_id
ALLOWED_TENANTS=tenant1,tenant2,tenant3
ENABLE_SHARED_KNOWLEDGE=true
STRICT_TENANT_ISOLATION=true  # Blocks cross-tenant queries
```

### Tenant Isolation

- Each tenant's data is completely isolated
- Queries are automatically filtered by tenant_id
- Cross-tenant access attempts are blocked with clear error messages
- Shared knowledge can be used across all tenants

### Example Multi-Tenant Setup

```python
# Tenant A trains their schema
vanna_train(
    training_type="ddl",
    content="CREATE TABLE tenant_a_sales (...)",
    tenant_id="tenant_a"
)

# Tenant B trains their schema
vanna_train(
    training_type="ddl", 
    content="CREATE TABLE tenant_b_orders (...)",
    tenant_id="tenant_b"
)

# Shared documentation for all tenants
vanna_train(
    training_type="documentation",
    content="All amounts are in USD",
    is_shared=True
)

# Tenant A can only query their data
result = vanna_ask(
    query="Show me sales",
    tenant_id="tenant_a"
)  # Returns: SELECT * FROM tenant_a_sales

# Cross-tenant access is blocked
result = vanna_ask(
    query="SELECT * FROM tenant_b_orders",
    tenant_id="tenant_a"
)  # Returns: Error - Cross-tenant access blocked
```

## 🔐 Security Features

- **Strict Tenant Isolation**: Prevents any cross-tenant data access
- **Query Validation**: All generated SQL is validated before execution
- **Metadata Filtering**: Uses PostgreSQL JSONB for efficient tenant filtering
- **Audit Logging**: All queries and access attempts are logged
- **Environment-based Configuration**: No hardcoded credentials

## 📊 Supported Databases

- **BigQuery**: Full support with schema extraction
- **PostgreSQL**: Native support with pgvector
- **MySQL**: Standard SQL support
- **MS SQL Server**: Enterprise database support

## 🛠️ Development

### Project Structure

```
vanna-mcp-server/
├── server.py              # Main MCP server
├── src/
│   ├── config/           # Configuration modules
│   ├── tools/            # MCP tool implementations
│   ├── utils/            # Utility functions
│   └── vanna_schema/     # Schema-aware implementations
├── scripts/              # Setup and utility scripts
├── tests/                # Test suite
└── docs/                 # Documentation
```

### Running Tests

```bash
python -m pytest tests/
```

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Vanna AI](https://vanna.ai/) for the SQL generation engine
- [Anthropic MCP](https://modelcontextprotocol.io/) for the protocol specification
- [Supabase](https://supabase.com/) for managed PostgreSQL with pgvector

## 📞 Support

- Create an issue for bug reports or feature requests
- Check the [documentation](docs/) for detailed guides
- Join our [Discord community](https://discord.gg/your-invite) for discussions

## 🚦 Status

![Tests](https://img.shields.io/badge/tests-passing-brightgreen)
![Multi-Tenant](https://img.shields.io/badge/multi--tenant-ready-blue)
![Production](https://img.shields.io/badge/production-ready-green)