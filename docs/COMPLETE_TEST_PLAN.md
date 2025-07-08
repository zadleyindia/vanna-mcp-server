# Vanna MCP Server - Complete Test Plan

## Overview
This document provides a comprehensive test plan for all 11 implemented tools in the Vanna MCP Server.

## Test Environment
- **Tenant**: zadley (default)
- **Database Type**: BigQuery
- **Multi-tenant Mode**: Enabled
- **Strict Isolation**: Enabled
- **Shared Knowledge**: Enabled

---

## Tool Testing Sequence

### Phase 1: Core Tools (1-3)

#### 1. vanna_ask - Natural Language to SQL
```
Test 1.1: Basic query
- Question: "Show me total sales by product"
- Expected: SQL with GROUP BY product

Test 1.2: Multi-tenant query
- Question: "What are the top customers by revenue?"
- Tenant: zadley
- Expected: SQL filtered by tenant

Test 1.3: Cross-tenant attempt
- Question: "Show me data from zadley_india.sales"
- Expected: Error - cross-tenant blocked

Test 1.4: Shared knowledge
- Question: "What shared metrics are available?"
- include_shared: true
- Expected: Results include shared data
```

#### 2. vanna_train - Add Training Data
```
Test 2.1: DDL training
- Type: "ddl"
- Content: "CREATE TABLE test_products (id INT, name STRING, price DECIMAL)"
- Expected: Success with metadata extraction

Test 2.2: Documentation training
- Type: "documentation"
- Content: "Revenue is calculated as quantity * unit_price"
- Expected: Success

Test 2.3: SQL training
- Type: "sql"
- Content: "SELECT product_name, SUM(revenue) FROM sales GROUP BY product_name"
- Question: "Show revenue by product"
- Expected: Success with validation

Test 2.4: Dangerous DDL attempt
- Type: "ddl"
- Content: "DROP TABLE users; CREATE TABLE test (id INT)"
- Expected: Error - dangerous keywords blocked
```

#### 3. vanna_suggest_questions - Get Suggestions
```
Test 3.1: Basic suggestions
- No parameters
- Expected: 5 relevant questions

Test 3.2: Context-based suggestions
- Context: "sales analysis"
- Expected: Sales-focused questions

Test 3.3: Limited suggestions
- Limit: 3
- Expected: Exactly 3 questions
```

### Phase 2: Support Tools (4-5)

#### 4. vanna_list_tenants - List Tenant Config
```
Test 4.1: List configuration
- No parameters
- Expected: Shows zadley, zadley_india, zadley_retail
```

#### 5. vanna_get_query_history - View History
```
Test 5.1: Recent queries
- Limit: 5
- Expected: Last 5 queries for tenant

Test 5.2: With analytics
- include_analytics: true
- Expected: Includes success rate, avg time
```

### Phase 3: Extended Tools (6-7)

#### 6. vanna_explain - Explain SQL
```
Test 6.1: Basic explanation
- SQL: "SELECT COUNT(*) FROM orders WHERE status = 'completed'"
- Expected: Plain English explanation

Test 6.2: Complex query explanation
- SQL: Complex JOIN with aggregation
- detail_level: "detailed"
- Expected: Technical breakdown

Test 6.3: Performance tips
- SQL: "SELECT * FROM large_table"
- include_performance_tips: true
- Expected: Suggests column selection
```

#### 7. vanna_execute - Execute SQL
```
Test 7.1: Basic execution
- SQL: "SELECT COUNT(*) FROM products"
- Expected: Result with count

Test 7.2: With export
- SQL: "SELECT * FROM sales LIMIT 10"
- export_format: "csv"
- Expected: CSV data returned

Test 7.3: Non-SELECT attempt
- SQL: "DELETE FROM products"
- Expected: Error - only SELECT allowed
```

### Phase 4: Management Tools (8-10)

#### 8. vanna_get_schemas - View Schemas
```
Test 8.1: All schemas
- No parameters
- Expected: Hierarchical schema list

Test 8.2: Filtered schemas
- table_filter: "sales*"
- Expected: Only sales tables

Test 8.3: Detailed format
- format_output: "detailed"
- Expected: Full column details
```

#### 9. vanna_get_training_data - View Training
```
Test 9.1: All training data
- Limit: 10
- Expected: Recent 10 items

Test 9.2: DDL only
- training_type: "ddl"
- Expected: Only DDL entries

Test 9.3: Search training
- search_query: "customer"
- Expected: Customer-related training

Test 9.4: Pagination
- limit: 5, offset: 5
- Expected: Items 6-10
```

#### 10. vanna_remove_training - Remove Training
```
Test 10.1: Dry run removal
- training_ids: [get from test 9]
- dry_run: true
- Expected: Preview without deletion

Test 10.2: Actual removal
- training_ids: [single ID]
- confirm_removal: true
- reason: "Test removal"
- Expected: Success with audit

Test 10.3: Cross-tenant attempt
- training_ids: [other tenant's ID]
- Expected: Error - access denied

Test 10.4: Bulk removal
- training_ids: [multiple IDs]
- Expected: Success/failure per item
```

### Phase 5: Advanced Tools (11)

#### 11. vanna_generate_followup - Follow-up Questions
```
Test 11.1: Basic follow-up
- original_question: "Show me sales by region"
- sql_generated: "SELECT region, SUM(sales) FROM orders GROUP BY region"
- Expected: 5 relevant follow-ups

Test 11.2: Temporal focus
- original_question: "Total revenue"
- sql_generated: "SELECT SUM(revenue) FROM sales"
- focus_area: "temporal"
- Expected: Time-based questions

Test 11.3: Limited suggestions
- max_suggestions: 3
- Expected: Exactly 3 questions

Test 11.4: No deeper analysis
- include_deeper_analysis: false
- Expected: Basic questions only
```

---

## Security Testing Matrix

| Tool | Multi-Tenant | Cross-Tenant | Shared Knowledge | Input Validation |
|------|--------------|--------------|------------------|------------------|
| vanna_ask | ✓ Test tenant filtering | ✓ Test blocking | ✓ Test inclusion | ✓ Test empty query |
| vanna_train | ✓ Test tenant tagging | N/A | ✓ Test is_shared | ✓ Test DDL validation |
| vanna_suggest_questions | ✓ Test tenant context | N/A | ✓ Test shared | ✓ Test limits |
| vanna_list_tenants | ✓ Show allowed only | N/A | N/A | N/A |
| vanna_get_query_history | ✓ Filter by tenant | N/A | N/A | ✓ Test limits |
| vanna_explain | ✓ Test validation | ✓ Test SQL check | N/A | ✓ Test empty SQL |
| vanna_execute | ✓ Test validation | ✓ Pre-execution check | N/A | ✓ Test non-SELECT |
| vanna_get_schemas | ✓ Show tenant schemas | N/A | ✓ Show shared | ✓ Test filters |
| vanna_get_training_data | ✓ Filter by tenant | N/A | ✓ Include shared | ✓ Test pagination |
| vanna_remove_training | ✓ Own tenant only | ✓ Block cross-tenant | ✓ Protect shared | ✓ Test UUID format |
| vanna_generate_followup | ✓ Test validation | ✓ Test SQL check | N/A | ✓ Test empty inputs |

---

## Integration Testing

### Workflow 1: Complete Query Lifecycle
1. Use `vanna_suggest_questions` to get ideas
2. Use `vanna_ask` to generate SQL
3. Use `vanna_explain` to understand the query
4. Use `vanna_execute` to run it
5. Use `vanna_generate_followup` for next questions
6. Store history automatically

### Workflow 2: Training Management
1. Use `vanna_get_schemas` to see current structure
2. Use `vanna_train` to add new DDL
3. Use `vanna_get_training_data` to verify
4. Use `vanna_train` to add documentation
5. Use `vanna_train` to add SQL examples
6. Use `vanna_remove_training` to clean up bad data

### Workflow 3: Multi-Tenant Verification
1. Use `vanna_list_tenants` to see configuration
2. Try queries with different tenant_id values
3. Verify isolation in all tools
4. Test shared knowledge access

---

## Expected Test Results

### Success Metrics
- All 11 tools respond without errors
- Multi-tenant isolation works correctly
- Cross-tenant access is blocked where applicable
- Shared knowledge is accessible when enabled
- All input validation works
- Metadata is consistent across tools

### Known Limitations
- SQL execution only works with BigQuery
- Cannot remove shared knowledge
- Cannot access other tenants' data
- DDL training blocks dangerous operations

---

## Test Execution Checklist

- [ ] Restart Claude Desktop
- [ ] Verify 11 tools loaded in logs
- [ ] Execute each test case
- [ ] Document any failures
- [ ] Verify security controls
- [ ] Test integration workflows
- [ ] Check performance (response times)
- [ ] Validate error messages

---

## Troubleshooting

### Common Issues
1. **Tool not found**: Restart Claude Desktop
2. **Tenant errors**: Check TENANT_ID in config
3. **Connection errors**: Verify Supabase/BigQuery credentials
4. **Cross-tenant blocks**: This is expected behavior
5. **Empty results**: Check if training data exists

### Debug Commands
- Check logs: `/Users/mohit/Library/Logs/Claude/mcp-server-vanna-mcp.log`
- List tools: Look for all 11 in Claude Desktop
- Test connection: Try `vanna_list_tenants` first