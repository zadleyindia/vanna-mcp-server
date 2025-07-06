# Vanna MCP Server - Development Context

## Project Overview
Production-ready MCP server for natural language to SQL conversion with enterprise multi-tenant support.

## Key Features
- Natural language to SQL conversion using Vanna AI
- Multi-tenant isolation with strict security boundaries  
- Cross-database support (BigQuery, PostgreSQL, MySQL, MS SQL Server)
- Shared knowledge base across tenants
- MCP protocol integration for Claude Desktop

## Architecture

### Core Components
1. **MCP Server** (`server.py`) - FastMCP-based server handling client requests
2. **Vanna Integration** (`src/config/production_vanna.py`) - Custom Vanna implementation with multi-tenant support
3. **Vector Store** (`src/vanna_schema/pgvector_with_schema.py`) - PostgreSQL pgvector for similarity search
4. **Tools** (`src/tools/`) - MCP tool implementations for ask, train, suggest, and tenant management

### Multi-Tenant Implementation
- Metadata-based filtering using PostgreSQL JSONB
- Tenant ID validation at multiple layers
- Cross-tenant query blocking with `STRICT_TENANT_ISOLATION`
- Shared knowledge support with `is_shared` flag

## Recent Improvements (2025-01-06)
- Fixed table name extraction to handle punctuation
- Enhanced cross-tenant detection with multiple validation layers
- Added pre-query blocking for explicit cross-tenant references
- Implemented DDL filtering in strict isolation mode
- Fixed training to use default tenant when not specified
- Cleaned up project structure and removed obsolete files
- Updated documentation to production standards

## Testing Status
✅ Multi-tenant isolation: 100% working
✅ Shared knowledge: Functioning correctly
✅ Cross-tenant blocking: Immediate with clear messages
✅ Training: All modes working with smart defaults

## Configuration

### Required Environment Variables
```bash
OPENAI_API_KEY=your_key
SUPABASE_URL=https://project.supabase.co
SUPABASE_KEY=anon_key
SUPABASE_DB_PASSWORD=db_password  # PostgreSQL password, not anon key!
DATABASE_TYPE=bigquery
BIGQUERY_PROJECT=project_id
```

### Multi-Tenant Settings
```bash
ENABLE_MULTI_TENANT=true
TENANT_ID=default_tenant
ALLOWED_TENANTS=tenant1,tenant2,tenant3
STRICT_TENANT_ISOLATION=true
ENABLE_SHARED_KNOWLEDGE=true
INCLUDE_LEGACY_DATA=false  # Don't include records without tenant_id
```

## Development Commands

### Running Locally
```bash
python server.py
```

### Running Tests
```bash
python -m pytest tests/
```

### Database Setup
```bash
python scripts/setup_database.py
```

## Database Structure
- Using configurable schema via `VANNA_SCHEMA` setting (defaults to "public")
- Tables: `{schema}.vanna_collections`, `{schema}.vanna_embeddings`
- Metadata stored as JSONB for efficient filtering
- Supports 1536-dimensional OpenAI embeddings
- Our fork enables custom schema support (unlike original Vanna)

## Important Implementation Details

### Tenant Isolation
1. Pre-query validation blocks explicit cross-tenant references
2. Metadata filtering ensures only tenant-specific data is used
3. Post-generation validation catches any leaks
4. Confidence reduced to 0.2 for suspicious queries (permissive mode)
5. Complete blocking in STRICT_TENANT_ISOLATION mode

### Vector Store
- Custom implementation in `src/vanna_schema/pgvector_with_schema.py`
- Handles tenant filtering at the PostgreSQL query level
- Supports both legacy data (without tenant_id) and strict filtering

### Training Data
- DDL: Table definitions (CREATE TABLE statements)
- Documentation: Business rules and context
- SQL: Question-answer pairs for learning patterns
- Shared knowledge: Available to all tenants with `is_shared=True`

## Security Considerations
- No hardcoded credentials in code
- Environment-based configuration only
- Tenant boundaries enforced at multiple layers
- Query validation before SQL generation
- Audit logging for all operations

## Next Steps
- Add comprehensive test suite
- Implement query result caching
- Add support for more embedding models
- Create admin dashboard for tenant management
- Add performance monitoring and metrics

## Troubleshooting

### Common Issues
1. **Connection errors**: Check SUPABASE_DB_PASSWORD (use PostgreSQL password)
2. **Tenant errors**: Ensure TENANT_ID is in ALLOWED_TENANTS list
3. **Cross-tenant access**: Enable STRICT_TENANT_ISOLATION for production
4. **Legacy data**: Set INCLUDE_LEGACY_DATA=true if migrating from single-tenant

### Debug Settings
```bash
LOG_LEVEL=DEBUG
DEBUG=true
```

## References
- Forked Vanna: `git+https://github.com/zadleyindia/vanna.git@add-metadata-support`
- MCP Protocol: https://modelcontextprotocol.io/
- FastMCP: https://github.com/jlowin/fastmcp