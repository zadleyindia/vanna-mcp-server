#!/usr/bin/env python3
"""
Test script for vanna_batch_train_ddl tool
Tests both BigQuery and MS SQL functionality
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.tools.vanna_batch_train_ddl import vanna_batch_train_ddl
from src.config.settings import settings

async def test_batch_ddl():
    """Test the batch DDL training tool"""
    
    print(f"\n{'='*60}")
    print(f"Testing vanna_batch_train_ddl")
    print(f"Database Type: {settings.DATABASE_TYPE}")
    print(f"{'='*60}\n")
    
    # Test 1: Dry run to see what would be processed
    print("Test 1: Dry run (preview mode)")
    print("-" * 40)
    
    if settings.DATABASE_TYPE == "bigquery":
        # Test with a BigQuery dataset
        result = await vanna_batch_train_ddl(
            dataset_id="test_dataset",  # Change to your dataset
            min_row_count=1,
            dry_run=True
        )
    else:  # mssql
        # Test with MS SQL database
        result = await vanna_batch_train_ddl(
            dataset_id="zadley",  # Change to your database
            min_row_count=1,
            dry_run=True
        )
    
    print(f"Success: {result.get('success')}")
    print(f"Dataset: {result.get('dataset_processed')}")
    print(f"Tables found: {len(result.get('tables_trained', []))}")
    
    if result.get('success'):
        for table in result.get('tables_trained', [])[:5]:  # Show first 5
            print(f"  - {table['table']}: {table['row_count']:,} rows")
        
        if len(result.get('tables_trained', [])) > 5:
            print(f"  ... and {len(result['tables_trained']) - 5} more tables")
    else:
        print(f"Error: {result.get('error')}")
        if result.get('suggestions'):
            print("Suggestions:")
            for suggestion in result['suggestions']:
                print(f"  - {suggestion}")
    
    print()
    
    # Test 2: Test with table pattern
    print("\nTest 2: Filter with table pattern")
    print("-" * 40)
    
    if settings.DATABASE_TYPE == "bigquery":
        result2 = await vanna_batch_train_ddl(
            dataset_id="test_dataset",
            table_pattern="test_*",  # Only tables starting with 'test_'
            min_row_count=100,
            dry_run=True
        )
    else:  # mssql
        result2 = await vanna_batch_train_ddl(
            dataset_id="zadley",
            table_pattern="mst*",  # Only tables starting with 'mst'
            min_row_count=100,
            dry_run=True
        )
    
    print(f"Success: {result2.get('success')}")
    print(f"Tables matching pattern: {len(result2.get('tables_trained', []))}")
    print(f"Min row count filter: {result2.get('summary', {}).get('min_row_count_used')}")
    
    # Test 3: Test with higher row count threshold
    print("\nTest 3: High row count threshold")
    print("-" * 40)
    
    if settings.DATABASE_TYPE == "bigquery":
        result3 = await vanna_batch_train_ddl(
            dataset_id="test_dataset",
            min_row_count=10000,  # Only tables with 10k+ rows
            dry_run=True
        )
    else:  # mssql
        result3 = await vanna_batch_train_ddl(
            dataset_id="zadley",
            min_row_count=5000,  # Only tables with 5k+ rows
            dry_run=True
        )
    
    print(f"Success: {result3.get('success')}")
    print(f"Large tables found: {len(result3.get('tables_trained', []))}")
    print(f"Total rows represented: {result3.get('summary', {}).get('total_rows_represented', 0):,}")
    
    # Show skipped tables
    if result3.get('tables_skipped'):
        print(f"\nTables skipped (low row count): {len(result3['tables_skipped'])}")
        for table in result3['tables_skipped'][:3]:
            print(f"  - {table['table']}: {table['row_count']} rows")
    
    print(f"\n{'='*60}")
    print("Test complete!")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    # Run the async test
    asyncio.run(test_batch_ddl())