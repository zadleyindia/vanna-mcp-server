#!/usr/bin/env python3
"""
Test script for catalog integration
"""
import asyncio
import sys
import os
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.config.settings import settings
from src.catalog_integration import CatalogQuerier, CatalogChunker, CatalogStorage

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_catalog_integration():
    """Test catalog integration components"""
    
    print("=== Catalog Integration Test ===\n")
    
    # Test 1: Configuration
    print("1. Testing Configuration...")
    print(f"   CATALOG_ENABLED: {settings.CATALOG_ENABLED}")
    print(f"   CATALOG_PROJECT: {settings.CATALOG_PROJECT}")
    print(f"   CATALOG_DATASET: {settings.CATALOG_DATASET}")
    print(f"   CHUNK_SIZE: {settings.CATALOG_CHUNK_SIZE}")
    print(f"   MAX_TOKENS: {settings.CATALOG_MAX_TOKENS}")
    
    if not settings.CATALOG_ENABLED:
        print("   ⚠️  Catalog integration is disabled")
        print("   Set CATALOG_ENABLED=true to enable")
        return
    
    print("   ✅ Configuration looks good\n")
    
    # Test 2: Sample JSON Loading
    print("2. Testing JSON Loading...")
    json_path = "/Users/mohit/claude/vanna-mcp-server/docs/data-catalog/CatalogExport_2025-06-21T14-01-13-904Z.json"
    
    if not os.path.exists(json_path):
        print(f"   ⚠️  Sample JSON not found: {json_path}")
        print("   Skipping JSON test")
    else:
        try:
            querier = CatalogQuerier()
            datasets, tables = await querier.fetch_from_json(json_path)
            print(f"   ✅ Loaded {len(datasets)} datasets, {len(tables)} tables")
            
            # Test 3: Chunking
            print("\n3. Testing Chunking...")
            chunker = CatalogChunker()
            
            if datasets and tables:
                # Test table context
                sample_dataset = datasets[0]
                sample_table = tables[0]
                
                table_context = chunker.chunk_table_context(sample_table, sample_dataset)
                print(f"   ✅ Table context chunk created: {len(table_context['context_chunk'])} chars")
                
                # Test column chunking
                columns = sample_table.get('columns', [])
                if columns:
                    column_chunks = chunker.chunk_columns(sample_table, columns)
                    print(f"   ✅ Column chunks created: {len(column_chunks)} chunks")
                
                # Test view chunking
                if sample_table.get('query'):
                    view_chunks = chunker.chunk_view_query(sample_table)
                    print(f"   ✅ View chunks created: {len(view_chunks)} chunks")
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
    
    # Test 4: Storage initialization (dry run)
    print("\n4. Testing Storage Setup...")
    try:
        storage = CatalogStorage()
        print("   ✅ Storage service initialized")
        
        # Note: We're not actually creating tables in test mode
        print("   ℹ️  Table creation skipped in test mode")
        
    except Exception as e:
        print(f"   ❌ Storage error: {str(e)}")
    
    # Test 5: BigQuery connectivity (if enabled)
    print("\n5. Testing BigQuery Connectivity...")
    
    if not settings.BIGQUERY_PROJECT:
        print("   ⚠️  BIGQUERY_PROJECT not set, skipping BigQuery test")
    else:
        try:
            from google.cloud import bigquery
            client = bigquery.Client(project=settings.BIGQUERY_PROJECT)
            
            # Test basic connectivity
            query = "SELECT 1 as test"
            result = list(client.query(query).result())
            print("   ✅ BigQuery connectivity working")
            
            # Test catalog access
            catalog_query = f"""
            SELECT COUNT(*) as table_count
            FROM `{settings.CATALOG_PROJECT}.{settings.CATALOG_DATASET}.Table_Metadata`
            WHERE status = 'In Use'
            LIMIT 1
            """
            
            try:
                result = list(client.query(catalog_query).result())
                table_count = result[0]['table_count']
                print(f"   ✅ Catalog access working: {table_count} active tables")
            except Exception as e:
                print(f"   ⚠️  Catalog access issue: {str(e)}")
                print("   This may be expected if catalog tables don't exist yet")
            
        except Exception as e:
            print(f"   ❌ BigQuery error: {str(e)}")
    
    print("\n=== Test Complete ===")
    print("\nNext steps:")
    print("1. If tests passed, try running: vanna_catalog_sync(mode='init')")
    print("2. Then run: vanna_catalog_sync(mode='full', dry_run=True)")
    print("3. If preview looks good: vanna_catalog_sync(mode='full')")

if __name__ == "__main__":
    asyncio.run(test_catalog_integration())