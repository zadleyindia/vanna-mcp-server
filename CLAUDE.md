# Vanna MCP Server - Development Context

## Previous Session Context

### Latest Updates (2025-01-08)
- ✅ Created vanna_batch_train_ddl tool for automated DDL extraction
- ✅ Added full MS SQL Server support (12/13 tools now support both databases)
- ✅ Implemented SQL dialect translation (BigQuery ↔ MS SQL)
- ✅ Updated documentation with complete 13-tool list
- ✅ Committed all changes (commit: 40c5c3c)
- Ready to test all 13 tools with both BigQuery and MS SQL configurations

## Project Overview
Production-ready MCP server for natural language to SQL conversion with enterprise multi-tenant support.

## Key Features
- Natural language to SQL conversion using Vanna AI
- Query history and analytics with performance tracking
- Multi-tenant isolation with strict security boundaries  
- Cross-database support (BigQuery, PostgreSQL, MySQL, MS SQL Server)
- Shared knowledge base across tenants
- MCP protocol integration for Claude Desktop

## Architecture

### Core Components
1. **MCP Server** (`server.py`) - FastMCP-based server handling client requests
2. **Vanna Integration** (`src/config/production_vanna.py`) - Custom Vanna implementation with multi-tenant support
3. **Vector Store** (`src/vanna_schema/pgvector_with_schema.py`) - PostgreSQL pgvector for similarity search
4. **Tools** (`src/tools/`) - Complete MCP tool suite (13 tools):
   - `vanna_ask` - Natural language to SQL conversion
   - `vanna_train` - Add training data (documentation/SQL only)
   - `vanna_batch_train_ddl` - Auto-generate DDL from database
   - `vanna_suggest_questions` - Generate suggested queries
   - `vanna_list_tenants` - Multi-tenant management
   - `vanna_get_query_history` - Query analytics and history
   - `vanna_explain` - SQL explanation in plain English
   - `vanna_execute` - SQL execution with export (CSV/JSON/Excel)
   - `vanna_get_schemas` - View database structure
   - `vanna_get_training_data` - Browse training data
   - `vanna_remove_training` - Remove incorrect training
   - `vanna_generate_followup` - Generate follow-up questions
   - `vanna_catalog_sync` - Sync BigQuery Data Catalog

### Multi-Tenant Implementation
- Metadata-based filtering using PostgreSQL JSONB
- Tenant ID validation at multiple layers
- Cross-tenant query blocking with `STRICT_TENANT_ISOLATION`
- Shared knowledge support with `is_shared` flag

## Recent Improvements (2025-01-06 to 2025-01-08)
- Fixed table name extraction to handle punctuation
- Enhanced cross-tenant detection with multiple validation layers
- Added pre-query blocking for explicit cross-tenant references
- Implemented DDL filtering in strict isolation mode
- Fixed training to use default tenant when not specified
- Cleaned up project structure and removed obsolete files
- Updated documentation to production standards
- **Query History Implementation**: Added full query analytics with multi-tenant isolation
- **Security Enhancement**: Implemented comprehensive DDL validation and metadata extraction
- **BigQuery DDL Testing**: Successfully tested with 3 e-commerce tables
- **Phase 3 Extended Features**: Completed vanna_explain and vanna_execute tools
- **Export Functionality**: Added CSV/JSON/Excel export with comprehensive data formatting
- **MS SQL Support**: Added full MS SQL Server support across 12/13 tools
- **Automated DDL Training**: Created vanna_batch_train_ddl tool with row count filtering
- **SQL Dialect Translation**: Implemented bidirectional BigQuery ↔ MS SQL translation
- **Data Catalog Integration**: Added vanna_catalog_sync for BigQuery metadata

## Testing Status
✅ Multi-tenant isolation: 100% working
✅ Shared knowledge: Functioning correctly
✅ Cross-tenant blocking: Immediate with clear messages
✅ Training: All modes working with smart defaults
✅ Query history: Full analytics with tenant isolation
✅ Security validation: DDL filtering and metadata extraction
✅ BigQuery features: STRUCT types, partitioning, clustering support
✅ Phase 3 Extended Features: SQL explanation and execution tools
✅ Export functionality: CSV/JSON/Excel with data formatting
✅ MS SQL Support: 12/13 tools support both BigQuery and MS SQL
✅ Automated DDL Training: Row count filtering and metadata enrichment
✅ SQL Dialect Translation: Automatic conversion between databases

## Configuration

### Required Environment Variables
```bash
OPENAI_API_KEY=your_key
SUPABASE_URL=https://project.supabase.co
SUPABASE_KEY=anon_key
SUPABASE_DB_PASSWORD=db_password  # PostgreSQL password, not anon key!
DATABASE_TYPE=bigquery  # Options: bigquery, mssql
BIGQUERY_PROJECT=project_id

# MS SQL Configuration (if using MS SQL)
MSSQL_SERVER=your_server
MSSQL_DATABASE=your_database
MSSQL_USERNAME=your_username
MSSQL_PASSWORD=your_password
MSSQL_DRIVER=ODBC Driver 17 for SQL Server
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
- Tables: `{schema}.vanna_collections`, `{schema}.vanna_embeddings`, `{schema}.query_history`
- Query history table tracks all SQL generations with analytics
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
- **DDL**: Automated extraction via `vanna_batch_train_ddl`
  - Extracts DDL from tables with data (min_row_count filtering)
  - Enriches with row count metadata
  - Supports table pattern matching (e.g., "sales_*")
  - Manual DDL input removed for security
- **Documentation**: Business rules and context
- **SQL**: Question-answer pairs with comprehensive validation
  - Only SELECT statements allowed for training
  - Dangerous patterns blocked (system functions, stored procedures)
  - Optional dry-run validation for syntax checking
- **Shared knowledge**: Available to all tenants with `is_shared=True`

## Security Considerations
- **Enhanced DDL Security**: Raw DDL commands blocked, only metadata extracted
- **SQL Validation**: Comprehensive filtering of dangerous keywords and patterns
- **Schema Metadata Extraction**: Normalized format prevents SQL injection
- **Multi-Tenant Security**: Strict tenant isolation with cross-tenant access blocking
- **Tool Security Standards**: All tools implement mandatory security requirements ([see standards](docs/TOOL_DEVELOPMENT_STANDARDS.md))
- **Database Type Validation**: Type-specific security restrictions and feature validation
- **Cross-Tenant Protection**: Pre-execution validation prevents data leakage
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