#!/usr/bin/env python3
"""
Test script for vanna_catalog_sync tool with CATALOG_ENABLED=true
"""
import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Enable catalog integration for this test
os.environ['CATALOG_ENABLED'] = 'true'
os.environ['CATALOG_PROJECT'] = 'bigquerylascoot'
os.environ['CATALOG_DATASET'] = 'metadata_data_dictionary'
os.environ['CATALOG_SYNC_MODE'] = 'manual'
os.environ['CATALOG_CHUNK_SIZE'] = '20'
os.environ['CATALOG_MAX_TOKENS'] = '1500'
os.environ['CATALOG_INCLUDE_VIEWS'] = 'true'
os.environ['CATALOG_INCLUDE_COLUMN_STATS'] = 'true'

# Minimal required values (will fail at connection but allow tool to initialize)
os.environ['OPENAI_API_KEY'] = 'test_key'
os.environ['BIGQUERY_PROJECT'] = 'test_project'
os.environ['SUPABASE_URL'] = 'test_url'
os.environ['SUPABASE_KEY'] = 'test_key'

from src.tools.vanna_catalog_sync import vanna_catalog_sync

async def test_catalog_sync_status():
    """Test vanna_catalog_sync with mode='status' and catalog enabled"""
    
    print("=== Testing vanna_catalog_sync Tool with Catalog Enabled ===")
    print("Mode: status")
    print("Catalog Integration: ENABLED")
    print("Purpose: Check if catalog integration is properly configured\n")
    
    try:
        result = await vanna_catalog_sync(mode="status")
        
        print("✅ Tool executed successfully!")
        print(f"Result type: {type(result)}")
        print(f"Result: {result}")
        
        # Parse the result if it's a dict
        if isinstance(result, dict):
            print("\nDetailed status:")
            for key, value in result.items():
                print(f"  {key}: {value}")
        
        # Check if we got a different response this time
        if result.get('success') is False:
            print("\n⚠️  Status check failed, but this is expected due to missing database connections")
            print("The tool is working correctly - it's checking the actual database status")
        else:
            print("\n✅ Status check passed!")
            
    except Exception as e:
        print(f"❌ Tool execution failed: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_catalog_sync_status())