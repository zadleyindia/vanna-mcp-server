# Vanna MCP Server - Latest Updates

## Date: 2025-01-08

### Major Changes Implemented

#### 1. **New Tool: vanna_batch_train_ddl** ✅
- Auto-generates DDL from database tables with data
- Supports both BigQuery and MS SQL Server
- Features:
  - Row count filtering (min_row_count parameter)
  - Table pattern matching (e.g., "sales_*")
  - Automatic refresh mode (removes old DDLs)
  - Dry run capability
  - Row count metadata enrichment

#### 2. **MS SQL Server Full Support** ✅
Fixed all tools to work with MS SQL Server:
- **vanna_execute**: Added full MS SQL execution support with pyodbc
- **vanna_ask**: Added SQL dialect translation (BigQuery → MS SQL)
- **vanna_train**: Fixed conditional imports and SQL validation
- Created SQL dialect translator utility for syntax conversion

#### 3. **Simplified DDL Training** ✅
- Removed manual DDL input from vanna_train tool
- DDL training now exclusively through vanna_batch_train_ddl
- More secure - no risk of malicious DDL injection
- Automated extraction ensures accuracy

#### 4. **Data Catalog Integration** ✅
- Integrated with BigQuery Data Catalog system
- Intelligent chunking for large metadata
- Separate storage tables for catalog data
- vanna_catalog_sync tool for synchronization

### Technical Improvements

#### SQL Dialect Translation
Created `src/utils/sql_dialect.py` with bidirectional translation:
- Backticks ↔ Square brackets
- LIMIT ↔ TOP syntax
- Date functions (DATE_SUB ↔ DATEADD)
- Data type mappings (STRING ↔ VARCHAR)

#### Database Routing
All tools now properly route based on DATABASE_TYPE setting:
- BigQuery uses Google Cloud client
- MS SQL uses pyodbc connection
- Consistent error handling across databases

### Updated Tool Count: 13 Tools

1. vanna_ask
2. vanna_train (simplified - no DDL)
3. vanna_suggest_questions
4. vanna_list_tenants
5. vanna_get_query_history
6. vanna_explain
7. vanna_execute
8. vanna_get_schemas
9. vanna_get_training_data
10. vanna_remove_training
11. vanna_generate_followup
12. vanna_catalog_sync
13. **vanna_batch_train_ddl** (NEW)

### Configuration Updates

#### Added Catalog Settings
```python
CATALOG_ENABLED = true
CATALOG_PROJECT = "bigquerylascoot"
CATALOG_DATASET = "metadata_data_dictionary"
CATALOG_CHUNK_SIZE = 20
CATALOG_MAX_TOKENS = 1500
```

#### MS SQL Configuration
- Separate MCP instance for MS SQL
- Full ODBC connection string support
- DATABASE_TYPE switching

### Files Added/Modified

#### New Files
- `src/tools/vanna_batch_train_ddl.py` - Batch DDL training tool
- `src/tools/vanna_catalog_sync.py` - Catalog synchronization
- `src/utils/sql_dialect.py` - SQL translation utilities
- `src/catalog_integration/` - Full catalog integration module

#### Modified Files
- `vanna_execute.py` - MS SQL execution support
- `vanna_ask.py` - Dialect translation
- `vanna_train.py` - Removed DDL, conditional imports
- `server.py` - Added new tool registrations
- `settings.py` - Catalog configuration

### Testing Scripts Created
- `test_batch_ddl.py` - Test DDL batch training
- `test_ddl_generation.py` - Validate DDL patterns
- `validate_batch_ddl.py` - Code validation
- `test_catalog_sync.py` - Catalog integration tests

### Security Enhancements
- DDL training now read-only (no manual SQL injection risk)
- Automated extraction validates table existence
- Row count filtering prevents training on empty tables
- Catalog integration respects tenant boundaries

### Next Steps for Users
1. Restart Claude Desktop to load new tools
2. Test vanna_batch_train_ddl with your datasets
3. Enable catalog integration if using BigQuery
4. Test all tools with MS SQL configuration

### Breaking Changes
- `vanna_train` no longer accepts `training_type="ddl"`
- Must use `vanna_batch_train_ddl` for schema training

## Summary
This update brings full MS SQL support, automated DDL training, and data catalog integration. The system is now more secure, easier to use, and supports multiple database platforms seamlessly.