# Production Deployment Guide

> **Last Updated**: 2025-01-06  
> **Version**: 2.0 with Filtered Vector Store and Forked Vanna

This guide explains how to deploy the Vanna MCP Server in production with multi-database and multi-tenant support.

## Overview

The Vanna MCP Server now includes:
- Custom filtered vector store for proper metadata isolation
- Forked Vanna with native metadata support
- Multi-database support (BigQuery, PostgreSQL, MS SQL Server)
- Multi-tenant isolation with tenant validation
- Production-ready configuration through MCP

## Development vs Production Configuration

### Development (using .env file)
```bash
# .env file contains all credentials
OPENAI_API_KEY=sk-...
SUPABASE_URL=https://...
DATABASE_TYPE=bigquery
ENABLE_MULTI_TENANT=true
# etc.
```

### Production (using MCP configuration)
Configuration is passed through Claude Desktop's settings file.

## Production Setup

### 1. Install the Server

```bash
# Clone the repository
git clone <your-repo-url>
cd vanna-mcp-server

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies (includes forked Vanna)
pip install -r requirements.txt

# Initialize database schema
python scripts/setup_database.py
```

### 2. Configure Claude Desktop

Edit your Claude Desktop configuration file:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

Add the Vanna MCP server configuration:

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
        "OPENAI_API_KEY": "sk-...",
        "OPENAI_MODEL": "gpt-4",
        
        "SUPABASE_URL": "https://your-project.supabase.co",
        "SUPABASE_KEY": "your-supabase-service-key",
        "SUPABASE_DB_PASSWORD": "your-database-password",
        
        "DATABASE_TYPE": "bigquery",
        "BIGQUERY_PROJECT": "your-project-id",
        "GOOGLE_APPLICATION_CREDENTIALS": "/path/to/service-account.json",
        
        "ENABLE_MULTI_TENANT": "true",
        "TENANT_ID": "default",
        "ALLOWED_TENANTS": "acme_corp,xyz_inc,test_corp",
        "ENABLE_SHARED_KNOWLEDGE": "true",
        
        "ACCESS_CONTROL_MODE": "whitelist",
        "ACCESS_CONTROL_DATASETS": "sales_data,customer_data",
        "MANDATORY_QUERY_VALIDATION": "true",
        "MAX_QUERY_RESULTS": "10000",
        
        "LOG_LEVEL": "INFO",
        "LOG_FILE": "/var/log/vanna-mcp/server.log"
      }
    }
  }
}
```

### 3. Multi-Database Deployment

For different database types, create separate MCP server instances:

#### BigQuery Instance
```json
{
  "vanna-bigquery": {
    "command": "python",
    "args": ["/path/to/vanna-mcp-server/server.py"],
    "config": {
      "DATABASE_TYPE": "bigquery",
      "BIGQUERY_PROJECT": "your-project-id",
      // ... other config
    }
  }
}
```

#### PostgreSQL Instance
```json
{
  "vanna-postgres": {
    "command": "python",
    "args": ["/path/to/vanna-mcp-server/server.py"],
    "config": {
      "DATABASE_TYPE": "postgres",
      "POSTGRES_HOST": "your-host",
      "POSTGRES_PORT": "5432",
      "POSTGRES_DATABASE": "your-db",
      "POSTGRES_USER": "your-user",
      "POSTGRES_PASSWORD": "your-password",
      // ... other config
    }
  }
}
```

#### MS SQL Server Instance
```json
{
  "vanna-mssql": {
    "command": "python",
    "args": ["/path/to/vanna-mcp-server/server.py"],
    "config": {
      "DATABASE_TYPE": "mssql",
      "MSSQL_SERVER": "your-server",
      "MSSQL_DATABASE": "your-db",
      "MSSQL_USER": "your-user", 
      "MSSQL_PASSWORD": "your-password",
      // ... other config
    }
  }
}
```

### 4. Configuration Options

#### Core Configuration
| Parameter | Description | Required | Default |
|-----------|-------------|----------|---------|
| `OPENAI_API_KEY` | OpenAI API key for embeddings and SQL generation | Yes | - |
| `OPENAI_MODEL` | Model to use (gpt-4, gpt-3.5-turbo) | No | gpt-4 |
| `SUPABASE_URL` | Supabase project URL | Yes | - |
| `SUPABASE_KEY` | Supabase service role key | Yes | - |
| `SUPABASE_DB_PASSWORD` | Database password for pgvector | Yes | - |

#### Database Configuration
| Parameter | Description | Required | Default |
|-----------|-------------|----------|---------|
| `DATABASE_TYPE` | Type: bigquery, postgres, mssql | Yes | - |
| `BIGQUERY_PROJECT` | BigQuery project ID | If bigquery | - |
| `POSTGRES_*` | PostgreSQL connection details | If postgres | - |
| `MSSQL_*` | MS SQL Server connection details | If mssql | - |

#### Multi-Tenant Configuration
| Parameter | Description | Required | Default |
|-----------|-------------|----------|---------|
| `ENABLE_MULTI_TENANT` | Enable multi-tenant support | No | false |
| `TENANT_ID` | Default tenant ID | If multi-tenant | default |
| `ALLOWED_TENANTS` | Comma-separated allowed tenants | If multi-tenant | - |
| `ENABLE_SHARED_KNOWLEDGE` | Allow shared training data | No | false |

#### Security Configuration
| Parameter | Description | Required | Default |
|-----------|-------------|----------|---------|
| `ACCESS_CONTROL_MODE` | whitelist or blacklist | No | whitelist |
| `ACCESS_CONTROL_DATASETS` | Comma-separated dataset list | No | - |
| `MANDATORY_QUERY_VALIDATION` | Validate SQL before execution | No | true |
| `MAX_QUERY_RESULTS` | Maximum rows to return | No | 10000 |

### 5. Verify Deployment

After configuration:

1. **Restart Claude Desktop**
2. **Check MCP Server Status**:
   ```
   In Claude Desktop, use: "List available tenants"
   ```
3. **Test Basic Functionality**:
   ```
   Ask: "What tables are available?"
   ```
4. **Verify Isolation**:
   ```
   Train DDL for tenant A, then query as tenant B
   Should not see tenant A's data
   ```

## Security Best Practices

### 1. Service Account Permissions

#### BigQuery
- `bigquery.dataViewer` on allowed datasets only
- `bigquery.jobUser` for query execution
- No `bigquery.admin` or write permissions

#### PostgreSQL/MS SQL
- Read-only user for data queries
- Separate user for Vanna tables with write access
- Use SSL connections

### 2. Supabase Security
- Use service role key (not anon key)
- Enable Row Level Security (RLS)
- Restrict network access
- Regular key rotation

### 3. API Key Management
- Environment-specific keys
- Regular rotation schedule
- Usage monitoring and alerts
- Never commit keys to version control

### 4. Access Control
- Always use whitelist mode in production
- Explicitly list allowed datasets/tables
- Enable query validation
- Log all queries for audit

### 5. Network Security
- Use HTTPS for all connections
- Implement IP allowlisting where possible
- Use VPN for database connections
- Enable SSL/TLS for all database connections

## Monitoring and Logging

### 1. Application Logs
```json
{
  "LOG_LEVEL": "INFO",
  "LOG_FILE": "/var/log/vanna-mcp/server.log",
  "LOG_MAX_FILE_SIZE": "100MB",
  "LOG_BACKUP_COUNT": "10"
}
```

### 2. Metrics to Monitor
- Query response times
- Error rates by tenant
- Token usage (OpenAI)
- Vector store size
- Cache hit rates

### 3. Alerts
Set up alerts for:
- Failed authentication attempts
- Unusual query patterns
- High error rates
- Resource exhaustion

## Troubleshooting

### Common Issues

1. **"Tenant or user not found"**
   - Check Supabase region (should be ap-south-1 for this project)
   - Verify database password is correct

2. **"No datasets found"**
   - Check database credentials
   - Verify service account permissions
   - Ensure DATABASE_TYPE matches your setup

3. **"Vector type casting error"**
   - This is a known limitation
   - Doesn't affect functionality, only ranking quality
   - Fixed in our custom FilteredPGVectorStore

4. **"Configuration errors found"**
   - Check all required parameters are provided
   - Verify JSON syntax in claude_desktop_config.json
   - Check logs for specific missing parameters

### Debug Mode
Enable debug logging:
```json
{
  "LOG_LEVEL": "DEBUG",
  "FASTMCP_DEBUG": "true"
}
```

## Migration Guide

### From Version 1.x (without filtered store)

1. **Update Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run Migration Script**:
   ```bash
   python scripts/migrate_to_filtered_vector.py
   ```

3. **Update Configuration**:
   - Add DATABASE_TYPE
   - Add tenant configuration if needed

### From Development to Production

1. Copy values from `.env` to MCP config
2. Remove/rename `.env` file
3. Update paths to absolute paths
4. Add production-specific settings (logging, limits)
5. Restart Claude Desktop

## Performance Tuning

### 1. Vector Store Optimization
- Regular VACUUM on PostgreSQL
- Create indexes on metadata columns
- Monitor embedding table size

### 2. Query Optimization
- Use materialized views for common queries
- Implement query result caching
- Set appropriate MAX_QUERY_RESULTS

### 3. Resource Limits
```json
{
  "MAX_QUERY_RESULTS": "10000",
  "QUERY_TIMEOUT": "30",
  "MAX_TRAINING_SIZE": "1000000",
  "EMBEDDING_BATCH_SIZE": "100"
}
```

## Backup and Recovery

### 1. Vector Store Backup
```bash
# Backup Supabase data
pg_dump -h your-db-host -U postgres -d postgres \
  -t langchain_pg_embedding -t langchain_pg_collection \
  > vanna_backup_$(date +%Y%m%d).sql
```

### 2. Configuration Backup
- Version control your claude_desktop_config.json
- Document all configuration changes
- Keep service account keys secure

## Support and Maintenance

### Regular Maintenance Tasks
1. Monitor vector store size
2. Review and clean old training data
3. Update dependencies monthly
4. Rotate API keys quarterly
5. Review access logs

### Upgrading
1. Test in development first
2. Backup vector store
3. Update one instance at a time
4. Monitor for errors
5. Have rollback plan ready

## Conclusion

The Vanna MCP Server is now production-ready with:
- True multi-database support
- Tenant isolation at the database level
- Filtered vector store implementation
- Forked Vanna with metadata support
- Comprehensive security features

Follow this guide for a secure, scalable deployment that maintains data isolation across databases and tenants.