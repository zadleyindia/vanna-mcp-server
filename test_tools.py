#!/usr/bin/env python3
"""
Test script to verify MCP tools are working
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.tools.vanna_list_tenants import vanna_list_tenants
from src.tools.vanna_suggest_questions import vanna_suggest_questions
from src.tools.vanna_get_schemas import vanna_get_schemas

async def test_tools():
    """Test the MCP tools directly"""
    
    print("=== Testing MCP Tools ===\n")
    
    # Test 1: vanna_list_tenants
    print("1. Testing vanna_list_tenants...")
    try:
        result = await vanna_list_tenants()
        print(f"✅ Success: {result}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    print("\n" + "-"*50 + "\n")
    
    # Test 2: vanna_suggest_questions
    print("2. Testing vanna_suggest_questions...")
    try:
        result = await vanna_suggest_questions(limit=3)
        print(f"✅ Success: {result}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    print("\n" + "-"*50 + "\n")
    
    # Test 3: vanna_get_schemas
    print("3. Testing vanna_get_schemas...")
    try:
        result = await vanna_get_schemas(format_output="flat")
        print(f"✅ Success: {result}")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_tools())