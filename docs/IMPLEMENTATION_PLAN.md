# Implementation Plan: Multi-Database and Multi-Tenant Support

## Overview
This document outlines the step-by-step implementation plan for adding multi-database and multi-tenant support to the Vanna MCP Server.

## Current State
- Single database support (BigQuery only)
- No tenant isolation
- All data stored in public schema
- Basic vanna_ask and vanna_train tools

## Target State
- Multiple database type support (BigQuery, MS SQL, etc.)
- Multi-tenant with metadata filtering
- Shared knowledge capability
- Enhanced tools with tenant parameters

## Implementation Tasks

### Phase 1: Configuration Updates (Priority: High)

#### 1.1 Update settings.py
- [x] Add DATABASE_TYPE parameter
- [x] Add TENANT_ID parameter  
- [x] Add ENABLE_MULTI_TENANT parameter
- [x] Add ENABLE_SHARED_KNOWLEDGE parameter
- [ ] Add MSSQL configuration parameters
- [ ] Remove VANNA_SCHEMA usage (deprecated)

#### 1.2 Update MultiDatabaseVanna class
- [x] Basic class structure exists
- [ ] Fix import issues (missing datetime import)
- [ ] Implement proper metadata filtering in ask()
- [ ] Override get_similar_question_sql for filtering
- [ ] Add proper tenant validation

### Phase 2: Tool Enhancements (Priority: High)

#### 2.1 Update vanna_ask tool
- [ ] Add tenant_id parameter
- [ ] Add include_shared parameter
- [ ] Pass parameters to MultiDatabaseVanna
- [ ] Update tool description

#### 2.2 Update vanna_train tool  
- [ ] Add is_shared parameter
- [ ] Implement tenant_id logic (shared vs tenant-specific)
- [ ] Update metadata structure
- [ ] Add validation for shared content

#### 2.3 Update vanna_train.py implementation
- [ ] Use MultiDatabaseVanna instead of base Vanna
- [ ] Add metadata enrichment
- [ ] Handle is_shared flag properly

### Phase 3: Core Implementation (Priority: High)

#### 3.1 Fix MultiDatabaseVanna implementation
- [ ] Add missing imports
- [ ] Implement proper pgvector filtering
- [ ] Override necessary Vanna methods
- [ ] Add logging for debugging

#### 3.2 Update vanna_config.py
- [ ] Use MultiDatabaseVanna instead of MyVanna
- [ ] Pass configuration properly
- [ ] Handle initialization errors

### Phase 4: Database-Specific Support (Priority: Medium)

#### 4.1 BigQuery Integration
- [ ] Validate existing BigQuery support
- [ ] Add BigQuery-specific metadata
- [ ] Test with current setup

#### 4.2 MS SQL Server Support
- [ ] Add MSSQL connection configuration
- [ ] Implement SQL dialect differences
- [ ] Add MSSQL-specific training examples

### Phase 5: Testing Scripts (Priority: Medium)

#### 5.1 Create test scripts
- [ ] test_single_tenant.py - Test single-tenant mode
- [ ] test_multi_tenant.py - Test multi-tenant isolation
- [ ] test_shared_knowledge.py - Test shared knowledge
- [ ] test_database_types.py - Test different databases

#### 5.2 Update existing scripts
- [ ] Update load_initial_training.py for metadata
- [ ] Update test_connection.py for new config

### Phase 6: Documentation (Priority: Low)

#### 6.1 Update README.md
- [ ] Add multi-database setup instructions
- [ ] Add multi-tenant configuration examples
- [ ] Update tool usage examples

#### 6.2 Create deployment guides
- [ ] Single-tenant deployment guide
- [ ] Multi-tenant deployment guide
- [ ] Migration guide from old version

### Phase 7: Cleanup (Priority: Low)

#### 7.1 Remove deprecated code
- [ ] Remove schema enforcement attempts
- [ ] Clean up unused imports
- [ ] Remove temporary migration scripts

#### 7.2 Code organization
- [ ] Move database-specific code to separate modules
- [ ] Create proper error handling
- [ ] Add comprehensive logging

## File Changes Summary

### Files to Modify:
1. `/src/config/settings.py` - Configuration updates
2. `/src/config/multi_database_vanna.py` - Core implementation
3. `/src/config/vanna_config.py` - Use MultiDatabaseVanna
4. `/server.py` - Tool parameter updates
5. `/src/tools/vanna_ask.py` - Add tenant support
6. `/src/tools/vanna_train.py` - Add shared knowledge support

### Files to Create:
1. `/scripts/test_multi_tenant.py` - Testing script
2. `/scripts/test_shared_knowledge.py` - Testing script
3. `/docs/DEPLOYMENT_GUIDE.md` - Deployment instructions

### Files to Remove:
1. `/scripts/force_all_to_vannabq.py` - Deprecated
2. `/scripts/cleanup_and_implement_proper_schema.py` - Deprecated
3. `/src/config/vanna_schema_wrapper.py` - No longer needed

## Success Criteria

1. **Single-Tenant Mode**: Works exactly as before when ENABLE_MULTI_TENANT=false
2. **Multi-Tenant Isolation**: Tenants cannot see each other's data
3. **Shared Knowledge**: Works when enabled, ignored when disabled
4. **Multiple Databases**: Can deploy separate instances for different database types
5. **Backward Compatibility**: Existing configurations continue to work

## Risk Mitigation

1. **Data Leakage**: Implement strict filtering at pgvector level
2. **Performance**: Test with large datasets and multiple tenants
3. **Compatibility**: Maintain backward compatibility with existing setups
4. **Security**: Validate all tenant operations

## Timeline Estimate

- Phase 1-3: 2-3 hours (Core functionality)
- Phase 4-5: 2-3 hours (Database support and testing)
- Phase 6-7: 1-2 hours (Documentation and cleanup)

Total: 5-8 hours of implementation work