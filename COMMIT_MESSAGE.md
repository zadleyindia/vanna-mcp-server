# Commit Message

## feat: Add MS SQL support and automated DDL training

### Major Features
- Add vanna_batch_train_ddl tool for automated DDL extraction with row count filtering
- Full MS SQL Server support across all tools (12/13 tools now support both databases)
- SQL dialect translation between BigQuery and MS SQL syntax
- Data Catalog integration for enhanced metadata (BigQuery)

### Tool Changes
- **NEW**: vanna_batch_train_ddl - Auto-generate DDLs from tables with data
- **FIXED**: vanna_execute - Now supports MS SQL query execution
- **ENHANCED**: vanna_ask - Adds SQL dialect translation for MS SQL
- **SIMPLIFIED**: vanna_train - Removed manual DDL input (security improvement)
- **NEW**: vanna_catalog_sync - Synchronize BigQuery Data Catalog

### Technical Improvements
- Add SQL dialect translator (backticks ↔ brackets, LIMIT ↔ TOP, date functions)
- Conditional imports for database-specific libraries
- Row count metadata enrichment in DDL training
- Intelligent chunking for catalog data (1500 token limit)

### Configuration
- Add catalog integration settings (9 new config options)
- Support for separate MS SQL MCP instance
- Enhanced multi-database routing

### Breaking Changes
- vanna_train no longer accepts training_type="ddl"
- DDL training must use vanna_batch_train_ddl tool

### Security
- Eliminated manual DDL injection risk
- Automated extraction validates table existence
- Catalog integration respects tenant boundaries

Tested with both BigQuery and MS SQL Server configurations.