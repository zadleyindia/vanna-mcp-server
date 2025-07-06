#!/usr/bin/env python3
"""
Test script for query history functionality
Run this after creating the query_history table in Supabase
"""
import sys
import asyncio
import logging
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.tools.vanna_ask import _store_query_history
from src.tools.vanna_get_query_history import vanna_get_query_history
from src.config.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_query_history():
    """Test the query history functionality"""
    
    print("🧪 Testing Query History Functionality")
    print("=" * 50)
    
    # Test 1: Store some sample query history
    print("\n1. Testing query history storage...")
    
    test_queries = [
        {
            "query": "Show me total sales for this month",
            "sql": "SELECT SUM(amount) FROM sales WHERE DATE(created_at) >= DATE_TRUNC('month', CURRENT_DATE)",
            "execution_time_ms": 1250.0,
            "confidence": 0.85,
            "tenant_id": "zadley"
        },
        {
            "query": "List top 10 customers by revenue",
            "sql": "SELECT customer_id, SUM(amount) as revenue FROM orders GROUP BY customer_id ORDER BY revenue DESC LIMIT 10",
            "execution_time_ms": 890.0,
            "confidence": 0.92,
            "tenant_id": "zadley"
        },
        {
            "query": "Show inventory levels",
            "sql": "SELECT product_id, stock_quantity FROM inventory WHERE stock_quantity > 0",
            "execution_time_ms": 450.0,
            "confidence": 0.78,
            "tenant_id": "zadley_retail"
        }
    ]
    
    for i, test_data in enumerate(test_queries, 1):
        try:
            await _store_query_history(
                query=test_data["query"],
                sql=test_data["sql"],
                execution_time_ms=test_data["execution_time_ms"],
                confidence=test_data["confidence"],
                tenant_id=test_data["tenant_id"]
            )
            print(f"   ✅ Stored test query {i}")
        except Exception as e:
            print(f"   ❌ Failed to store test query {i}: {e}")
            return False
    
    # Test 2: Retrieve query history
    print("\n2. Testing query history retrieval...")
    
    try:
        # Get all queries
        result = await vanna_get_query_history(limit=10, include_analytics=True)
        print(f"   ✅ Retrieved {len(result.get('queries', []))} queries")
        
        if result.get('analytics'):
            analytics = result['analytics']
            print(f"   📊 Average execution time: {analytics.get('average_execution_time_ms', 0):.1f}ms")
            print(f"   📊 Average confidence: {analytics.get('average_confidence_score', 0):.2f}")
            print(f"   📊 High confidence queries: {analytics.get('queries_by_confidence', {}).get('high_confidence', 0)}")
        
    except Exception as e:
        print(f"   ❌ Failed to retrieve query history: {e}")
        return False
    
    # Test 3: Test tenant filtering (if multi-tenant enabled)
    if settings.ENABLE_MULTI_TENANT:
        print("\n3. Testing tenant filtering...")
        
        try:
            # Get queries for specific tenant
            zadley_result = await vanna_get_query_history(tenant_id="zadley", limit=10)
            retail_result = await vanna_get_query_history(tenant_id="zadley_retail", limit=10)
            
            print(f"   ✅ Zadley queries: {len(zadley_result.get('queries', []))}")
            print(f"   ✅ Retail queries: {len(retail_result.get('queries', []))}")
            
            # Verify tenant isolation
            for query in zadley_result.get('queries', []):
                if query.get('tenant_id') not in [None, 'zadley']:
                    print(f"   ❌ Cross-tenant leak detected: {query.get('tenant_id')}")
                    return False
            
            print("   ✅ Tenant isolation working correctly")
            
        except Exception as e:
            print(f"   ❌ Failed tenant filtering test: {e}")
            return False
    else:
        print("\n3. Multi-tenant disabled, skipping tenant filtering test")
    
    # Test 4: Check table structure
    print("\n4. Testing table access...")
    
    try:
        from supabase import create_client
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        
        # Try to count records
        result = supabase.table("query_history").select("id", count="exact").execute()
        print(f"   ✅ Total records in query_history: {result.count}")
        
    except Exception as e:
        print(f"   ❌ Failed to access query_history table: {e}")
        print(f"   💡 Make sure you've run the SQL to create the table in Supabase")
        return False
    
    print("\n🎉 All tests passed! Query history is working correctly.")
    return True

async def main():
    """Main test function"""
    
    # Check basic configuration
    required_config = ['SUPABASE_URL', 'SUPABASE_KEY']
    missing_config = [key for key in required_config if not getattr(settings, key)]
    
    if missing_config:
        print(f"❌ Missing configuration: {', '.join(missing_config)}")
        print("Please set these in your environment or .env file")
        return
    
    print(f"Configuration:")
    print(f"  Database Type: {settings.DATABASE_TYPE}")
    print(f"  Multi-tenant: {settings.ENABLE_MULTI_TENANT}")
    print(f"  Default Tenant: {settings.TENANT_ID}")
    print(f"  Schema: {settings.VANNA_SCHEMA}")
    
    # Run tests
    success = await test_query_history()
    
    if success:
        print("\n✅ Query history functionality is ready!")
    else:
        print("\n❌ Some tests failed. Check the errors above.")

if __name__ == "__main__":
    asyncio.run(main())