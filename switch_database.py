#!/usr/bin/env python3
"""
Helper script to switch between database types
"""
import os
import sys
from pathlib import Path

def switch_database(db_type: str):
    """Switch DATABASE_TYPE in .env file"""
    
    env_file = Path(".env")
    
    if not env_file.exists():
        print(f"❌ No .env file found!")
        print("Create one from .env.mssql.example:")
        print("  cp .env.mssql.example .env")
        return
    
    # Read current .env
    with open(env_file, 'r') as f:
        lines = f.readlines()
    
    # Update DATABASE_TYPE
    updated = False
    new_lines = []
    
    for line in lines:
        if line.strip().startswith("DATABASE_TYPE="):
            new_lines.append(f"DATABASE_TYPE={db_type}\n")
            updated = True
        else:
            new_lines.append(line)
    
    # If DATABASE_TYPE wasn't found, add it
    if not updated:
        new_lines.insert(0, f"DATABASE_TYPE={db_type}\n")
    
    # Write back
    with open(env_file, 'w') as f:
        f.writelines(new_lines)
    
    print(f"✅ DATABASE_TYPE set to: {db_type}")
    
    # Show required variables for the selected type
    if db_type == "mssql":
        print("\nRequired MS SQL variables:")
        print("  - MSSQL_SERVER")
        print("  - MSSQL_DATABASE")
        print("  - MSSQL_USERNAME")
        print("  - MSSQL_PASSWORD")
        print("\nRun: python3 test_mssql_connection.py")
        
    elif db_type == "bigquery":
        print("\nRequired BigQuery variables:")
        print("  - BIGQUERY_PROJECT")
        print("  - GOOGLE_APPLICATION_CREDENTIALS (optional)")
        
    print("\nRestart the MCP server for changes to take effect")

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ["mssql", "bigquery", "postgres", "mysql"]:
        print("Usage: python3 switch_database.py [mssql|bigquery|postgres|mysql]")
        print("\nExample:")
        print("  python3 switch_database.py mssql")
        sys.exit(1)
    
    os.chdir(Path(__file__).parent)
    switch_database(sys.argv[1])