# Multi-Database and Multi-Tenant Architecture for Vanna MCP Server

## Overview

This document outlines the architecture for supporting multiple database types (BigQuery, MS SQL Server, etc.) and multiple tenants within the Vanna MCP Server. The solution uses metadata filtering with all data stored in PostgreSQL's public schema.

## Core Architecture Decisions

### 1. Schema Strategy
- **Decision**: Use PostgreSQL `public` schema for all tables
- **Rationale**: Vanna's LangChain pgvector implementation is hardcoded to use public schema
- **Impact**: Simplified architecture, no schema switching complexity

### 2. Multi-Database Support
- **Decision**: Deploy separate MCP server instances per database type
- **Implementation**:
  - `vanna-bigquery` - MCP server for BigQuery
  - `vanna-mssql` - MCP server for MS SQL Server
  - `vanna-postgres` - MCP server for PostgreSQL (future)
- **Benefits**: 
  - Clean separation of concerns
  - Database-specific optimizations possible
  - Simpler configuration management

### 3. Multi-Tenant Support
- **Decision**: Use metadata filtering within each database instance
- **Implementation**: Store tenant information in JSONB metadata column
- **Benefits**:
  - Efficient vector similarity search
  - Flexible tenant isolation
  - Support for shared knowledge

## Configuration Parameters

### Environment Variables / MCP Config

```python
# Database Configuration
DATABASE_TYPE = "bigquery"          # Required: bigquery, mssql, postgres, mysql
TENANT_ID = "default"               # Default tenant identifier

# Multi-Tenant Configuration  
ENABLE_MULTI_TENANT = "false"       # Enable/disable multi-tenant mode
ENABLE_SHARED_KNOWLEDGE = "true"    # Allow shared training data across tenants
ALLOWED_TENANTS = ""                # Comma-separated list of allowed tenants (empty = all allowed)

# Deprecated (kept for compatibility)
VANNA_SCHEMA = "public"             # Always public, not configurable

# Other Required Configuration
SUPABASE_URL = "https://xxx.supabase.co"
SUPABASE_DB_PASSWORD = "password"   # PostgreSQL password
OPENAI_API_KEY = "sk-..."
BIGQUERY_PROJECT = "project-id"     # For BigQuery instance
MSSQL_CONNECTION_STRING = "..."     # For MS SQL instance
```

## Metadata Structure

### Single-Tenant Mode (ENABLE_MULTI_TENANT=false)

```json
{
  "database_type": "bigquery",
  "database_name": "bigquerylascout", 
  "schema_name": "SQL_ZADLEY",
  "table_name": "sales",
  "timestamp": "2025-01-05 10:30:00"
}
```

### Multi-Tenant Mode (ENABLE_MULTI_TENANT=true)

```json
{
  "database_type": "bigquery",
  "tenant_id": "customer1",
  "database_name": "bigquerylascout",
  "schema_name": "customer1_data", 
  "table_name": "sales",
  "timestamp": "2025-01-05 10:30:00"
}
```

### Shared Knowledge Entry

```json
{
  "database_type": "bigquery",
  "tenant_id": "shared",
  "database_name": "bigquerylascout",
  "content_type": "best_practice",
  "timestamp": "2025-01-05 10:30:00"
}
```

## Tool Implementations

### Enhanced vanna_ask Tool

```python
@mcp.tool(name="vanna_ask")
async def handle_vanna_ask(
    query: str,
    tenant_id: Optional[str] = None,      # Override default tenant
    include_shared: Optional[bool] = None, # Override shared knowledge setting
    include_explanation: bool = True,
    include_confidence: bool = True,
    auto_train: bool = False
) -> Dict[str, Any]:
    """
    Convert natural language to SQL with multi-tenant support.
    
    Args:
        query: Natural language question
        tenant_id: Override default tenant (for multi-tenant mode)
        include_shared: Override shared knowledge setting
        include_explanation: Include plain English explanation
        include_confidence: Include confidence score
        auto_train: Automatically train on successful queries
    """
    # Determine actual tenant to use
    if settings.ENABLE_MULTI_TENANT:
        actual_tenant = tenant_id or settings.TENANT_ID
        use_shared = include_shared if include_shared is not None else settings.ENABLE_SHARED_KNOWLEDGE
    else:
        actual_tenant = None  # No tenant filtering in single-tenant mode
        use_shared = False
```

### Enhanced vanna_train Tool

```python
@mcp.tool(name="vanna_train")
async def handle_vanna_train(
    training_type: str,  # ddl, sql, documentation
    content: str,
    question: Optional[str] = None,
    is_shared: bool = False,  # Mark as shared knowledge
    metadata: Optional[Dict[str, Any]] = None,
    validate: bool = True
) -> Dict[str, Any]:
    """
    Train Vanna with new data.
    
    Args:
        training_type: Type of training data
        content: The training content
        question: For SQL training, the natural language question
        is_shared: Mark this as shared knowledge for all tenants
        metadata: Additional metadata to store
        validate: Whether to validate the training data
    """
    # Determine tenant_id
    if settings.ENABLE_MULTI_TENANT:
        tenant_id = "shared" if is_shared else settings.TENANT_ID
    else:
        tenant_id = None  # No tenant in single-tenant mode
```

## Query Filtering Logic

### Single-Tenant Mode
```sql
-- Only filter by database type
WHERE metadata->>'database_type' = 'bigquery'
```

### Multi-Tenant Mode (without shared knowledge)
```sql
-- Filter by database type AND tenant
WHERE metadata->>'database_type' = 'bigquery'
  AND metadata->>'tenant_id' = 'customer1'
```

### Multi-Tenant Mode (with shared knowledge)
```sql
-- Filter by database type AND (tenant OR shared)
WHERE metadata->>'database_type' = 'bigquery'
  AND (metadata->>'tenant_id' = 'customer1' 
       OR metadata->>'tenant_id' = 'shared')
```

## Deployment Examples

### Example 1: Single-Tenant BigQuery Setup

**Claude Desktop Config** (settings.json):
```json
{
  "mcpServers": {
    "vanna-bigquery": {
      "command": "python",
      "args": ["/path/to/vanna-mcp-server/server.py"],
      "config": {
        "DATABASE_TYPE": "bigquery",
        "ENABLE_MULTI_TENANT": "false",
        "BIGQUERY_PROJECT": "my-bigquery-project",
        "SUPABASE_URL": "https://xxx.supabase.co",
        "SUPABASE_DB_PASSWORD": "password",
        "OPENAI_API_KEY": "sk-..."
      }
    }
  }
}
```

### Example 2: Multi-Tenant Multi-Database Setup

**BigQuery Instance** (claude_desktop_config.json):
```json
{
  "mcpServers": {
    "vanna-bigquery": {
      "command": "python",
      "args": ["/path/to/vanna-mcp-server/server.py"],
      "config": {
        "DATABASE_TYPE": "bigquery",
        "TENANT_ID": "tenant1",
        "ENABLE_MULTI_TENANT": "true",
        "ENABLE_SHARED_KNOWLEDGE": "true",
        "BIGQUERY_PROJECT": "bigquerylascout",
        "SUPABASE_URL": "https://xxx.supabase.co",
        "SUPABASE_DB_PASSWORD": "password",
        "OPENAI_API_KEY": "sk-..."
      }
    }
  }
}
```

**MS SQL Instance** (separate config):
```json
{
  "mcpServers": {
    "vanna-mssql": {
      "command": "python", 
      "args": ["/path/to/vanna-mcp-server/server.py"],
      "config": {
        "DATABASE_TYPE": "mssql",
        "TENANT_ID": "tenant1",
        "ENABLE_MULTI_TENANT": "true",
        "ENABLE_SHARED_KNOWLEDGE": "true",
        "MSSQL_CONNECTION_STRING": "Server=...;Database=...;",
        "SUPABASE_URL": "https://xxx.supabase.co",
        "SUPABASE_DB_PASSWORD": "password",
        "OPENAI_API_KEY": "sk-..."
      }
    }
  }
}
```

## Usage Examples

### Single-Tenant Usage
```python
# Ask a question (no tenant needed)
result = await vanna_ask(
    query="Show me total sales by month"
)

# Train with DDL
await vanna_train(
    training_type="ddl",
    content="CREATE TABLE sales (id INT64, amount NUMERIC)"
)
```

### Multi-Tenant Usage
```python
# Ask for default tenant (zaldey)
result = await vanna_ask(
    query="Show me total sales"
)

# Ask for different tenant (singla) 
result = await vanna_ask(
    query="Show me total sales",
    tenant_id="singla"
)

# Train shared knowledge
await vanna_train(
    training_type="documentation",
    content="Best practices for BigQuery performance",
    is_shared=True  # Available to all tenants
)

# Train tenant-specific data
await vanna_train(
    training_type="ddl",
    content="CREATE TABLE tenant1.sales (...)",
    is_shared=False  # Only for current tenant
)
```

## Implementation Phases

### Phase 1: Core Multi-Database Support
- [ ] Update settings.py with new configuration parameters
- [ ] Modify vanna_config.py to use MultiDatabaseVanna class
- [ ] Update metadata structure in training and query methods
- [ ] Add database_type filtering to all queries

### Phase 2: Multi-Tenant Support
- [ ] Add tenant_id parameter to tools
- [ ] Implement metadata filtering for tenant isolation
- [ ] Add shared knowledge support
- [ ] Update all training methods to include tenant metadata

### Phase 3: Tool Enhancements
- [ ] Add tenant_id override to vanna_ask
- [ ] Add is_shared flag to vanna_train
- [ ] Create vanna_list_tenants tool
- [ ] Add tenant validation and access control

### Phase 4: Testing and Documentation
- [ ] Test single-tenant mode
- [ ] Test multi-tenant with shared knowledge
- [ ] Test tenant isolation
- [ ] Update user documentation

## Tenant Validation

### Configuration
Use `ALLOWED_TENANTS` to restrict which tenants can be used:

```bash
# No restrictions (default)
ALLOWED_TENANTS=""

# Specific tenants only
ALLOWED_TENANTS="zaldey,singla,customer1"

# Single tenant lock
ALLOWED_TENANTS="production"
```

### Validation Rules
1. If `ALLOWED_TENANTS` is empty, all tenant IDs are allowed
2. If `ALLOWED_TENANTS` is set, only listed tenants can be used
3. The default `TENANT_ID` must be in the allowed list (if set)
4. Special tenant `"shared"` is always allowed when `ENABLE_SHARED_KNOWLEDGE=true`
5. Validation only applies in multi-tenant mode

### Error Handling
When an invalid tenant is used:
```json
{
  "error": "Tenant 'invalid_tenant' is not allowed",
  "allowed_tenants": ["zaldey", "singla", "customer1"],
  "suggestions": ["Use one of the allowed tenants", "Check your tenant configuration"]
}
```

## Security Considerations

1. **Tenant Isolation**: Queries must strictly filter by tenant_id to prevent data leakage
2. **Tenant Validation**: Use ALLOWED_TENANTS to prevent unauthorized tenant access
3. **Shared Knowledge**: Only non-sensitive, general best practices should be marked as shared
4. **Configuration**: Database credentials must be properly secured in MCP config
5. **Validation**: Always validate tenant_id before operations

## Future Enhancements

1. **Cross-Database Queries**: Detect and prevent queries across database types
2. **SQL Dialect Translation**: Automatic conversion between SQL dialects
3. **Tenant Usage Tracking**: Monitor usage per tenant for billing/quotas
4. **Dynamic Tenant Creation**: API to create new tenants on-demand
5. **Tenant-Specific Models**: Fine-tune models per tenant for better accuracy