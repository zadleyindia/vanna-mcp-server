#!/usr/bin/env python3
"""
Test if query_history table auto-creates when needed
This simulates what happens when vanna_ask is called
"""
import sys
import asyncio
import logging
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_auto_create_table():
    """Test if the table auto-creates when we try to store history"""
    
    print("🧪 Testing Auto-Creation of Query History Table")
    print("=" * 50)
    
    try:
        # Import after path is set
        from src.tools.vanna_ask import _store_query_history
        from src.config.settings import settings
        
        print(f"Schema setting: {settings.VANNA_SCHEMA}")
        print(f"Multi-tenant: {settings.ENABLE_MULTI_TENANT}")
        
        # Try to store a test query - this should auto-create the table if it doesn't exist
        print("\n1. Testing query history storage (should auto-create table)...")
        
        await _store_query_history(
            query="Test query to check auto-creation",
            sql="SELECT 1 as test",
            execution_time_ms=100.0,
            confidence=0.9,
            tenant_id="test_tenant"
        )
        
        print("   ✅ Query history storage succeeded - table likely exists or was created")
        
        # Now try to retrieve to confirm it worked
        print("\n2. Testing query history retrieval...")
        
        from src.tools.vanna_get_query_history import vanna_get_query_history
        
        result = await vanna_get_query_history(limit=1)
        
        if result.get('queries'):
            print(f"   ✅ Retrieved {len(result['queries'])} queries")
            print(f"   📝 Latest query: {result['queries'][0].get('question', '')[:50]}...")
        else:
            print("   ⚠️  No queries found - table might be empty")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        print(f"   💡 This might mean the table doesn't exist and auto-creation failed")
        
        # Let's try to understand the error better
        error_str = str(e).lower()
        if 'relation' in error_str and 'does not exist' in error_str:
            print("   🔍 Detected 'relation does not exist' error")
            print("   📋 The table needs to be created manually in Supabase")
            return False
        elif 'permission' in error_str:
            print("   🔍 Detected permission error")
            print("   📋 Check database permissions")
            return False
        else:
            print(f"   🔍 Unknown error type: {error_str}")
            return False

async def main():
    """Main test function"""
    print("Starting auto-creation test...")
    print("Note: This test assumes MCP configuration is available from environment")
    
    success = await test_auto_create_table()
    
    if success:
        print("\n✅ Query history auto-creation test passed!")
        print("🎉 The table exists and is working correctly")
    else:
        print("\n❌ Query history auto-creation test failed")
        print("📋 You'll need to manually create the table using the SQL provided")

if __name__ == "__main__":
    asyncio.run(main())