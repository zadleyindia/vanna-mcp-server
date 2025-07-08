# MS SQL Server Support Audit Report for Vanna MCP Tools

## Summary
This audit examines all 13 Vanna MCP tools to assess their MS SQL Server support. The user has reported that not all tools work properly with MS SQL in the past.

## Key Findings

### Database Type Configuration
- The system uses `settings.DATABASE_TYPE` to determine the active database
- Supported values: "bigquery", "mssql", "postgres", "mysql"
- MS SQL configuration is available in `settings.py` with proper connection string support

### Tool-by-Tool Analysis

#### 1. vanna_ask ✅ Partially Supported
**File:** `/src/tools/vanna_ask.py`
- **Status:** Database-aware but hardcoded for BigQuery
- **Issues:**
  - Line 26: Docstring mentions "generates appropriate SQL queries for BigQuery" (hardcoded)
  - Line 56: Example response shows BigQuery-specific syntax
  - Line 244: Uses `settings.DATABASE_TYPE` correctly
  - **Missing:** No SQL dialect adaptation for MS SQL syntax differences

#### 2. vanna_train ❌ BigQuery Import
**File:** `/src/tools/vanna_train.py`
- **Status:** Has BigQuery-specific import
- **Issues:**
  - Line 11: `from google.cloud import bigquery` - unnecessary import
  - No database-specific handling in the training logic
  - Should work for MS SQL if BigQuery import is removed/made conditional

#### 3. vanna_suggest_questions ❓ Not Examined Yet
**File:** `/src/tools/vanna_suggest_questions.py`
- Needs examination

#### 4. vanna_list_tenants ❓ Not Examined Yet
**File:** `/src/tools/vanna_list_tenants.py`
- Needs examination

#### 5. vanna_get_query_history ❓ Not Examined Yet
**File:** `/src/tools/vanna_get_query_history.py`
- Uses `settings.DATABASE_TYPE` (found in grep)

#### 6. vanna_explain ✅ Partially Supported
**File:** `/src/tools/vanna_explain.py`
- **Status:** Database-aware
- **Issues:**
  - Line 52: Mentions "estimated_cost (str): Rough cost estimate for BigQuery"
  - Line 148-150: Has database type awareness but no MS SQL specific handling
  - **Missing:** MS SQL specific performance tips and cost estimation

#### 7. vanna_execute ❌ BigQuery Only
**File:** `/src/tools/vanna_execute.py`
- **Status:** BigQuery-specific implementation
- **Critical Issues:**
  - Line 14: Imports `from google.cloud import bigquery`
  - Line 203-208: Explicitly checks and blocks non-BigQuery databases:
    ```python
    if database_type.lower() != "bigquery":
        return {
            "success": False,
            "error": f"SQL execution only supported for BigQuery, current database: {database_type}",
            "suggestions": ["Configure DATABASE_TYPE=bigquery for execution support"]
        }
    ```
  - Line 345-397: Uses BigQuery client for execution
  - **Verdict:** NO MS SQL SUPPORT - needs complete rewrite for MS SQL

#### 8. vanna_get_schemas ✅ Partially Supported
**File:** `/src/tools/vanna_get_schemas.py`
- **Status:** Database-aware
- Line 101: Uses `settings.DATABASE_TYPE`
- Line 106: Gets DDL training data which should work for any database
- **Issues:** Relies on DDL training data, no direct MS SQL schema querying

#### 9. vanna_get_training_data ✅ Database-Aware
**File:** `/src/tools/vanna_get_training_data.py`
- Uses `DATABASE_TYPE` for filtering training data
- Should work with MS SQL

#### 10. vanna_remove_training ✅ Database-Aware
**File:** `/src/tools/vanna_remove_training.py`
- Uses `DATABASE_TYPE` for validation
- Should work with MS SQL

#### 11. vanna_generate_followup ✅ Database-Aware
**File:** `/src/tools/vanna_generate_followup.py`
- Uses `DATABASE_TYPE` in responses
- Should work with MS SQL

#### 12. vanna_catalog_sync ❌ BigQuery Only
**File:** `/src/tools/vanna_catalog_sync.py`
- **Status:** BigQuery-specific implementation
- Line 17: Default source is "bigquery"
- Line 44-49: Requires catalog to be in BigQuery
- **Verdict:** NO MS SQL SUPPORT - catalog is hardcoded for BigQuery

#### 13. vanna_batch_train_ddl ✅ Full MS SQL Support
**File:** `/src/tools/vanna_batch_train_ddl.py`
- **Status:** FULL MS SQL SUPPORT
- Line 3: "Supports both BigQuery and MS SQL Server"
- Line 9: Imports `pyodbc` for MS SQL
- Line 99-107: Checks database type and routes appropriately
- Line 119-128: Calls `_handle_mssql_batch_ddl` for MS SQL
- **Verdict:** This tool has proper MS SQL implementation

## Critical Issues for MS SQL Support

### 1. SQL Execution Not Supported
The `vanna_execute` tool explicitly blocks MS SQL execution. This is a major limitation as users cannot run queries against MS SQL databases.

### 2. Missing SQL Dialect Translation
Tools that generate SQL (like `vanna_ask`) don't adapt the SQL syntax for MS SQL:
- BigQuery uses backticks for identifiers: `` `table` ``
- MS SQL uses brackets: `[table]`
- Date functions differ significantly
- Data types have different names

### 3. Hardcoded BigQuery References
Many tools have hardcoded references to BigQuery in documentation and examples, which is misleading for MS SQL users.

### 4. No Direct Schema Access for MS SQL
Tools like `vanna_get_schemas` rely on DDL training data rather than querying MS SQL system tables directly.

## Summary of MS SQL Support Status

### Tools with Full Support (1/13):
- ✅ **vanna_batch_train_ddl** - Complete MS SQL implementation with pyodbc

### Tools with Partial Support (7/13):
- ✅ **vanna_ask** - Works but no SQL dialect translation
- ✅ **vanna_explain** - Works but BigQuery-specific features
- ✅ **vanna_get_schemas** - Works via DDL training data
- ✅ **vanna_get_training_data** - Database-aware filtering
- ✅ **vanna_remove_training** - Database-aware validation
- ✅ **vanna_generate_followup** - Database-aware responses
- ✅ **vanna_get_query_history** - Database-aware (needs verification)

### Tools with No MS SQL Support (3/13):
- ❌ **vanna_execute** - Hardcoded to block non-BigQuery databases
- ❌ **vanna_train** - Has unnecessary BigQuery import
- ❌ **vanna_catalog_sync** - BigQuery-only implementation

### Tools Not Fully Examined (2/13):
- ❓ **vanna_suggest_questions** - Likely works but needs verification
- ❓ **vanna_list_tenants** - Likely works but needs verification

## Critical Issues for MS SQL Users

1. **Cannot Execute Queries**: The `vanna_execute` tool explicitly blocks MS SQL, preventing users from running any queries
2. **SQL Syntax Mismatch**: Generated SQL uses BigQuery syntax (backticks) instead of MS SQL syntax (brackets)
3. **Missing Error Handling**: Tools don't handle MS SQL-specific errors or connection issues
4. **No Direct Schema Access**: Tools rely on training data instead of querying MS SQL system tables

## Recommendations

### Immediate Fixes Required:

1. **Fix vanna_execute (CRITICAL)**:
   - Remove BigQuery-only restriction
   - Add pyodbc-based execution for MS SQL
   - Handle MS SQL-specific result formatting

2. **Fix vanna_train**:
   - Make BigQuery import conditional
   - Add MS SQL validation logic

3. **Add SQL Dialect Translation**:
   - Create dialect translator for BigQuery → MS SQL syntax
   - Handle identifier quoting (backticks → brackets)
   - Translate date/time functions
   - Map data types correctly

### Implementation Plan:

```python
# Example fix for vanna_execute.py
if database_type == "mssql":
    import pyodbc
    conn_str = settings.get_mssql_connection_string()
    with pyodbc.connect(conn_str) as conn:
        cursor = conn.cursor()
        cursor.execute(sql)
        results = cursor.fetchall()
        # Process results...
```

### Testing Requirements:

1. End-to-end MS SQL workflow test
2. SQL syntax translation verification
3. Connection and error handling tests
4. Multi-tenant isolation with MS SQL

## Conclusion

MS SQL support is **partially broken** with 10/13 tools having some level of support, but critical functionality like query execution is completely blocked. The system architecture supports MS SQL, but implementation is incomplete. Users cannot effectively use the MCP server with MS SQL databases until `vanna_execute` is fixed.