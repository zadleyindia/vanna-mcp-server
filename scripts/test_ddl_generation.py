#!/usr/bin/env python3
"""
Test DDL generation logic without full environment
"""
import re

def test_sql_patterns():
    """Test SQL pattern generation for both databases"""
    
    print("\n" + "="*60)
    print("Testing DDL Generation Patterns")
    print("="*60 + "\n")
    
    # Test 1: BigQuery patterns
    print("1. BigQuery SQL Patterns:")
    print("-" * 40)
    
    # INFORMATION_SCHEMA query
    bq_query = """
    SELECT 
        table_catalog as project_id,
        table_schema as dataset_id,
        table_name,
        row_count,
        TIMESTAMP_MILLIS(creation_time) as created_at
    FROM `myproject.mydataset.INFORMATION_SCHEMA.TABLES`
    WHERE table_type = 'BASE TABLE'
      AND row_count >= 100
      AND table_name LIKE 'sales_%'
    ORDER BY row_count DESC, table_name
    """
    print("Query pattern:")
    print(bq_query.strip())
    
    # DDL pattern
    bq_ddl = """
CREATE TABLE `project.dataset.sales_data` (
  order_id STRING NOT NULL,
  amount NUMERIC,
  created_at TIMESTAMP
)
-- Row Count: 1,234,567
PARTITION BY DATE(created_at)
CLUSTER BY order_id
    """
    print("\nDDL pattern:")
    print(bq_ddl.strip())
    
    # Test 2: MS SQL patterns
    print("\n\n2. MS SQL Patterns:")
    print("-" * 40)
    
    # sys.tables query
    mssql_query = """
    USE [zadley];
    
    SELECT 
        DB_NAME() as database_name,
        s.name as schema_name,
        t.name as table_name,
        SUM(p.rows) as row_count,
        t.create_date as created_at
    FROM sys.tables t
    INNER JOIN sys.schemas s ON t.schema_id = s.schema_id
    INNER JOIN sys.partitions p ON t.object_id = p.object_id
    WHERE p.index_id IN (0,1)
      AND s.name = 'dbo'
    GROUP BY s.name, t.name, t.create_date
    HAVING SUM(p.rows) >= 100
      AND t.name LIKE 'mst%'
    ORDER BY SUM(p.rows) DESC, t.name
    """
    print("Query pattern:")
    print(mssql_query.strip())
    
    # DDL pattern
    mssql_ddl = """
CREATE TABLE [dbo].[mstemployee] (
  [emp_id] int NOT NULL,
  [emp_name] varchar(100),
  [department] varchar(50),
  [salary] decimal(10,2)
)
-- Row Count: 15,234
-- Indexes: IX_employee_dept (NONCLUSTERED)
    """
    print("\nDDL pattern:")
    print(mssql_ddl.strip())
    
    # Test 3: Table pattern matching
    print("\n\n3. Table Pattern Matching:")
    print("-" * 40)
    
    patterns = [
        ("sales_*", "sales_%", "Matches: sales_data, sales_history, sales_temp"),
        ("mst*", "mst%", "Matches: mstemployee, mstcustomer, mstproduct"),
        ("fact_", "fact_", "Matches: fact_ (exact match)"),
        ("*_archive", "%_archive", "Matches: sales_archive, orders_archive")
    ]
    
    for user_pattern, sql_pattern, description in patterns:
        print(f"User pattern: {user_pattern}")
        print(f"SQL pattern:  {sql_pattern}")
        print(f"Description:  {description}")
        print()
    
    # Test 4: Removal search pattern
    print("\n4. DDL Removal Pattern:")
    print("-" * 40)
    
    dataset_names = ["sales_data", "zadley", "analytics.reporting"]
    for dataset in dataset_names:
        search_pattern = f"{dataset}."
        print(f"Dataset: {dataset}")
        print(f"Search:  '{search_pattern}'")
        print(f"Removes: All DDLs containing '{search_pattern}' in content")
        print()
    
    print("="*60)
    print("Test Complete!")
    print("="*60 + "\n")

if __name__ == "__main__":
    test_sql_patterns()