# Claude Desktop Testing Checklist

## Pre-Test Checklist ✓

### 1. Dependencies Installed ✅
- Forked Vanna with schema support
- All Python dependencies from requirements.txt

### 2. Configuration Ready ✅
Your config should be in `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "vanna-mcp": {
      "command": "python",
      "args": ["/Users/mohit/claude/vanna-mcp-server/server.py"],
      "env": {
        "PYTHONPATH": "/Users/mohit/claude/vanna-mcp-server"
      },
      "config": {
        "OPENAI_API_KEY": "sk-proj-...",
        "SUPABASE_URL": "https://lohggakrufbclcccamaj.supabase.co",
        "SUPABASE_KEY": "eyJ...",
        "SUPABASE_DB_PASSWORD": "mP*t^xfEr2o*@!F",
        "BIGQUERY_PROJECT": "bigquerylascoot",
        "DATABASE_TYPE": "bigquery",
        "VANNA_SCHEMA": "vanna_bigquery",
        "ENABLE_MULTI_TENANT": "false",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

### 3. Database is Clean ✅
- All old schemas removed
- Fresh start with new schema isolation

## Testing Steps in Claude Desktop

### Step 1: Restart Claude Desktop
```
1. Completely quit Claude Desktop (Cmd+Q on Mac)
2. Start Claude Desktop again
3. Open a new conversation
```

### Step 2: Verify MCP Connection
Ask Claude:
```
Can you list the available Vanna MCP tools?
```

You should see:
- vanna_train
- vanna_ask
- vanna_list_training_data
- vanna_remove_training
- vanna_execute (if enabled)

### Step 3: Add Your First Training Data
```
Use vanna_train to add this BigQuery table schema:
- Type: ddl
- Content: CREATE TABLE sales.transactions (
    transaction_id STRING,
    customer_id INT64,
    product_id INT64,
    amount NUMERIC(10,2),
    transaction_date DATE,
    status STRING
  )
```

### Step 4: Add Example Query
```
Use vanna_train to add this SQL example:
- Type: sql
- Question: Show total sales by month for this year
- SQL: SELECT 
    FORMAT_DATE('%Y-%m', transaction_date) as month,
    SUM(amount) as total_sales
  FROM sales.transactions
  WHERE EXTRACT(YEAR FROM transaction_date) = EXTRACT(YEAR FROM CURRENT_DATE())
  GROUP BY month
  ORDER BY month
```

### Step 5: Test Query Generation
```
Use vanna_ask: What were the top 10 customers by total spending last month?
```

### Step 6: Verify Schema Isolation
Check the logs or ask:
```
Use vanna_list_training_data to show what's been trained
```

## Expected Results

✅ **Tools should be available immediately**
✅ **Training data stored in `vanna_bigquery` schema**
✅ **SQL generation uses BigQuery syntax**
✅ **No errors about schemas or connections**

## Troubleshooting

### If "No MCP tools available":
1. Check the server logs: `~/Library/Logs/Claude/mcp-server-vanna-mcp.log`
2. Verify the path in config is correct
3. Make sure Claude Desktop was fully restarted

### If connection errors:
1. Verify SUPABASE_DB_PASSWORD is the database password (not anon key)
2. Check if virtual environment has all dependencies

### If schema errors:
The schemas will be created automatically on first use!

## Quick Test Commands

Once connected, try these in sequence:
```
1. List available Vanna tools
2. Use vanna_train to add a simple DDL
3. Use vanna_ask to generate a query
4. Use vanna_list_training_data to see what's stored
```

## 🎯 You're Ready!

Everything is set up correctly. The system will:
- Create `vanna_bigquery` schema automatically
- Store all training data with proper isolation
- Generate BigQuery-specific SQL

Good luck with your testing! 🚀