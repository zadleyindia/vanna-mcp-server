# Changelog

All notable changes to the Vanna MCP Server project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-01-06

### Added
- Initial production release
- Natural language to SQL conversion using Vanna AI
- Multi-tenant support with strict isolation
- Cross-database compatibility (BigQuery, PostgreSQL, MySQL, MS SQL Server)
- Shared knowledge base functionality
- MCP protocol integration for Claude Desktop
- Comprehensive security features including:
  - Pre-query validation for cross-tenant references
  - Metadata-based tenant filtering
  - Post-generation validation
  - Configurable strict isolation mode
- Four main MCP tools:
  - `vanna_ask` - Convert natural language to SQL
  - `vanna_train` - Train the model with DDL, documentation, or SQL examples
  - `vanna_suggest_questions` - Get question suggestions
  - `vanna_list_tenants` - List tenant configuration
- Production-ready features:
  - Environment-based configuration
  - Comprehensive error handling
  - Detailed logging
  - Query validation
  - Audit trails

### Fixed
- Table name extraction now properly handles punctuation
- Training uses default tenant when not specified
- Cross-tenant query blocking works in all scenarios
- Proper PostgreSQL password handling (not anon key)

### Security
- No hardcoded credentials in codebase
- All sensitive configuration via environment variables
- Tenant boundaries enforced at multiple layers
- Query validation before SQL generation

### Documentation
- Comprehensive README with installation and usage instructions
- CLAUDE.md for development context
- Setup template for secure configuration
- Architecture and implementation details

## [0.9.0] - 2024-12-31 (Pre-release)

### Added
- Initial implementation of multi-tenant support
- Basic Vanna integration
- MCP server setup
- Database schema for vector storage

### Known Issues
- Cross-tenant isolation not fully working
- Training requires explicit tenant_id
- Some test scripts included in distribution