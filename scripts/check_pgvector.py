#!/usr/bin/env python3
"""
Check if pgvector is available and provide installation instructions
"""
import sys
import psycopg2
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from src.config.settings import settings

def check_pgvector():
    """Check pgvector availability"""
    try:
        conn_string = settings.get_supabase_connection_string()
        conn = psycopg2.connect(conn_string)
        cursor = conn.cursor()
        
        print("Checking pgvector availability...")
        
        # Check if pgvector extension is available
        cursor.execute("""
            SELECT * FROM pg_available_extensions 
            WHERE name = 'vector'
        """)
        available = cursor.fetchone()
        
        if available:
            print(f"✅ pgvector is available (version: {available[2] or 'unknown'})")
            
            # Check if it's installed
            cursor.execute("""
                SELECT * FROM pg_extension 
                WHERE extname = 'vector'
            """)
            installed = cursor.fetchone()
            
            if installed:
                print("✅ pgvector is already installed")
            else:
                print("⚠️  pgvector is available but not installed")
                print("\nTrying to install pgvector...")
                
                try:
                    cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
                    conn.commit()
                    print("✅ pgvector installed successfully!")
                except Exception as e:
                    print(f"❌ Failed to install pgvector: {e}")
                    print("\nYou may need to enable it in Supabase dashboard:")
                    print("1. Go to your Supabase dashboard")
                    print("2. Navigate to Database > Extensions")
                    print("3. Search for 'vector' and enable it")
        else:
            print("❌ pgvector is not available in this database")
            print("\nFor Supabase:")
            print("1. Go to your Supabase dashboard")
            print("2. Navigate to Database > Extensions")
            print("3. Search for 'vector' and enable it")
            print("\nAlternatively, contact Supabase support if vector extension is not listed")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error checking pgvector: {e}")

if __name__ == "__main__":
    check_pgvector()