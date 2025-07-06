# Tool Development Standards & Security Requirements

## Overview

This document establishes mandatory standards for all MCP tools in the Vanna MCP Server to ensure consistent security, filtering, and functionality across the entire tool suite.

**⚠️ CRITICAL:** All tools MUST implement these standards before being considered production-ready.

## Security & Filtering Requirements

### 1. Multi-Tenant Support (MANDATORY)

All tools that process queries, training data, or access database information MUST implement:

#### **Tenant ID Validation**
```python
# Handle tenant_id in multi-tenant mode
if settings.ENABLE_MULTI_TENANT:
    # Use default tenant if not provided
    if not tenant_id:
        tenant_id = settings.TENANT_ID
        logger.info(f"No tenant_id provided, using default: {tenant_id}")
    
    # Validate tenant_id
    if not tenant_id:
        return {
            "success": False,
            "error": "tenant_id is required when multi-tenant is enabled",
            "allowed_tenants": settings.get_allowed_tenants()
        }
    
    if not settings.is_tenant_allowed(tenant_id):
        allowed = settings.get_allowed_tenants()
        return {
            "success": False,
            "error": f"Tenant '{tenant_id}' is not allowed",
            "allowed_tenants": allowed if allowed else "All tenants allowed"
        }
```

#### **Cross-Tenant Query Validation**
For tools that process SQL queries, MUST implement cross-tenant validation:

```python
# CRITICAL: Apply cross-tenant validation (same as vanna_ask)
if settings.ENABLE_MULTI_TENANT and (tenant_id or settings.TENANT_ID):
    effective_tenant = tenant_id or settings.TENANT_ID
    
    # Import cross-tenant validation logic from vanna_ask
    try:
        from src.tools.vanna_ask import _extract_tables_from_sql, _check_cross_tenant_access
        
        tables_referenced = _extract_tables_from_sql(sql_content)
        logger.info(f"Tables referenced in {tool_name}: {tables_referenced}")
        
        # Check for cross-tenant violations
        tenant_violations = _check_cross_tenant_access(tables_referenced, effective_tenant)
        
        if tenant_violations:
            if settings.STRICT_TENANT_ISOLATION:
                return {
                    "success": False,
                    "error": f"Cross-tenant table access blocked in {tool_name}",
                    "blocked_tables": tenant_violations,
                    "tenant_id": effective_tenant,
                    "security_policy": "STRICT_TENANT_ISOLATION enabled",
                    "suggestions": [
                        f"Use tables accessible to tenant '{effective_tenant}'",
                        "Contact administrator to access shared data"
                    ]
                }
            else:
                # Permissive mode: warn but continue
                logger.warning(f"Cross-tenant access detected in {tool_name} for tenant '{effective_tenant}': {tenant_violations}")
                
    except ImportError as e:
        logger.warning(f"Could not import cross-tenant validation: {e}")
```

### 2. Database Type Awareness (MANDATORY)

All tools MUST handle database type validation and adaptation:

#### **Database Type Validation**
```python
# Database type validation
database_type = settings.DATABASE_TYPE

# For execution tools
if tool_requires_execution and database_type.lower() != "bigquery":
    return {
        "success": False,
        "error": f"Tool only supported for BigQuery, current database: {database_type}",
        "suggestions": ["Configure DATABASE_TYPE=bigquery for execution support"]
    }

# For explanation/analysis tools
if database_type:
    logger.info(f"Processing for database type: {database_type}")
    # Include database-specific context in processing
```

#### **Database-Specific Features**
- Include database type in prompts and processing context
- Handle database-specific SQL syntax differences
- Provide database-appropriate suggestions and explanations

### 3. Shared Knowledge Support (MANDATORY)

All tools MUST respect shared knowledge settings:

#### **Shared Knowledge Context**
```python
# Include shared knowledge status in metadata
"shared_knowledge_enabled": settings.ENABLE_SHARED_KNOWLEDGE if settings.ENABLE_MULTI_TENANT else None
```

#### **Shared Knowledge Processing**
- Tools that access training data MUST consider `ENABLE_SHARED_KNOWLEDGE`
- Tools that provide suggestions MUST include shared knowledge when enabled
- Tools MUST filter results based on shared knowledge settings

### 4. Response Metadata Standards (MANDATORY)

All tools MUST include consistent metadata in responses:

#### **Required Metadata Fields**
```python
# Standard metadata for all tools
result.update({
    "tenant_id": tenant_id if settings.ENABLE_MULTI_TENANT else None,
    "database_type": settings.DATABASE_TYPE,
    "timestamp": datetime.now().isoformat(),
    "shared_knowledge_enabled": settings.ENABLE_SHARED_KNOWLEDGE if settings.ENABLE_MULTI_TENANT else None,
    "strict_isolation": settings.STRICT_TENANT_ISOLATION if settings.ENABLE_MULTI_TENANT else None
})
```

#### **Tool-Specific Metadata**
Each tool should add relevant specific metadata while maintaining the standard fields.

## Implementation Checklist

### For Each New Tool

#### **Phase 1: Core Implementation**
- [ ] Implement basic tool functionality
- [ ] Add tenant_id parameter to tool signature
- [ ] Import required settings and validation functions

#### **Phase 2: Security Implementation (CRITICAL)**
- [ ] Add tenant ID validation and error handling
- [ ] Implement cross-tenant query validation (if tool processes SQL)
- [ ] Add database type validation and restrictions
- [ ] Include shared knowledge handling

#### **Phase 3: Metadata & Consistency**
- [ ] Add standard metadata fields to responses
- [ ] Include tool-specific metadata
- [ ] Add proper logging for security events
- [ ] Ensure error messages include helpful suggestions

#### **Phase 4: Testing & Validation**
- [ ] Test with multiple tenants
- [ ] Test cross-tenant access attempts
- [ ] Test with different database types
- [ ] Verify metadata consistency
- [ ] Test security policy enforcement

## Code Patterns & Templates

### Basic Tool Structure Template
```python
async def new_tool(
    # Tool-specific parameters
    param1: str,
    param2: Optional[str] = None,
    # Standard parameters (MANDATORY)
    tenant_id: Optional[str] = None,
    # Tool-specific optional parameters
    include_metadata: bool = True
) -> Dict[str, Any]:
    """
    Tool description
    
    Args:
        param1: Tool-specific parameter
        tenant_id: Override default tenant (for multi-tenant mode)
        include_metadata: Include execution metadata
    """
    try:
        vn = get_vanna()
        
        # 1. TENANT VALIDATION (MANDATORY)
        if settings.ENABLE_MULTI_TENANT:
            # ... implement tenant validation
        
        # 2. INPUT VALIDATION
        # ... validate tool-specific inputs
        
        # 3. CROSS-TENANT VALIDATION (if processing SQL)
        if processes_sql and settings.ENABLE_MULTI_TENANT:
            # ... implement cross-tenant validation
        
        # 4. DATABASE TYPE VALIDATION
        database_type = settings.DATABASE_TYPE
        # ... implement database-specific logic
        
        # 5. CORE TOOL LOGIC
        # ... implement main functionality
        
        # 6. RESPONSE ASSEMBLY
        result = {
            "success": True,
            # ... tool-specific results
        }
        
        # 7. METADATA (MANDATORY)
        if include_metadata:
            result.update({
                "tenant_id": tenant_id if settings.ENABLE_MULTI_TENANT else None,
                "database_type": database_type,
                "timestamp": datetime.now().isoformat(),
                "shared_knowledge_enabled": settings.ENABLE_SHARED_KNOWLEDGE if settings.ENABLE_MULTI_TENANT else None,
                "strict_isolation": settings.STRICT_TENANT_ISOLATION if settings.ENABLE_MULTI_TENANT else None
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Error in {tool_name}: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": f"{tool_name} error: {str(e)}",
            "error_type": type(e).__name__,
            "suggestions": ["Check input parameters", "Verify database connection"]
        }
```

## Security Policies & Enforcement

### STRICT_TENANT_ISOLATION Policy
When `STRICT_TENANT_ISOLATION=true`:
- **Block all cross-tenant access attempts immediately**
- **Return clear error messages with security context**
- **Log all security violations**
- **Provide helpful suggestions for resolution**

### Permissive Mode (STRICT_TENANT_ISOLATION=false)
When permissive mode is enabled:
- **Warn about cross-tenant access but allow operation**
- **Log warnings for audit purposes**
- **Reduce confidence scores where applicable**
- **Include security warnings in responses**

### Database Type Restrictions
- **Execution tools**: Only allow execution for supported database types
- **Analysis tools**: Adapt analysis to database-specific features
- **Training tools**: Validate data formats for target database

## Common Security Vulnerabilities to Avoid

### ❌ **NEVER DO**
1. **Skip tenant validation** - All tools must validate tenant access
2. **Process SQL without cross-tenant checks** - Always validate table access
3. **Ignore database type** - Always consider database-specific constraints
4. **Return inconsistent metadata** - Always include standard metadata fields
5. **Execute queries without validation** - Always validate before execution

### ✅ **ALWAYS DO**
1. **Validate tenant_id** before processing any data
2. **Check cross-tenant access** for any SQL content
3. **Include database type** in processing context
4. **Log security events** appropriately
5. **Return helpful error messages** with clear next steps

## Testing Requirements

### Security Testing (MANDATORY)
Each tool MUST pass these security tests:

1. **Multi-tenant isolation**: Tool rejects cross-tenant access
2. **Database type validation**: Tool handles unsupported databases gracefully
3. **Metadata consistency**: Tool returns standard metadata fields
4. **Error handling**: Tool provides helpful error messages
5. **Logging verification**: Tool logs security events appropriately

### Integration Testing
- Test with existing tools for consistency
- Verify metadata format compatibility
- Test with different configuration combinations

## Compliance Verification

### Pre-Production Checklist
Before any tool can be deployed to production:

- [ ] **Security audit passed** - All security requirements implemented
- [ ] **Cross-tenant testing completed** - Tool properly isolates tenants
- [ ] **Database compatibility verified** - Tool works with configured database
- [ ] **Metadata consistency confirmed** - Tool returns standard metadata
- [ ] **Error handling validated** - Tool provides helpful error messages
- [ ] **Documentation complete** - Tool is properly documented
- [ ] **Code review approved** - Security implementation reviewed

### Ongoing Compliance
- Regular security audits of all tools
- Automated testing for security regression
- Consistent monitoring of cross-tenant access attempts
- Regular updates to security standards as needed

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-01-06 | Initial standards based on Phase 3 security audit |

---

**⚠️ IMPORTANT:** These standards are MANDATORY for all tools. Any tool that does not implement these requirements is considered a security risk and MUST NOT be deployed to production.