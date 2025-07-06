# Claude Desktop Quick Start Guide

## 🚀 5-Minute Setup

### 1. Prerequisites
- Claude Desktop installed
- Python 3.9+ installed
- PostgreSQL database with pgvector extension (we use Supabase)
- OpenAI API key

### 2. Quick Installation

```bash
# Clone the repository
git clone https://github.com/your-org/vanna-mcp-server.git
cd vanna-mcp-server

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies (includes forked Vanna with schema support)
pip install -r requirements.txt
```

### 3. Configure Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (Mac) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "vanna-mcp": {
      "command": "python",
      "args": ["/full/path/to/vanna-mcp-server/server.py"],
      "env": {
        "PYTHONPATH": "/full/path/to/vanna-mcp-server"
      },
      "config": {
        "OPENAI_API_KEY": "sk-proj-...",
        "SUPABASE_URL": "https://your-project.supabase.co",
        "SUPABASE_KEY": "eyJ...",  
        "SUPABASE_DB_PASSWORD": "your-actual-db-password",
        "DATABASE_TYPE": "bigquery",
        "VANNA_SCHEMA": "vanna_bigquery",
        "BIGQUERY_PROJECT": "your-project-id",
        "ENABLE_MULTI_TENANT": "false",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

### 4. Restart Claude Desktop

After saving the config, completely quit and restart Claude Desktop.

## 🎯 First Steps in Claude

### 1. Verify Installation
Ask Claude:
```
Can you list the available Vanna tools?
```

You should see:
- vanna_train
- vanna_ask
- vanna_list_training_data
- vanna_remove_training
- vanna_execute (if enabled)
- vanna_list_tenants (if multi-tenant enabled)

### 2. Add Your First Training Data

**For BigQuery:**
```
Use vanna_train to add this BigQuery DDL:
- Type: ddl
- Content: CREATE TABLE sales.orders (
    order_id INT64,
    customer_id INT64,
    order_date DATE,
    total_amount NUMERIC(10, 2),
    status STRING
  )
```

**For PostgreSQL:**
```
Use vanna_train to add this PostgreSQL DDL:
- Type: ddl  
- Content: CREATE TABLE sales.orders (
    order_id SERIAL PRIMARY KEY,
    customer_id INTEGER,
    order_date DATE,
    total_amount DECIMAL(10, 2),
    status VARCHAR(50)
  )
```

### 3. Train with Sample Queries

```
Use vanna_train to add this SQL example:
- Type: sql
- Question: Show me all orders from last month
- SQL: SELECT * FROM sales.orders 
       WHERE order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 MONTH)
       AND order_date < CURRENT_DATE()
```

### 4. Ask Your First Question

```
Use vanna_ask: What were the total sales last month?
```

Claude should generate appropriate SQL based on your database type and training data.

## 📊 Database-Specific Examples

### BigQuery Configuration
```json
{
  "DATABASE_TYPE": "bigquery",
  "VANNA_SCHEMA": "vanna_bigquery",
  "BIGQUERY_PROJECT": "your-project-id"
}
```

### PostgreSQL Configuration  
```json
{
  "DATABASE_TYPE": "postgres",
  "VANNA_SCHEMA": "vanna_postgres",
  "POSTGRES_CONNECTION_STRING": "postgresql://user:pass@host:5432/db"
}
```

### MS SQL Server Configuration
```json
{
  "DATABASE_TYPE": "mssql",
  "VANNA_SCHEMA": "vanna_mssql",
  "MSSQL_SERVER": "your-server.database.windows.net",
  "MSSQL_DATABASE": "your-database",
  "MSSQL_USERNAME": "your-username",
  "MSSQL_PASSWORD": "your-password"
}
```

## 🏢 Multi-Tenant Setup (Optional)

Enable multi-tenant mode:
```json
{
  "ENABLE_MULTI_TENANT": "true",
  "TENANT_ID": "acme_corp",
  "ALLOWED_TENANTS": "acme_corp,xyz_inc,contoso",
  "ENABLE_SHARED_KNOWLEDGE": "true"
}
```

Then in Claude:
```
List available tenants using vanna_list_tenants

Train tenant-specific data:
Use vanna_train with:
- Tenant ID: acme_corp
- Type: sql
- Question: Show ACME's top customers
- SQL: SELECT * FROM acme_customers ORDER BY revenue DESC LIMIT 10
```

## 🔍 Troubleshooting

### "No MCP tools available"
- Check Claude Desktop was fully restarted
- Verify the server path is correct
- Check logs: `~/Library/Logs/Claude/mcp-server-vanna-mcp.log`

### Database Connection Errors
- For Supabase: Use the database password, not the anon key
- Check your database is in the correct region
- Verify pgvector extension is installed

### Import Errors
```bash
# Verify the forked Vanna is installed:
pip show vanna | grep Location

# Reinstall if needed:
pip install --force-reinstall git+https://github.com/zadleyindia/vanna.git@add-metadata-support
```

## 💡 Pro Tips

1. **Start Simple**: Train with your actual table schemas first
2. **Be Specific**: Use descriptive questions when training
3. **Database Syntax**: Include database-specific SQL examples
4. **Iterate**: Add more training data as you discover gaps
5. **Monitor**: Check the MCP logs for detailed debugging

## 📚 Next Steps

1. Read the [Production Ready Guide](PRODUCTION_READY_GUIDE.md) for advanced features
2. Explore [Multi-Database Architecture](MULTI_DATABASE_MULTI_TENANT_ARCHITECTURE.md)
3. Learn about [Custom Schema Support](../METADATA_SUPPORT.md)
4. Run tests: `python scripts/test_production_simple.py`

## 🆘 Getting Help

1. **Check Logs**: 
   - MCP Server: `~/Library/Logs/Claude/mcp-server-vanna-mcp.log`
   - Set `LOG_LEVEL: "DEBUG"` for verbose output

2. **Test Connection**:
   ```bash
   python scripts/test_production_simple.py
   ```

3. **Verify Training Data**:
   ```
   Use vanna_list_training_data to see what's been trained
   ```

Happy querying! 🎉