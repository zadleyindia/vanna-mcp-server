# MS SQL Server Setup Guide for Vanna MCP Server

## Prerequisites

### 1. Install ODBC Driver for SQL Server

**macOS**:
```bash
# Install using Homebrew
brew tap microsoft/mssql-release https://github.com/Microsoft/homebrew-mssql-release
brew update
brew install msodbcsql17 mssql-tools

# Verify installation
odbcinst -q -d -n "ODBC Driver 17 for SQL Server"
```

**Alternative macOS installation**:
```bash
# Download directly from Microsoft
# https://docs.microsoft.com/en-us/sql/connect/odbc/linux-mac/install-microsoft-odbc-driver-sql-server-macos
```

### 2. Install Python Dependencies

```bash
# Activate your virtual environment first
cd /Users/mohit/claude/vanna-mcp-server

# Install pyodbc
pip install pyodbc

# Verify installation
python3 -c "import pyodbc; print(pyodbc.drivers())"
```

## Configuration Steps

### 1. Create Environment File

```bash
# Copy the example file
cp .env.mssql.example .env

# Edit with your actual values
nano .env
```

### 2. Configure MS SQL Connection

Update these values in your `.env` file:

```env
# Change database type to mssql
DATABASE_TYPE=mssql

# Your MS SQL Server details
MSSQL_SERVER=your-server.database.windows.net  # or IP address
MSSQL_DATABASE=your-database-name
MSSQL_USERNAME=your-username
MSSQL_PASSWORD=your-password

# Driver (verify this matches your installation)
MSSQL_DRIVER=ODBC Driver 17 for SQL Server

# Security settings
MSSQL_ENCRYPT=true  # For Azure SQL Database
MSSQL_TRUST_SERVER_CERTIFICATE=false  # Set to true for self-signed certs
```

### 3. Connection String Formats

The system will automatically build a connection string like:

```
DRIVER={ODBC Driver 17 for SQL Server};SERVER=your-server;DATABASE=your-db;UID=user;PWD=pass;Encrypt=yes
```

#### Common Connection Scenarios:

**Azure SQL Database**:
```env
MSSQL_SERVER=yourserver.database.windows.net
MSSQL_ENCRYPT=true
MSSQL_TRUST_SERVER_CERTIFICATE=false
```

**On-Premise SQL Server**:
```env
MSSQL_SERVER=192.168.1.100,1433  # IP,Port
MSSQL_ENCRYPT=false
MSSQL_TRUST_SERVER_CERTIFICATE=true
```

**Named Instance**:
```env
MSSQL_SERVER=SERVERNAME\\INSTANCENAME
```

## Testing the Connection

### 1. Test Script

Create `test_mssql_connection.py`:

```python
#!/usr/bin/env python3
import os
import pyodbc
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Build connection string
conn_parts = [
    f"DRIVER={{{os.getenv('MSSQL_DRIVER', 'ODBC Driver 17 for SQL Server')}}}",
    f"SERVER={os.getenv('MSSQL_SERVER')}",
    f"DATABASE={os.getenv('MSSQL_DATABASE')}",
    f"UID={os.getenv('MSSQL_USERNAME')}",
    f"PWD={os.getenv('MSSQL_PASSWORD')}"
]

if os.getenv('MSSQL_ENCRYPT', 'true').lower() == 'true':
    conn_parts.append("Encrypt=yes")

if os.getenv('MSSQL_TRUST_SERVER_CERTIFICATE', 'false').lower() == 'true':
    conn_parts.append("TrustServerCertificate=yes")

connection_string = ";".join(conn_parts)

print("Testing MS SQL Connection...")
print(f"Server: {os.getenv('MSSQL_SERVER')}")
print(f"Database: {os.getenv('MSSQL_DATABASE')}")

try:
    # Connect
    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()
    
    # Test query
    cursor.execute("SELECT @@VERSION")
    row = cursor.fetchone()
    print("\n✅ Connection successful!")
    print(f"SQL Server Version: {row[0]}")
    
    # List tables
    cursor.execute("""
        SELECT TABLE_SCHEMA, TABLE_NAME 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_SCHEMA, TABLE_NAME
    """)
    
    print("\nAvailable Tables:")
    for row in cursor.fetchall():
        print(f"  - {row[0]}.{row[1]}")
    
    conn.close()
    
except Exception as e:
    print(f"\n❌ Connection failed: {str(e)}")
    print("\nTroubleshooting:")
    print("1. Check your credentials")
    print("2. Verify server is accessible")
    print("3. Check firewall settings")
    print("4. Ensure ODBC driver is installed")
```

### 2. Run the Test

```bash
python3 test_mssql_connection.py
```

## Troubleshooting

### Common Issues

1. **"Driver not found" error**:
   ```bash
   # List available drivers
   python3 -c "import pyodbc; print(pyodbc.drivers())"
   
   # Update MSSQL_DRIVER in .env to match
   ```

2. **"Login failed" error**:
   - Verify username/password
   - Check SQL Server authentication mode
   - Ensure user has database access

3. **"Cannot open server" error**:
   - Check server name/IP
   - Verify port (default 1433)
   - Check firewall settings
   - For Azure SQL, ensure IP is whitelisted

4. **SSL/TLS errors**:
   - For self-signed certificates: `MSSQL_TRUST_SERVER_CERTIFICATE=true`
   - For older SQL Servers: `MSSQL_ENCRYPT=false`

## Training Vanna with MS SQL Data

Once connected, you can train Vanna with your MS SQL schema:

### 1. Extract DDL from MS SQL

```python
# The system will use MS SQL specific queries like:
SELECT 
    OBJECT_SCHEMA_NAME(t.object_id) AS schema_name,
    t.name AS table_name,
    c.name AS column_name,
    TYPE_NAME(c.user_type_id) AS data_type,
    c.max_length,
    c.precision,
    c.scale,
    c.is_nullable
FROM sys.tables t
JOIN sys.columns c ON t.object_id = c.object_id
ORDER BY schema_name, table_name, c.column_id
```

### 2. Use MCP Tools

Once configured, use the tools normally:
- `vanna_train` with type "ddl" will extract from MS SQL
- `vanna_ask` will generate MS SQL compatible queries
- `vanna_execute` will run against MS SQL

## Security Best Practices

1. **Use Least Privilege**:
   - Create a read-only user for Vanna
   - Grant only necessary permissions

2. **Network Security**:
   - Use SSL/TLS encryption
   - Restrict IP access
   - Use VPN for on-premise servers

3. **Credential Management**:
   - Never commit `.env` files
   - Use environment variables in production
   - Consider Azure Key Vault or similar

## Next Steps

1. Configure your `.env` file with MS SQL credentials
2. Test the connection using the test script
3. Train Vanna with your MS SQL schema
4. Start using natural language queries!

## Support

If you encounter issues:
1. Check the logs: `/Users/mohit/Library/Logs/Claude/mcp-server-vanna-mcp.log`
2. Verify ODBC driver installation
3. Test connection outside of Vanna first
4. Ensure all environment variables are set correctly