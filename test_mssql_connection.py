#!/usr/bin/env python3
"""
Test MS SQL Server connection for Vanna MCP Server
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_connection():
    """Test MS SQL connection using configuration"""
    
    print("=== MS SQL Connection Test ===\n")
    
    # Check if pyodbc is installed
    try:
        import pyodbc
        print("✅ pyodbc is installed")
        print(f"Available drivers: {pyodbc.drivers()}\n")
    except ImportError:
        print("❌ pyodbc is not installed!")
        print("Run: pip install pyodbc")
        return
    
    # Check environment variables
    required_vars = ['MSSQL_SERVER', 'MSSQL_DATABASE', 'MSSQL_USERNAME', 'MSSQL_PASSWORD']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("❌ Missing environment variables:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nPlease set these in your .env file")
        return
    
    # Build connection string
    conn_parts = [
        f"DRIVER={{{os.getenv('MSSQL_DRIVER', 'ODBC Driver 18 for SQL Server')}}}",
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
    
    print("Configuration:")
    print(f"  Server: {os.getenv('MSSQL_SERVER')}")
    print(f"  Database: {os.getenv('MSSQL_DATABASE')}")
    print(f"  Username: {os.getenv('MSSQL_USERNAME')}")
    print(f"  Driver: {os.getenv('MSSQL_DRIVER', 'ODBC Driver 18 for SQL Server')}")
    print(f"  Encrypt: {os.getenv('MSSQL_ENCRYPT', 'true')}")
    print()
    
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
        print("\nNext steps:")
        print("1. Update DATABASE_TYPE=mssql in your .env file")
        print("2. Restart the MCP server")
        print("3. Train Vanna with your MS SQL schema using vanna_train")
        
    except pyodbc.Error as e:
        print(f"\n❌ Connection failed: {str(e)}")
        
        if "IM002" in str(e):
            print("\n⚠️  Driver not found!")
            print("Available drivers:", pyodbc.drivers())
            print("\nInstall ODBC Driver 18 for SQL Server:")
            print("brew install msodbcsql18")
            
        elif "28000" in str(e):
            print("\n⚠️  Authentication failed!")
            print("Check your username and password")
            print("Ensure SQL Server authentication is enabled")
            
        elif "08001" in str(e):
            print("\n⚠️  Cannot connect to server!")
            print("Check:")
            print("- Server name/IP is correct")
            print("- Port 1433 is open")
            print("- Firewall allows connection")
            print("- For Azure SQL, your IP is whitelisted")
            
        else:
            print("\nTroubleshooting tips:")
            print("1. Verify all connection parameters")
            print("2. Check network connectivity")
            print("3. Review SQL Server logs")
            print("4. Test with SQL Server Management Studio")
    
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        print(f"Error type: {type(e).__name__}")

if __name__ == "__main__":
    # Add project root to path
    sys.path.insert(0, str(Path(__file__).parent))
    
    # Check DATABASE_TYPE setting
    db_type = os.getenv('DATABASE_TYPE', 'bigquery')
    if db_type != 'mssql':
        print(f"⚠️  Note: DATABASE_TYPE is currently set to '{db_type}'")
        print("   Change to 'mssql' in your .env file to use MS SQL\n")
    
    test_connection()