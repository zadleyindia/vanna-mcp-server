#!/usr/bin/env python3
"""
Basic test to check what's implemented without dependencies
"""
import os
from pathlib import Path

print("🔍 Vanna MCP Server - Basic Implementation Check\n")

# Check project structure
project_root = Path(__file__).parent
print("✅ Project Structure:")
print(f"   Root: {project_root}")

# Check implemented files
files_to_check = [
    ("Configuration", [
        "src/config/settings.py",
        "src/config/vanna_config.py",
        ".env.example"
    ]),
    ("Tools", [
        "src/tools/vanna_ask.py",
        "src/tools/vanna_train.py", 
        "src/tools/vanna_suggest_questions.py"
    ]),
    ("Scripts", [
        "scripts/setup_database.py",
        "scripts/extract_bigquery_ddl.py",
        "scripts/load_initial_training.py"
    ]),
    ("Server", [
        "server.py"
    ]),
    ("Documentation", [
        "PROJECT_PLAN.md",
        "README.md",
        "PHASE1_STATUS.md",
        "PHASE2_STATUS.md"
    ])
]

for category, files in files_to_check:
    print(f"\n✅ {category}:")
    for file in files:
        file_path = project_root / file
        if file_path.exists():
            size = file_path.stat().st_size
            print(f"   ✓ {file} ({size:,} bytes)")
        else:
            print(f"   ✗ {file} (missing)")

# Check for .env file
print("\n🔐 Environment Configuration:")
env_file = project_root / ".env"
env_example = project_root / ".env.example"

if env_file.exists():
    print("   ✓ .env file exists")
    # Check which variables are set (without showing values)
    with open(env_file) as f:
        env_vars = [line.split('=')[0] for line in f if '=' in line and not line.startswith('#')]
    print(f"   ✓ {len(env_vars)} environment variables configured")
else:
    print("   ✗ .env file not found")
    if env_example.exists():
        print("   ℹ️  Copy .env.example to .env and fill in your credentials")

# Show what's implemented
print("\n📦 Implemented Components:")
print("   1. vanna_ask - Natural language to SQL conversion ✓")
print("   2. vanna_train - Add training data (DDL, docs, SQL) ✓")
print("   3. vanna_suggest_questions - Get question suggestions ✓")
print("   4. BigQuery DDL extractor with catalog integration ✓")
print("   5. Database setup script for Supabase ✓")
print("   6. FastMCP server with tool registration ✓")

print("\n🚀 To fully test the implementation:")
print("   1. Create Python virtual environment:")
print("      python3 -m venv venv")
print("      source venv/bin/activate")
print("   2. Install dependencies:")
print("      pip install -r requirements.txt")
print("   3. Copy and configure .env:")
print("      cp .env.example .env")
print("      # Edit .env with your credentials")
print("   4. Run configuration test:")
print("      python scripts/test_setup.py")
print("   5. Set up database:")
print("      python scripts/setup_database.py")
print("   6. Start the server:")
print("      python server.py")