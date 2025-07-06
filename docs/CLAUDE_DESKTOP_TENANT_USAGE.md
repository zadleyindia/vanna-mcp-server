# Using Tenant Features in Claude Desktop

> **Last Updated**: 2025-01-06  
> **Status**: Fully functional with filtered vector store implementation

## Overview

This guide explains how to use the multi-tenant and multi-database features of Vanna MCP Server in Claude Desktop. With the recent implementation of filtered vector store and forked Vanna, tenant isolation is now properly enforced at the database level.

## The Challenge
When Claude Desktop loads the MCP tools, it only sees the parameter definitions (e.g., `tenant_id: string`), not the actual valid values. The `ALLOWED_TENANTS` configuration is only known server-side.

## The Solution: vanna_list_tenants Tool

### Discovery Workflow

1. **First, discover allowed tenants:**
   ```
   Use vanna_list_tenants to show me the tenant configuration
   ```

2. **Claude will respond with:**
   ```json
   {
     "multi_tenant_enabled": true,
     "default_tenant": "zaldey",
     "allowed_tenants": ["zaldey", "singla", "customer1"],
     "all_tenants_allowed": false,
     "shared_knowledge_enabled": true,
     "current_database_type": "bigquery",
     "message": "3 tenants are allowed. Use 'shared' for shared knowledge.",
     "usage_examples": [...]
   }
   ```

3. **Then use the allowed tenants:**
   ```
   Ask a question for tenant singla: Show me total sales
   ```

## Key Features

### 1. Metadata Filtering
With the custom FilteredPGVectorStore implementation:
- Each query is filtered by database_type AND tenant_id
- No cross-contamination between tenants
- Shared knowledge is explicitly marked and accessible when enabled

### 2. Automatic Metadata Tagging
All training data is automatically tagged with:
- `database_type`: From configuration (bigquery, postgres, mssql)
- `tenant_id`: From configuration or parameter override
- `is_shared`: For shared knowledge across tenants
- `created_at`: Timestamp for tracking

### 3. Fork Benefits
Using the forked Vanna (https://github.com/zadleyindia/vanna):
- Native metadata support in train() method
- Cleaner API without workarounds
- Future-proof for official Vanna updates

## Prompting Strategies

### Strategy 1: Explicit Tenant Discovery
```
1. What tenants are available?
2. Train this DDL for tenant singla: CREATE TABLE...
```

### Strategy 2: Let Claude Handle It
```
"Train this documentation for the singla tenant, but first check if that tenant is allowed"
```
Claude will:
1. Call vanna_list_tenants
2. Verify "singla" is allowed
3. Call vanna_train with tenant_id="singla"

### Strategy 3: Upfront Context
```
"I want to work with tenant singla. First show me the allowed tenants, then train this DDL..."
```

## Example Conversations

### Example 1: Multi-Tenant Query
**User**: "Show me what tenants I can query data for"

**Claude**: Let me check the tenant configuration for you.
*[Calls vanna_list_tenants]*

You can query data for these tenants:
- zaldey (default)
- singla 
- customer1

You can also use shared knowledge available to all tenants.

**User**: "Now show me sales data for tenant singla"

**Claude**: I'll query the sales data for tenant singla.
*[Calls vanna_ask with tenant_id="singla"]*

### Example 2: Training with Validation
**User**: "Train this DDL for tenant acme: CREATE TABLE orders..."

**Claude**: Let me first check if 'acme' is an allowed tenant.
*[Calls vanna_list_tenants]*

I see that 'acme' is not in the allowed tenants list. The allowed tenants are:
- zaldey
- singla
- customer1

Would you like me to train this for one of these tenants instead?

### Example 3: Shared Knowledge
**User**: "Add this as a best practice for all tenants: Always use proper date formatting"

**Claude**: I'll add this as shared knowledge available to all tenants.
*[Calls vanna_train with is_shared=true]*

Successfully added documentation as shared knowledge for all tenants.

### Example 4: Multi-Database Context
**User**: "I have BigQuery and PostgreSQL instances. Train this BigQuery DDL for tenant acme"

**Claude**: I'll train this BigQuery DDL for tenant acme. The system will automatically tag it with:
- database_type: bigquery (from your configuration)
- tenant_id: acme
- content_type: ddl

*[Calls vanna_train with DDL content]*

## Best Practices for Claude Desktop Users

1. **Start Sessions with Discovery**:
   - Begin with "Show me the tenant configuration"
   - This gives Claude context about available tenants

2. **Use Natural Language**:
   - "Query data for tenant singla"
   - "Train this for all tenants" (Claude will use is_shared=true)
   - "Use the customer1 tenant"

3. **Let Claude Validate**:
   - Just specify the tenant you want
   - Claude will check if it's allowed and inform you if not

4. **Session Memory**:
   - Once Claude knows the allowed tenants in a session, it remembers
   - You don't need to check every time

5. **Database Context**:
   - The database type is set in configuration
   - All operations are automatically filtered by database type
   - No BigQuery SQL will ever appear in PostgreSQL context

## Configuration Examples

### For Development (Multiple Test Tenants)
```json
{
  "DATABASE_TYPE": "bigquery",
  "ENABLE_MULTI_TENANT": "true",
  "ALLOWED_TENANTS": "dev1,dev2,test,staging",
  "TENANT_ID": "dev1"
}
```
Usage: "Run this query for the test tenant"

### For Production (Locked Down)
```json
{
  "DATABASE_TYPE": "bigquery",
  "ENABLE_MULTI_TENANT": "true",
  "ALLOWED_TENANTS": "production",
  "TENANT_ID": "production"
}
```
Only one tenant allowed - no need to specify in commands

### For Multi-Customer
```json
{
  "DATABASE_TYPE": "bigquery",
  "ENABLE_MULTI_TENANT": "true",
  "ALLOWED_TENANTS": "acme,globex,initech",
  "TENANT_ID": "acme",
  "ENABLE_SHARED_KNOWLEDGE": "true"
}
```
Usage: "Show me data for the globex tenant"

### For Single Database, No Tenants
```json
{
  "DATABASE_TYPE": "postgres",
  "ENABLE_MULTI_TENANT": "false"
}
```
Simple setup - no tenant specification needed

## Error Handling

When you request an invalid tenant, Claude will see:
```json
{
  "error": "Tenant 'invalid' is not allowed",
  "allowed_tenants": ["zaldey", "singla", "customer1"],
  "suggestions": ["Use one of the allowed tenants", "Check your tenant configuration"]
}
```

And will helpfully suggest valid options.

## Technical Implementation

### How Isolation Works
1. **Training**: All data is tagged with metadata (database_type, tenant_id)
2. **Retrieval**: Similarity search includes JSONB metadata filters
3. **Generation**: Only relevant context is used for SQL generation

### Metadata Structure
```json
{
  "database_type": "bigquery",
  "tenant_id": "acme_corp",
  "content_type": "ddl|documentation|sql",
  "is_shared": "true|false",
  "created_at": "2025-01-06T10:30:00Z",
  "created_by": "user@example.com"
}
```

### Vector Store Query
When you ask a question, the system:
1. Generates embedding for your question
2. Searches similar embeddings WITH metadata filter
3. Returns only matching database_type AND tenant_id results
4. Optionally includes shared knowledge if enabled

## Summary

The Vanna MCP Server now provides true multi-database and multi-tenant isolation through:
1. Custom FilteredPGVectorStore implementation
2. Forked Vanna with metadata support
3. Automatic metadata tagging
4. Server-side tenant validation
5. Clean discovery mechanism via vanna_list_tenants

While Claude Desktop can't automatically populate a dropdown of valid tenants, the `vanna_list_tenants` tool provides a clean discovery mechanism. Users can:

1. Ask Claude to list tenants at any time
2. Use natural language to specify tenants
3. Rely on Claude to validate and guide them to valid options
4. Trust that data isolation is enforced at the database level

This approach maintains security (server-side validation) while providing a good user experience with proper data isolation.