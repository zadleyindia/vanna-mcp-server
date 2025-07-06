#!/usr/bin/env python3
"""
Production-ready Vanna implementation with all features:
- Schema support from forked Vanna
- Multi-database support
- Multi-tenant isolation
- Metadata filtering
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json

from vanna.openai import OpenAI_Chat
from ..vanna_schema.pgvector_with_schema import SchemaAwarePGVectorStore
from ..config.settings import settings

logger = logging.getLogger(__name__)


class ProductionVanna(OpenAI_Chat, SchemaAwarePGVectorStore):
    """
    Production-ready Vanna implementation combining:
    - Schema support (from our fork)
    - Multi-database isolation
    - Multi-tenant support
    - Full metadata filtering
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize with all production features."""
        
        # Get configuration
        self.database_type = (config or {}).get("database_type", settings.DATABASE_TYPE)
        # Use the tenant_id from settings if multi-tenant is enabled
        if settings.ENABLE_MULTI_TENANT:
            self.tenant_id = (config or {}).get("tenant_id", settings.TENANT_ID) or settings.TENANT_ID
            if not self.tenant_id:
                raise ValueError("TENANT_ID is mandatory when ENABLE_MULTI_TENANT is true")
        else:
            self.tenant_id = None
        self.schema_name = (config or {}).get("schema", settings.VANNA_SCHEMA)
        
        # Initialize OpenAI for LLM capabilities
        openai_config = {
            "api_key": settings.OPENAI_API_KEY,
            "model": settings.OPENAI_MODEL
        }
        OpenAI_Chat.__init__(self, config=openai_config)
        
        # Initialize schema-aware pgvector with proper schema
        pgvector_config = {
            "connection_string": settings.get_supabase_connection_string(),
            "schema": self.schema_name,
            "n_results": 10,
            # Don't set embedding_function to avoid recursion
        }
        SchemaAwarePGVectorStore.__init__(self, config=pgvector_config)
        
        logger.info(
            f"Initialized ProductionVanna - "
            f"Schema: {self.schema_name}, "
            f"Database: {self.database_type}, "
            f"Tenant: {self.tenant_id}"
        )
    
    def generate_embedding_openai(self, text: str) -> List[float]:
        """Generate embedding using OpenAI."""
        # Use our configured embedding model instead of default ada-002
        import openai
        
        if not hasattr(self, '_openai_client'):
            self._openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        
        response = self._openai_client.embeddings.create(
            model=settings.OPENAI_EMBEDDING_MODEL,
            input=text,
            dimensions=1536  # Ensure we get 1536 dimensions
        )
        
        return response.data[0].embedding
    
    def _build_metadata(self, content_type: str, **kwargs) -> Dict[str, Any]:
        """Build metadata with all required fields."""
        metadata = {
            "content_type": content_type,
            "database_type": kwargs.get("database_type", self.database_type),
            "schema": self.schema_name,
            "created_at": datetime.now().isoformat(),
            "created_by": kwargs.get("created_by", "system")
        }
        
        # Add tenant information if multi-tenant is enabled
        if settings.ENABLE_MULTI_TENANT or kwargs.get("tenant_id"):
            if kwargs.get("is_shared", False):
                metadata["is_shared"] = "true"
                metadata["tenant_id"] = "shared"
            else:
                tenant_id = kwargs.get("tenant_id", self.tenant_id)
                if not tenant_id and settings.ENABLE_MULTI_TENANT:
                    raise ValueError(f"tenant_id is required in multi-tenant mode but got: {tenant_id}")
                if tenant_id:
                    metadata["tenant_id"] = tenant_id
        
        # Add any additional metadata
        for key, value in kwargs.items():
            if key not in ["database_type", "tenant_id", "is_shared", "created_by"] and value is not None:
                metadata[key] = value
        
        return metadata
    
    def add_question_sql(self, question: str, sql: str, **kwargs) -> str:
        """Add question-SQL pair with full metadata support."""
        # Build complete metadata
        metadata = self._build_metadata("sql", **kwargs)
        metadata["question"] = question
        metadata["sql"] = sql
        
        # Update kwargs with the metadata
        kwargs["metadata"] = metadata
        
        # Let parent handle the storage with metadata
        return super().add_question_sql(question, sql, **kwargs)
    
    def add_ddl(self, ddl: str, **kwargs) -> str:
        """Add DDL with full metadata support."""
        metadata = self._build_metadata("ddl", **kwargs)
        kwargs["metadata"] = metadata
        return super().add_ddl(ddl, **kwargs)
    
    def add_documentation(self, documentation: str, **kwargs) -> str:
        """Add documentation with full metadata support."""
        metadata = self._build_metadata("documentation", **kwargs)
        kwargs["metadata"] = metadata
        return super().add_documentation(documentation, **kwargs)
    
    def get_similar_question_sql(self, question: str, **kwargs) -> List[str]:
        """Get similar questions with metadata filtering."""
        # Build metadata filter
        metadata_filter = {
            "database_type": kwargs.get("database_type", self.database_type),
            "content_type": "sql"
        }
        
        # Add tenant filter if enabled
        if settings.ENABLE_MULTI_TENANT:
            tenant_id = kwargs.get("tenant_id", self.tenant_id)
            include_shared = kwargs.get("include_shared", settings.ENABLE_SHARED_KNOWLEDGE)
            
            if include_shared and tenant_id:
                # Get both tenant-specific and shared results
                tenant_results = super().get_similar_question_sql(
                    question, 
                    metadata_filter={**metadata_filter, "tenant_id": tenant_id}
                )
                shared_results = super().get_similar_question_sql(
                    question, 
                    metadata_filter={**metadata_filter, "is_shared": "true"}
                )
                # Combine and deduplicate
                all_results = list(set(tenant_results + shared_results))
                return all_results[:kwargs.get("k", 5)]
            elif tenant_id:
                metadata_filter["tenant_id"] = tenant_id
        
        return super().get_similar_question_sql(question, metadata_filter=metadata_filter)
    
    def get_related_ddl(self, question: str, **kwargs) -> List[str]:
        """Get related DDL with metadata filtering."""
        metadata_filter = {
            "database_type": kwargs.get("database_type", self.database_type),
            "content_type": "ddl"
        }
        
        # Add tenant filter if enabled
        if settings.ENABLE_MULTI_TENANT:
            tenant_id = kwargs.get("tenant_id", self.tenant_id)
            include_shared = kwargs.get("include_shared", settings.ENABLE_SHARED_KNOWLEDGE)
            
            if include_shared and tenant_id:
                # Get both tenant-specific and shared results
                tenant_results = super().get_related_ddl(
                    question, 
                    metadata_filter={**metadata_filter, "tenant_id": tenant_id}
                )
                shared_results = super().get_related_ddl(
                    question, 
                    metadata_filter={**metadata_filter, "is_shared": "true"}
                )
                # Combine and deduplicate
                all_results = list(set(tenant_results + shared_results))
                return all_results[:kwargs.get("k", 5)]
            elif tenant_id:
                metadata_filter["tenant_id"] = tenant_id
        
        logger.debug(f"get_related_ddl metadata_filter: {metadata_filter}")
        return super().get_related_ddl(question, metadata_filter=metadata_filter)
    
    def get_related_documentation(self, question: str, **kwargs) -> List[str]:
        """Get related documentation with metadata filtering."""
        metadata_filter = {
            "database_type": kwargs.get("database_type", self.database_type),
            "content_type": "documentation"
        }
        
        # Add tenant filter if enabled
        if settings.ENABLE_MULTI_TENANT:
            tenant_id = kwargs.get("tenant_id", self.tenant_id)
            include_shared = kwargs.get("include_shared", settings.ENABLE_SHARED_KNOWLEDGE)
            
            if include_shared and tenant_id:
                # Get both tenant-specific and shared results
                tenant_results = super().get_related_documentation(
                    question, 
                    metadata_filter={**metadata_filter, "tenant_id": tenant_id}
                )
                shared_results = super().get_related_documentation(
                    question, 
                    metadata_filter={**metadata_filter, "is_shared": "true"}
                )
                # Combine and deduplicate
                all_results = list(set(tenant_results + shared_results))
                return all_results[:kwargs.get("k", 5)]
            elif tenant_id:
                metadata_filter["tenant_id"] = tenant_id
        
        return super().get_related_documentation(question, metadata_filter=metadata_filter)
    
    def generate_sql(self, question: str, **kwargs) -> str:
        """Generate SQL with proper context filtering."""
        # Get filtering parameters
        database_type = kwargs.get("database_type", self.database_type)
        tenant_id = kwargs.get("tenant_id", self.tenant_id)
        include_shared = kwargs.get("include_shared", settings.ENABLE_SHARED_KNOWLEDGE)
        
        # Log the filtering parameters
        logger.info(f"SQL Generation Context - Tenant: {tenant_id}, Database: {database_type}, Include Shared: {include_shared}")
        
        # Get similar questions with filtering
        similar_sql = self.get_similar_question_sql(
            question, 
            database_type=database_type,
            tenant_id=tenant_id,
            include_shared=include_shared,
            k=3
        )
        logger.debug(f"Found {len(similar_sql)} similar SQL examples")
        
        # Get related DDL with filtering
        related_ddl = self.get_related_ddl(
            question,
            database_type=database_type,
            tenant_id=tenant_id,
            include_shared=include_shared,
            k=5
        )
        logger.debug(f"Found {len(related_ddl)} related DDL entries")
        if related_ddl:
            logger.info(f"DDL entries found for tenant {tenant_id}: {[ddl[:50] + '...' for ddl in related_ddl]}")
        
        # Get related documentation
        related_docs = self.get_related_documentation(
            question,
            database_type=database_type,
            tenant_id=tenant_id,
            include_shared=include_shared,
            k=3
        )
        logger.debug(f"Found {len(related_docs)} related documentation entries")
        
        # Build context
        context_parts = []
        
        # CRITICAL: In strict isolation mode, verify no cross-tenant data leaked
        if settings.STRICT_TENANT_ISOLATION and tenant_id:
            # Check DDL for cross-tenant references
            filtered_ddl = []
            for ddl in related_ddl:
                ddl_lower = ddl.lower()
                is_cross_tenant = False
                
                # Check if DDL contains tables from other tenants
                for other_tenant in settings.get_allowed_tenants():
                    if other_tenant != tenant_id and other_tenant.lower() in ddl_lower:
                        logger.warning(f"BLOCKED: Cross-tenant DDL found in strict mode - {ddl[:50]}...")
                        is_cross_tenant = True
                        break
                
                if not is_cross_tenant:
                    filtered_ddl.append(ddl)
            
            original_count = len(related_ddl)
            related_ddl = filtered_ddl
            if original_count != len(filtered_ddl):
                logger.info(f"Strict isolation: Filtered DDL from {original_count} to {len(filtered_ddl)} entries")
        
        if related_ddl:
            context_parts.append("=== Table Definitions ===")
            for ddl in related_ddl:
                context_parts.append(ddl)
        
        if related_docs:
            context_parts.append("\n=== Documentation ===")
            for doc in related_docs:
                context_parts.append(doc)
        
        if similar_sql:
            context_parts.append("\n=== Similar Examples ===")
            for sql in similar_sql:
                if isinstance(sql, dict):
                    # Format as "Question: ... \nSQL: ..."
                    context_parts.append(f"Question: {sql.get('question', 'N/A')}\nSQL: {sql.get('sql', 'N/A')}")
                else:
                    context_parts.append(str(sql))
        
        context = "\n".join(context_parts)
        
        # Generate SQL using LLM
        prompt_text = f"""Given the following context about a {database_type} database, generate SQL to answer this question:

{context}

Question: {question}

Generate only the SQL query without any explanation."""
        
        messages = [
            {"role": "system", "content": "You are a SQL expert. Generate only the SQL query without any explanation."},
            {"role": "user", "content": prompt_text}
        ]
        
        sql = self.submit_prompt(messages)
        
        # Log with full context for debugging
        logger.info(f"Generated SQL for {database_type}/{tenant_id}: {sql[:100]}...")
        logger.debug(f"Full SQL: {sql}")
        logger.debug(f"Context used: DDL count={len(related_ddl)}, Docs={len(related_docs)}, Examples={len(similar_sql)}")
        
        return sql
    
    def train(self, 
              question: Optional[str] = None,
              sql: Optional[str] = None,
              ddl: Optional[str] = None,
              documentation: Optional[str] = None,
              metadata: Optional[Dict[str, Any]] = None,
              **kwargs) -> bool:
        """Train with full metadata support."""
        try:
            # Merge provided metadata with kwargs
            all_metadata = kwargs.copy()
            if metadata:
                all_metadata.update(metadata)
            
            if question and sql:
                result = self.add_question_sql(question=question, sql=sql, **all_metadata)
                return bool(result)
            elif ddl:
                result = self.add_ddl(ddl=ddl, **all_metadata)
                return bool(result)
            elif documentation:
                result = self.add_documentation(documentation=documentation, **all_metadata)
                return bool(result)
            else:
                logger.warning("No training data provided")
                return False
        except Exception as e:
            logger.error(f"Training failed: {e}")
            return False
    
    def ask(self, question: str, **kwargs) -> str:
        """Ask a question (alias for generate_sql)."""
        return self.generate_sql(question, **kwargs)


class VannaMCP(ProductionVanna):
    """MCP-specific Vanna implementation with validation."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize with MCP-specific configuration."""
        super().__init__(config)
        logger.info("VannaMCP initialized with production features")
    
    def train(self, **kwargs) -> bool:
        """Train with MCP-specific validation."""
        # Validate SQL if provided
        if "sql" in kwargs and settings.MANDATORY_QUERY_VALIDATION:
            if not self._validate_sql_for_training(kwargs["sql"]):
                logger.warning(f"SQL validation failed for: {kwargs['sql'][:100]}...")
                return False
        
        return super().train(**kwargs)
    
    def _validate_sql_for_training(self, sql: str) -> bool:
        """Validate SQL before training."""
        import sqlparse
        
        # Parse SQL
        parsed = sqlparse.parse(sql)
        if not parsed:
            return False
        
        # Check if it's a SELECT statement
        stmt = parsed[0]
        if stmt.get_type() != 'SELECT':
            logger.warning(f"Non-SELECT statement rejected: {stmt.get_type()}")
            return False
        
        return True


# Singleton instance
_vanna_instance: Optional[VannaMCP] = None


def get_vanna() -> VannaMCP:
    """Get or create Vanna instance."""
    global _vanna_instance
    if _vanna_instance is None:
        # Pass configuration including tenant_id
        config = {
            "database_type": settings.DATABASE_TYPE,
            "tenant_id": settings.TENANT_ID,
            "schema": settings.VANNA_SCHEMA
        }
        _vanna_instance = VannaMCP(config=config)
    return _vanna_instance