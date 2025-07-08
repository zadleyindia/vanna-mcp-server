#!/usr/bin/env python3
"""
Test script for vanna_catalog_sync tool with mode="status"
"""
import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Set test environment
os.environ['DOTENV_PATH'] = '/Users/mohit/claude/vanna-mcp-server/.env.test'

from src.tools.vanna_catalog_sync import vanna_catalog_sync

async def test_catalog_sync_status():
    """Test vanna_catalog_sync with mode='status'"""
    
    print("=== Testing vanna_catalog_sync Tool ===")
    print("Mode: status")
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
        
    except Exception as e:
        print(f"❌ Tool execution failed: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_catalog_sync_status())