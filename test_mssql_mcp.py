#!/usr/bin/env python3
"""
Test MS SQL Server connection using MCP configuration
This script should be run with the same environment variables as the MCP server
"""
import os
import sys
from pathlib import Path

def test_connection():
    """Test MS SQL connection using MCP configuration"""
    
    print("=== MS SQL MCP Connection Test ===\n")
    
    # Check if pyodbc is installed
    try:
        import pyodbc
        print("✅ pyodbc is installed")
        print(f"Available drivers: {pyodbc.drivers()}\n")
    except ImportError:
        print("❌ pyodbc is not installed!")
        print("The virtual environment should have pyodbc installed")
        return
    
    # Check MCP environment variables
    print("MCP Configuration:")
    print(f"  DATABASE_TYPE: {os.getenv('DATABASE_TYPE', 'not set')}")
    print(f"  MSSQL_SERVER: {os.getenv('MSSQL_SERVER', 'not set')}")
    print(f"  MSSQL_DATABASE: {os.getenv('MSSQL_DATABASE', 'not set')}")
    print(f"  MSSQL_USERNAME: {os.getenv('MSSQL_USERNAME', 'not set')}")
    print(f"  MSSQL_PASSWORD: {'*' * len(os.getenv('MSSQL_PASSWORD', '')) if os.getenv('MSSQL_PASSWORD') else 'not set'}")
    print(f"  MSSQL_DRIVER: {os.getenv('MSSQL_DRIVER', 'not set')}")
    print()
    
    # Check if we're in MS SQL mode
    if os.getenv('DATABASE_TYPE') != 'mssql':
        print("⚠️  DATABASE_TYPE is not set to 'mssql'")
        print("   The MCP server configuration should set DATABASE_TYPE=mssql")
        print()
    
    # Check required variables
    required_vars = ['MSSQL_SERVER', 'MSSQL_DATABASE', 'MSSQL_USERNAME', 'MSSQL_PASSWORD']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("❌ Missing environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nThese should be set in the MCP server configuration")
        print("in /Users/mohit/Library/Application Support/Claude/claude_desktop_config.json")
        return
    
    # Build connection string
    conn_parts = [
        f"DRIVER={{{os.getenv('MSSQL_DRIVER', 'ODBC Driver 18 for SQL Server')}}}",
        f"SERVER={os.getenv('MSSQL_SERVER')}",
        f"DATABASE={os.getenv('MSSQL_DATABASE')}",
        f"UID={os.getenv('MSSQL_USERNAME')}",
        f"PWD={os.getenv('MSSQL_PASSWORD')}"
    ]
    
    if os.getenv('MSSQL_ENCRYPT', 'false').lower() == 'true':
        conn_parts.append("Encrypt=yes")
    
    if os.getenv('MSSQL_TRUST_SERVER_CERTIFICATE', 'true').lower() == 'true':
        conn_parts.append("TrustServerCertificate=yes")
    
    connection_string = ";".join(conn_parts)
    
    try:
        print("Connecting to MS SQL Server...")
        
        # Connect
        conn = pyodbc.connect(connection_string, timeout=10)
        cursor = conn.cursor()
        
        # Test query
        cursor.execute("SELECT @@VERSION")
        row = cursor.fetchone()
        print("\n✅ Connection successful!")
        print(f"\nSQL Server Version:\n{row[0]}\n")
        
        # Get database info
        cursor.execute("SELECT DB_NAME()")
        db_name = cursor.fetchone()[0]
        print(f"Connected to database: {db_name}")
        
        # List schemas
        cursor.execute("""
            SELECT DISTINCT TABLE_SCHEMA 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_SCHEMA
        """)
        
        schemas = [row[0] for row in cursor.fetchall()]
        print(f"\nAvailable schemas: {', '.join(schemas)}")
        
        # Count tables
        cursor.execute("""
            SELECT COUNT(*) 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_TYPE = 'BASE TABLE'
        """)
        table_count = cursor.fetchone()[0]
        print(f"Total tables: {table_count}")
        
        # List first 10 tables
        cursor.execute("""
            SELECT TOP 10 TABLE_SCHEMA, TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_SCHEMA, TABLE_NAME
        """)
        
        print("\nSample tables:")
        for row in cursor.fetchall():
            print(f"  - {row[0]}.{row[1]}")
        
        if table_count > 10:
            print(f"  ... and {table_count - 10} more tables")
        
        conn.close()
        
        print("\n✅ MS SQL Server is ready for use with Vanna MCP Server!")
        print("\nThe vanna-mcp-mssql server in Claude Desktop should work correctly.")
        
    except pyodbc.Error as e:
        print(f"\n❌ Connection failed: {str(e)}")
        
        if "IM002" in str(e):
            print("\n⚠️  Driver not found!")
            print("Available drivers:", pyodbc.drivers())
            
        elif "28000" in str(e):
            print("\n⚠️  Authentication failed!")
            print("Check your username and password in the MCP configuration")
            
        elif "08001" in str(e):
            print("\n⚠️  Cannot connect to server!")
            print("Check:")
            print("- Server name/IP is correct")
            print("- Port 1433 is open")
            print("- Firewall allows connection")
            
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        print(f"Error type: {type(e).__name__}")

if __name__ == "__main__":
    # This simulates the MCP environment
    print("To test with MCP configuration, run with environment variables:")
    print("Example:")
    print('  DATABASE_TYPE=mssql MSSQL_SERVER=db.singlagroups.com MSSQL_DATABASE=zadley MSSQL_USERNAME=sa MSSQL_PASSWORD=cmFrZXNoMTc4 MSSQL_DRIVER="ODBC Driver 18 for SQL Server" python3 test_mssql_mcp.py')
    print()
    
    # If environment variables are set, run the test
    if os.getenv('MSSQL_SERVER'):
        test_connection()
    else:
        print("No MSSQL_SERVER environment variable found.")
        print("Testing with values from MCP config...")
        
        # Set the values from the MCP config
        os.environ['DATABASE_TYPE'] = 'mssql'
        os.environ['MSSQL_SERVER'] = 'db.singlagroups.com'
        os.environ['MSSQL_DATABASE'] = 'zadley'
        os.environ['MSSQL_USERNAME'] = 'sa'
        os.environ['MSSQL_PASSWORD'] = 'cmFrZXNoMTc4'
        os.environ['MSSQL_DRIVER'] = 'ODBC Driver 18 for SQL Server'
        os.environ['MSSQL_ENCRYPT'] = 'false'
        os.environ['MSSQL_TRUST_SERVER_CERTIFICATE'] = 'true'
        
        test_connection()