#!/usr/bin/env python3
"""
Validate vanna_batch_train_ddl tool implementation
Checks the code logic without requiring full environment
"""
import ast
import re
from pathlib import Path

def validate_ddl_tool():
    """Validate the batch DDL tool implementation"""
    
    print("\n" + "="*60)
    print("Validating vanna_batch_train_ddl Implementation")
    print("="*60 + "\n")
    
    # Read the tool file
    tool_path = Path(__file__).parent.parent / "src/tools/vanna_batch_train_ddl.py"
    with open(tool_path, 'r') as f:
        content = f.read()
    
    # Parse the AST
    tree = ast.parse(content)
    
    # 1. Check main function signature
    print("1. Checking function signature...")
    main_func = None
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "vanna_batch_train_ddl":
            main_func = node
            break
    
    if main_func:
        params = [arg.arg for arg in main_func.args.args]
        print(f"   ✓ Function found with parameters: {params}")
        
        # Check required parameters
        required_params = ["dataset_id", "tenant_id", "min_row_count", "include_row_counts", 
                          "table_pattern", "dry_run", "remove_existing"]
        for param in required_params:
            if param in params:
                print(f"   ✓ Parameter '{param}' present")
            else:
                print(f"   ✗ Parameter '{param}' missing!")
    else:
        print("   ✗ Main function not found!")
    
    # 2. Check database routing
    print("\n2. Checking database routing...")
    if "database_type == \"bigquery\"" in content and "database_type == \"mssql\"" in content:
        print("   ✓ Both BigQuery and MS SQL routing found")
        
        # Check handler functions
        if "_handle_bigquery_batch_ddl" in content:
            print("   ✓ BigQuery handler function found")
        if "_handle_mssql_batch_ddl" in content:
            print("   ✓ MS SQL handler function found")
    else:
        print("   ✗ Database routing not properly implemented")
    
    # 3. Check SQL queries
    print("\n3. Checking database-specific SQL queries...")
    
    # BigQuery query pattern
    bq_pattern = r'FROM\s+`[^`]+\.INFORMATION_SCHEMA\.TABLES`'
    if re.search(bq_pattern, content):
        print("   ✓ BigQuery INFORMATION_SCHEMA query found")
    
    # MS SQL query pattern  
    mssql_pattern = r'FROM\s+sys\.tables.*sys\.partitions'
    if re.search(mssql_pattern, content, re.DOTALL):
        print("   ✓ MS SQL sys.tables query found")
    
    # Check row count handling
    if "row_count >=" in content:
        print("   ✓ Row count filtering implemented")
    
    # Check table pattern
    if "table_pattern" in content and "LIKE" in content:
        print("   ✓ Table pattern filtering implemented")
    
    # 4. Check DDL generation
    print("\n4. Checking DDL generation...")
    if "_generate_bigquery_ddl" in content:
        print("   ✓ BigQuery DDL generator found")
        # Check for BigQuery-specific features
        if "PARTITION BY" in content and "CLUSTER BY" in content:
            print("   ✓ BigQuery partitioning/clustering support")
    
    if "_generate_mssql_ddl" in content:
        print("   ✓ MS SQL DDL generator found")
        # Check for MS SQL-specific features
        if "CONSTRAINT" in content and "PRIMARY KEY" in content:
            print("   ✓ MS SQL constraint support")
    
    # 5. Check removal logic
    print("\n5. Checking DDL removal logic...")
    if "remove_existing" in content and "_remove_existing_ddls" in content:
        print("   ✓ DDL removal function found")
        if "vanna_get_training_data" in content and "vanna_remove_training" in content:
            print("   ✓ Uses existing tools for removal")
    
    # 6. Check response format
    print("\n6. Checking response format...")
    response_fields = ["success", "database_type", "dataset_processed", "tables_trained", 
                      "tables_skipped", "removed_count", "errors", "dry_run"]
    for field in response_fields:
        if f'"{field}"' in content:
            print(f"   ✓ Response field '{field}' included")
    
    # 7. Validate SQL patterns
    print("\n7. Validating SQL generation patterns...")
    
    # Check BigQuery SQL
    print("\n   BigQuery SQL patterns:")
    if re.search(r'CREATE TABLE `[^`]+`', content):
        print("   ✓ Uses backticks for identifiers")
    if "STRING" in content and "INT64" in content:
        print("   ✓ Uses BigQuery data types")
    
    # Check MS SQL patterns
    print("\n   MS SQL patterns:")
    if re.search(r'CREATE TABLE \[[^\]]+\]', content):
        print("   ✓ Uses square brackets for identifiers")
    if "VARCHAR" in content and "BIGINT" in content:
        print("   ✓ Uses MS SQL data types")
    
    print("\n" + "="*60)
    print("Validation Complete!")
    print("="*60 + "\n")

if __name__ == "__main__":
    validate_ddl_tool()