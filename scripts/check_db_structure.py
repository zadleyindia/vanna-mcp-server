#!/usr/bin/env python3
"""Check existing database structure."""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.config.settings import settings
from sqlalchemy import create_engine, text

def check_structure():
    """Check existing table structure."""
    connection_string = settings.get_supabase_connection_string()
    engine = create_engine(connection_string)
    
    with engine.connect() as conn:
        # Check embedding table columns
        result = conn.execute(text("""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'langchain_pg_embedding'
            ORDER BY ordinal_position
        """))
        
        print("langchain_pg_embedding columns:")
        for row in result:
            print(f"  - {row.column_name}: {row.data_type}")
        
        # Check for vector type
        result = conn.execute(text("""
            SELECT typname FROM pg_type WHERE typname = 'vector'
        """))
        
        has_vector = result.fetchone() is not None
        print(f"\nVector type available: {has_vector}")
        
        # Check indexes
        result = conn.execute(text("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'langchain_pg_embedding'
        """))
        
        print("\nExisting indexes:")
        for row in result:
            print(f"  - {row.indexname}")

if __name__ == "__main__":
    check_structure()