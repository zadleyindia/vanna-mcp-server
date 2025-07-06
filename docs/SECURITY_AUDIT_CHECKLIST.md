# Security Audit Checklist for MCP Tools

## Overview
This checklist must be completed for every MCP tool before it can be considered production-ready.

## Tool Information
- **Tool Name**: ________________
- **Audit Date**: ________________
- **Auditor**: ________________
- **Tool Version/Commit**: ________________

## Security Requirements Audit

### 1. Multi-Tenant Support
- [ ] **Tenant ID Parameter**: Tool accepts `tenant_id` parameter
- [ ] **Default Tenant Fallback**: Uses `settings.TENANT_ID` when no tenant provided
- [ ] **Tenant Validation**: Validates tenant against `settings.get_allowed_tenants()`
- [ ] **Tenant Error Handling**: Returns proper error messages for invalid tenants
- [ ] **Tenant Logging**: Logs tenant context for operations

### 2. Cross-Tenant Access Protection
- [ ] **SQL Content Analysis**: Tool analyzes SQL content for table references (if applicable)
- [ ] **Cross-Tenant Detection**: Detects and flags cross-tenant table access attempts
- [ ] **STRICT_TENANT_ISOLATION**: Properly enforces strict isolation policy when enabled
- [ ] **Permissive Mode**: Warns but continues when strict isolation disabled
- [ ] **Security Logging**: Logs cross-tenant access attempts and violations

### 3. Database Type Awareness
- [ ] **Database Type Validation**: Validates operations against configured database type
- [ ] **Type-Specific Features**: Handles database-specific features appropriately
- [ ] **Unsupported Operations**: Properly rejects unsupported operations for database type
- [ ] **Database Context**: Includes database type in processing context

### 4. Shared Knowledge Support
- [ ] **Shared Knowledge Awareness**: Respects `ENABLE_SHARED_KNOWLEDGE` setting
- [ ] **Shared Data Access**: Properly handles shared vs tenant-specific data
- [ ] **Metadata Inclusion**: Includes shared knowledge status in response metadata

### 5. Response Metadata Standards
- [ ] **Standard Fields**: Includes all mandatory metadata fields
  - [ ] `tenant_id` (when multi-tenant enabled)
  - [ ] `database_type`
  - [ ] `timestamp`
  - [ ] `shared_knowledge_enabled`
  - [ ] `strict_isolation`
- [ ] **Consistent Format**: Metadata format matches other tools
- [ ] **Optional Metadata**: Properly handles `include_metadata` parameter

### 6. Error Handling & Security
- [ ] **Security Error Messages**: Clear, helpful error messages for security violations
- [ ] **Suggestion Provision**: Provides actionable suggestions for resolving issues
- [ ] **Error Logging**: Proper logging of errors and security events
- [ ] **Exception Handling**: Graceful handling of exceptions without information leakage

### 7. Input Validation
- [ ] **Parameter Validation**: Validates all input parameters
- [ ] **SQL Sanitization**: Properly sanitizes SQL input (if applicable)
- [ ] **Injection Prevention**: Prevents SQL injection and other injection attacks
- [ ] **Input Limits**: Enforces reasonable limits on input size/complexity

### 8. Settings Integration
- [ ] **Settings Import**: Properly imports and uses settings module
- [ ] **Configuration Respect**: Respects all relevant configuration settings
- [ ] **Setting Validation**: Validates required settings are present
- [ ] **Default Handling**: Proper handling of missing or default settings

## Testing Requirements

### Security Testing
- [ ] **Multi-Tenant Isolation**: Tested with multiple tenants, confirmed isolation
- [ ] **Cross-Tenant Blocking**: Attempted cross-tenant access, confirmed blocking
- [ ] **Database Type**: Tested with different database configurations
- [ ] **Invalid Tenant**: Tested with invalid tenant IDs, confirmed rejection
- [ ] **Security Policy**: Tested both strict and permissive isolation modes

### Functional Testing
- [ ] **Basic Operation**: Tool performs core function correctly
- [ ] **Error Scenarios**: Tool handles error conditions gracefully
- [ ] **Edge Cases**: Tool handles edge cases and boundary conditions
- [ ] **Performance**: Tool performs within acceptable limits

### Integration Testing
- [ ] **Tool Consistency**: Metadata format consistent with other tools
- [ ] **Setting Compatibility**: Works with various configuration combinations
- [ ] **Server Integration**: Properly integrates with MCP server

## Security Vulnerabilities Check

### Common Vulnerabilities (MUST BE NONE)
- [ ] **No Cross-Tenant Leakage**: Confirmed no data leakage between tenants
- [ ] **No Privilege Escalation**: Cannot access unauthorized data or functions
- [ ] **No Injection Vulnerabilities**: No SQL injection or other injection risks
- [ ] **No Information Disclosure**: No unauthorized information disclosure
- [ ] **No Authentication Bypass**: Cannot bypass tenant authentication/authorization

### Tool-Specific Risks
- [ ] **Tool-Specific Risk 1**: ________________________________
- [ ] **Tool-Specific Risk 2**: ________________________________
- [ ] **Tool-Specific Risk 3**: ________________________________

## Code Quality & Compliance

### Code Standards
- [ ] **Follows Template**: Uses approved tool development template
- [ ] **Standard Imports**: Uses standard imports and patterns
- [ ] **Error Handling**: Consistent error handling pattern
- [ ] **Logging Standards**: Follows logging standards and patterns
- [ ] **Documentation**: Proper docstrings and inline documentation

### Security Code Review
- [ ] **Validation Logic**: All validation logic reviewed and approved
- [ ] **Security Functions**: All security-related functions reviewed
- [ ] **Dependencies**: All dependencies reviewed for security issues
- [ ] **Configuration**: All configuration usage reviewed

## Audit Results

### Security Score
- **Total Checks**: _____ / _____
- **Security Issues Found**: _____
- **Critical Issues**: _____
- **High Issues**: _____
- **Medium Issues**: _____
- **Low Issues**: _____

### Overall Assessment
- [ ] **PASS**: Tool meets all security requirements and is ready for production
- [ ] **CONDITIONAL PASS**: Tool meets most requirements but needs minor fixes
- [ ] **FAIL**: Tool has significant security issues and cannot be deployed

### Required Actions
1. _________________________________
2. _________________________________
3. _________________________________

### Recommendations
1. _________________________________
2. _________________________________
3. _________________________________

## Sign-Off

### Security Auditor
- **Name**: ________________
- **Date**: ________________
- **Signature**: ________________

### Technical Lead
- **Name**: ________________
- **Date**: ________________
- **Signature**: ________________

---

**Note**: This audit must be passed before any tool can be deployed to production. Tools that fail the audit must be fixed and re-audited before deployment.