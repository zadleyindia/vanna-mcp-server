# Vanna MCP Server - Production Ready Guide

## Overview

This guide provides comprehensive instructions for deploying and testing the production-ready Vanna MCP Server with all features:
- **Multi-Database Support**: BigQuery, PostgreSQL, MS SQL Server
- **Multi-Tenant Isolation**: Complete data separation between tenants
- **Schema Support**: Custom PostgreSQL schemas via forked Vanna
- **Metadata Filtering**: Advanced query context management

## Features Implemented

### 1. Schema Support (NEW)
- **Fork Repository**: https://github.com/zadleyindia/vanna
- **Key Enhancement**: Overcomes LangChain's public schema limitation
- **Custom Tables**: 
  - `{schema}.vanna_collections` - Collection metadata
  - `{schema}.vanna_embeddings` - Training data with vectors

### 2. Multi-Database Architecture
Each database type gets isolated:
- Separate training data
- Database-specific SQL syntax
- No cross-contamination between BigQuery/PostgreSQL/MSSQL

### 3. Multi-Tenant Support
- Complete data isolation per tenant
- Shared knowledge capability
- Tenant validation and access control

## Configuration

### Environment Variables

```bash
# Core Configuration
OPENAI_API_KEY=your-openai-key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key
SUPABASE_DB_PASSWORD=your-database-password

# Database Configuration
DATABASE_TYPE=bigquery  # or postgres, mssql
VANNA_SCHEMA=vanna_bigquery  # Custom schema name

# BigQuery Specific
BIGQUERY_PROJECT=your-project-id

# Multi-Tenant Configuration
ENABLE_MULTI_TENANT=true
TENANT_ID=default
ENABLE_SHARED_KNOWLEDGE=true
ALLOWED_TENANTS=acme_corp,xyz_inc,contoso

# Query Validation
MANDATORY_QUERY_VALIDATION=true
MAX_QUERY_RESULTS=10000
```

### Claude Desktop Configuration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "vanna-mcp": {
      "command": "python",
      "args": ["/path/to/vanna-mcp-server/server.py"],
      "env": {
        "PYTHONPATH": "/path/to/vanna-mcp-server"
      },
      "config": {
        "OPENAI_API_KEY": "your-key",
        "SUPABASE_URL": "https://your-project.supabase.co",
        "SUPABASE_KEY": "your-service-role-key",
        "SUPABASE_DB_PASSWORD": "your-db-password",
        "DATABASE_TYPE": "bigquery",
        "VANNA_SCHEMA": "vanna_bigquery",
        "BIGQUERY_PROJECT": "your-project",
        "ENABLE_MULTI_TENANT": "true",
        "TENANT_ID": "default",
        "ENABLE_SHARED_KNOWLEDGE": "true",
        "ALLOWED_TENANTS": "acme_corp,xyz_inc",
        "ACCESS_CONTROL_MODE": "whitelist",
        "ACCESS_CONTROL_DATASETS": "allowed_datasets",
        "MANDATORY_QUERY_VALIDATION": "true",
        "MAX_QUERY_RESULTS": "10000",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

## Installation

### 1. Clone Repository
```bash
git clone https://github.com/your-org/vanna-mcp-server.git
cd vanna-mcp-server
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

This will install the forked Vanna with schema support:
```
git+https://github.com/zadleyindia/vanna.git@add-metadata-support
```

### 4. Verify Installation
```bash
python -c "from vanna.pgvector.pgvector_with_schema import SchemaAwarePGVectorStore; print('Schema support ready!')"
```

## Testing

### 1. Unit Tests
Run the comprehensive test suite:

```bash
python scripts/test_production_features.py
```

This tests:
- Schema creation and isolation
- Multi-database support
- Multi-tenant data isolation
- MCP integration

### 2. Manual Testing in Claude Desktop

1. **Start Claude Desktop** with the configuration above

2. **List Available Tenants**:
   ```
   Use the vanna_list_tenants tool to show all configured tenants
   ```

3. **Train with BigQuery Data**:
   ```
   Use vanna_train to add BigQuery-specific SQL:
   - Type: sql
   - Question: "Show recent orders"
   - SQL: "SELECT * FROM orders WHERE DATE(created_at) = CURRENT_DATE()"
   - Database: bigquery
   - Tenant: acme_corp
   ```

4. **Train with PostgreSQL Data**:
   ```
   Use vanna_train to add PostgreSQL-specific SQL:
   - Type: sql
   - Question: "Show recent orders"
   - SQL: "SELECT * FROM orders WHERE created_at::date = CURRENT_DATE"
   - Database: postgres
   - Tenant: acme_corp
   ```

5. **Test Query Generation**:
   ```
   Use vanna_ask with "Show me recent orders" for tenant acme_corp
   ```

   You should get database-specific SQL based on your DATABASE_TYPE setting.

## Architecture

### Schema Isolation
```
PostgreSQL Database
├── public/                    # Default PostgreSQL schema
├── vanna_bigquery/           # BigQuery training data
│   ├── vanna_collections
│   └── vanna_embeddings
├── vanna_postgres/           # PostgreSQL training data
│   ├── vanna_collections
│   └── vanna_embeddings
└── vanna_mssql/              # MS SQL Server training data
    ├── vanna_collections
    └── vanna_embeddings
```

### Data Flow
1. **Training**: Data stored with full metadata (database_type, tenant_id, schema)
2. **Retrieval**: Filtered by metadata to ensure proper context
3. **Generation**: LLM receives only relevant examples for the target database

## Production Deployment

### 1. Database Setup
Ensure PostgreSQL has pgvector extension:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Schemas are created automatically on first use.

### 2. Security Considerations
- Use service role key for Supabase (not anon key)
- Set ALLOWED_TENANTS to restrict access
- Enable MANDATORY_QUERY_VALIDATION for SELECT-only queries
- Use environment variables, never commit secrets

### 3. Performance Optimization
- Each schema maintains its own indexes
- Vector similarity search is optimized per schema
- Connection pooling via Supabase pooler

### 4. Monitoring
- Check logs at LOG_LEVEL=INFO
- Monitor schema sizes:
  ```sql
  SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
  FROM pg_tables 
  WHERE schemaname LIKE 'vanna_%'
  ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
  ```

## Troubleshooting

### Connection Issues
1. Verify SUPABASE_DB_PASSWORD is correct (not the anon key)
2. Check if project is in correct region (ap-south-1 for India)
3. Ensure service role key has sufficient permissions

### Schema Not Created
1. Check PostgreSQL logs for permission errors
2. Verify user has CREATE SCHEMA privilege
3. Manually create schema if needed:
   ```sql
   CREATE SCHEMA IF NOT EXISTS vanna_bigquery;
   GRANT ALL ON SCHEMA vanna_bigquery TO postgres;
   ```

### Import Errors
If you get `ModuleNotFoundError` for schema support:
1. Ensure you installed from the fork: `pip show vanna`
2. Reinstall if needed: `pip install --force-reinstall git+https://github.com/zadleyindia/vanna.git@add-metadata-support`

### Multi-Tenant Issues
1. Verify ENABLE_MULTI_TENANT=true
2. Check ALLOWED_TENANTS includes your tenant
3. Ensure tenant_id is passed in all operations

## Next Steps

1. **Scale Testing**: Test with larger datasets
2. **Performance Tuning**: Optimize vector search parameters
3. **Access Control**: Implement row-level security if needed
4. **Backup Strategy**: Regular backups of schema data
5. **Migration Tools**: Scripts to migrate between schemas

## Support

For issues or questions:
1. Check logs first (LOG_LEVEL=DEBUG for detailed info)
2. Review this guide and architecture docs
3. Test with the provided test scripts
4. Contact the development team with specific error messages

## Version Information

- **Vanna Fork**: v0.7.9 with metadata support
- **MCP Server**: v1.0.0 with schema support
- **Required**: Python 3.9+, PostgreSQL 13+ with pgvector