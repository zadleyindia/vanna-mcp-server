#!/usr/bin/env python3
"""
Test the implemented Vanna tools locally (without MCP)
Run this after installing dependencies and configuring .env
"""
import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

async def test_tools():
    """Test each tool independently"""
    print("🧪 Testing Vanna MCP Tools\n")
    
    try:
        # Test configuration
        print("1️⃣ Testing Configuration...")
        from src.config.settings import settings
        config = settings.validate_config()
        if config['valid']:
            print("   ✅ Configuration valid")
        else:
            print("   ❌ Configuration errors:")
            for error in config['errors']:
                print(f"      - {error}")
            return
        
        # Test vanna connection
        print("\n2️⃣ Testing Vanna Connection...")
        from src.config.vanna_config import get_vanna
        vn = get_vanna()
        print("   ✅ Vanna initialized successfully")
        
        # Test vanna_suggest_questions (doesn't need training data)
        print("\n3️⃣ Testing vanna_suggest_questions...")
        from src.tools.vanna_suggest_questions import vanna_suggest_questions
        
        result = await vanna_suggest_questions(limit=3, include_metadata=False)
        if result['success']:
            print("   ✅ vanna_suggest_questions works!")
            print("   Suggestions:")
            for sugg in result['suggestions']:
                print(f"      - {sugg['question']}")
        else:
            print(f"   ❌ Error: {result.get('error', 'Unknown error')}")
        
        # Test vanna_train with DDL
        print("\n4️⃣ Testing vanna_train with sample DDL...")
        from src.tools.vanna_train import vanna_train
        
        sample_ddl = """
        CREATE TABLE test_table (
            id INT64,
            name STRING,
            created_at TIMESTAMP
        )
        """
        
        result = await vanna_train(
            training_type="ddl",
            content=sample_ddl,
            validate=False  # Skip validation for test
        )
        
        if result['success']:
            print("   ✅ vanna_train works!")
            print(f"   Training ID: {result['training_id']}")
        else:
            print(f"   ❌ Error: {result.get('message', 'Unknown error')}")
        
        # Test vanna_ask
        print("\n5️⃣ Testing vanna_ask...")
        from src.tools.vanna_ask import vanna_ask
        
        result = await vanna_ask(
            query="Show me all columns in test_table",
            include_explanation=True,
            include_confidence=True
        )
        
        if result['success']:
            print("   ✅ vanna_ask works!")
            if result.get('sql'):
                print(f"   Generated SQL: {result['sql'][:100]}...")
            if result.get('explanation'):
                print(f"   Explanation: {result['explanation'][:100]}...")
        else:
            print(f"   ❌ Error: {result.get('error', 'Unknown error')}")
            if result.get('suggestions'):
                print("   Suggestions:")
                for sugg in result['suggestions'][:3]:
                    print(f"      - {sugg}")
        
        print("\n✅ All basic tests completed!")
        print("\nNext steps:")
        print("1. Run scripts/load_initial_training.py to load your BigQuery data")
        print("2. Start the MCP server with: python server.py")
        print("3. Use the tools through Claude Desktop")
        
    except ImportError as e:
        print(f"\n❌ Import Error: {e}")
        print("\nMake sure you have:")
        print("1. Created a virtual environment: python3 -m venv venv")
        print("2. Activated it: source venv/bin/activate")
        print("3. Installed dependencies: pip install -r requirements.txt")
        print("4. Created .env file with your credentials")
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_tools())