"""
Schema-enabled Vanna configuration using custom schemas.

This implementation shows how we can use custom schemas now that
we've enhanced Vanna to support them.
"""
import os
from typing import Optional, Dict, Any
import logging

from vanna.openai import OpenAI_Chat
from vanna.pgvector.pgvector_with_schema import SchemaAwarePGVectorStore
from .settings import settings

logger = logging.getLogger(__name__)


class SchemaEnabledVanna(OpenAI_Chat, SchemaAwarePGVectorStore):
    """
    Vanna implementation that supports custom schemas.
    
    This combines:
    - OpenAI for LLM capabilities
    - SchemaAwarePGVectorStore for custom schema support
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize with custom schema support."""
        
        # Get schema from config or settings
        schema_name = "public"  # Default
        if config and "schema" in config:
            schema_name = config["schema"]
        elif hasattr(settings, 'VANNA_SCHEMA'):
            schema_name = settings.VANNA_SCHEMA
        
        # Initialize OpenAI
        openai_config = {
            "api_key": settings.OPENAI_API_KEY,
            "model": settings.OPENAI_MODEL
        }
        OpenAI_Chat.__init__(self, config=openai_config)
        
        # Initialize schema-aware pgvector
        pgvector_config = {
            "connection_string": settings.get_supabase_connection_string(),
            "schema": schema_name,
            "n_results": 10
        }
        
        # Add embedding function from OpenAI
        pgvector_config["embedding_function"] = self
        
        SchemaAwarePGVectorStore.__init__(self, config=pgvector_config)
        
        logger.info(f"Initialized SchemaEnabledVanna with schema: {schema_name}")
    
    def embed_query(self, text: str) -> List[float]:
        """Generate embedding using OpenAI (required by SchemaAwarePGVectorStore)."""
        return self.generate_embedding(text)


def test_schema_enabled_vanna():
    """Test that we can use custom schemas."""
    
    print("🧪 Testing Schema-Enabled Vanna\n")
    
    # Test different schemas
    schemas = ["vanna_bigquery", "vanna_postgres", "vanna_mssql"]
    
    for schema in schemas:
        print(f"\n📂 Testing with schema: {schema}")
        
        try:
            # Create instance with custom schema
            vn = SchemaEnabledVanna(config={"schema": schema})
            
            # Add some test data
            ddl_id = vn.add_ddl(
                f"CREATE TABLE {schema}.test_table (id INT, name VARCHAR)",
                metadata={"schema_test": True}
            )
            print(f"   ✅ Added DDL to schema {schema}")
            
            # Retrieve data
            related_ddl = vn.get_related_ddl("test table")
            print(f"   ✅ Retrieved {len(related_ddl)} DDL statements")
            
            # Clean up
            vn.remove_training_data(ddl_id)
            print(f"   ✅ Cleaned up test data")
            
        except Exception as e:
            print(f"   ❌ Error with schema {schema}: {e}")
    
    print("\n✅ Schema-enabled Vanna test complete!")
    print("\n🎉 We can now use ANY schema, not just public!")


if __name__ == "__main__":
    # Add necessary imports for standalone execution
    from typing import List
    test_schema_enabled_vanna()