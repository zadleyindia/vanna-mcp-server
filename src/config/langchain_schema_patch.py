"""
Monkey patch LangChain's PGVector to respect schema configuration
"""
import logging
from typing import Any, Dict, Optional
from langchain.vectorstores import pgvector

logger = logging.getLogger(__name__)

# Store the original PGVector class
_original_pgvector = pgvector.PGVector

class SchemaPatchedPGVector(_original_pgvector):
    """Patched PGVector that respects schema configuration"""
    
    def __init__(self, *args, **kwargs):
        """Initialize with schema support"""
        # Get schema from connection string or kwargs
        connection_string = kwargs.get('connection_string', args[0] if args else '')
        
        # Extract schema from search_path if present
        import re
        schema_match = re.search(r'search_path=([^,&\s]+)', connection_string)
        if schema_match:
            self.schema_name = schema_match.group(1)
        else:
            self.schema_name = kwargs.get('schema_name', 'public')
        
        logger.info(f"Initializing PGVector with schema: {self.schema_name}")
        
        # Call original init
        super().__init__(*args, **kwargs)
        
        # Override table names to include schema
        if self.schema_name != 'public':
            self._patch_table_names()
    
    def _patch_table_names(self):
        """Patch internal table references to use our schema"""
        # These are the tables LangChain creates
        self.CollectionStore.__table__.name = f"{self.schema_name}.langchain_pg_collection"
        self.EmbeddingStore.__table__.name = f"{self.schema_name}.langchain_pg_embedding"
        
        # Also patch the table creation queries if they exist
        if hasattr(self, '_create_tables'):
            original_create = self._create_tables
            
            def patched_create(*args, **kwargs):
                # Set schema before creating tables
                with self._session() as session:
                    session.execute(f"CREATE SCHEMA IF NOT EXISTS {self.schema_name}")
                    session.execute(f"SET search_path TO {self.schema_name}, public")
                    session.commit()
                
                # Call original create
                return original_create(*args, **kwargs)
            
            self._create_tables = patched_create
    
    def create_tables_if_not_exists(self) -> None:
        """Override to create tables in our schema"""
        with self._session() as session:
            # Ensure schema exists
            session.execute(f"CREATE SCHEMA IF NOT EXISTS {self.schema_name}")
            session.execute(f"SET search_path TO {self.schema_name}, public")
            session.commit()
        
        # Call parent method
        super().create_tables_if_not_exists()
        
        logger.info(f"Ensured tables exist in schema: {self.schema_name}")

def apply_langchain_schema_patch():
    """Apply the monkey patch to LangChain's PGVector"""
    logger.info("Applying LangChain schema patch...")
    
    # Replace the PGVector class with our patched version
    pgvector.PGVector = SchemaPatchedPGVector
    
    # Also patch the module-level reference if it exists
    if hasattr(pgvector, 'PGVector'):
        setattr(pgvector, 'PGVector', SchemaPatchedPGVector)
    
    logger.info("LangChain schema patch applied successfully")

# Apply the patch when this module is imported
apply_langchain_schema_patch()