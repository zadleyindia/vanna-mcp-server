#!/usr/bin/env python3
"""
Vanna integration with filtered vector store for proper metadata filtering.

This module bridges our custom FilteredPGVectorStore with Vanna to enable
true multi-database and multi-tenant isolation.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
import os
from datetime import datetime

from vanna.openai import OpenAI_Chat
from vanna.base import VannaBase

from src.vector_stores.filtered_pgvector import FilteredPGVectorStore
from src.config.settings import settings

logger = logging.getLogger(__name__)


class FilteredVectorVanna(OpenAI_Chat):
    """
    Vanna implementation using FilteredPGVectorStore for proper metadata filtering.
    
    This class overrides Vanna's vector store methods to use our custom implementation
    that supports metadata filtering during similarity search.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize with custom vector store."""
        # Initialize OpenAI_Chat for LLM capabilities
        openai_config = {
            "api_key": config.get("api_key") if config else settings.OPENAI_API_KEY,
            "model": config.get("model", settings.OPENAI_MODEL) if config else settings.OPENAI_MODEL
        }
        super().__init__(config=openai_config)
        
        # Initialize our custom vector store
        connection_string = settings.get_supabase_connection_string()
        self.vector_store = FilteredPGVectorStore(
            connection_string=connection_string,
            collection_name="vanna_embeddings",
            embedding_dimension=1536,
            skip_schema_init=True  # We're working with existing Vanna tables
        )
        
        # Store config for metadata generation
        self.config = config or {}
        self.database_type = self.config.get("database_type", settings.DATABASE_TYPE)
        self.tenant_id = self.config.get("tenant_id", settings.TENANT_ID)
        
        # Store API key for embedding generation
        self.api_key = openai_config.get("api_key", settings.OPENAI_API_KEY)
        
        logger.info(f"Initialized FilteredVectorVanna for database_type={self.database_type}, tenant_id={self.tenant_id}")
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI."""
        import openai
        
        client = openai.OpenAI(api_key=self.api_key)
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    
    def add_question_sql(self, question: str, sql: str, **kwargs) -> str:
        """Add a question-SQL pair with metadata filtering support."""
        # Extract metadata from kwargs
        metadata = self._build_metadata("sql", **kwargs)
        metadata["question"] = question
        metadata["sql"] = sql
        
        # Create document content
        document = f"Question: {question}\nSQL: {sql}"
        
        # Generate embedding
        embedding = self.generate_embedding(document)
        
        # Add to vector store
        ids = self.vector_store.add_documents(
            documents=[document],
            embeddings=[embedding],
            metadatas=[metadata]
        )
        
        logger.info(f"Added question-SQL pair with metadata: {metadata}")
        return ids[0]
    
    def add_ddl(self, ddl: str, **kwargs) -> str:
        """Add DDL with metadata filtering support."""
        # Extract metadata from kwargs
        metadata = self._build_metadata("ddl", **kwargs)
        
        # Generate embedding
        embedding = self.generate_embedding(ddl)
        
        # Add to vector store
        ids = self.vector_store.add_documents(
            documents=[ddl],
            embeddings=[embedding],
            metadatas=[metadata]
        )
        
        logger.info(f"Added DDL with metadata: {metadata}")
        return ids[0]
    
    def add_documentation(self, documentation: str, **kwargs) -> str:
        """Add documentation with metadata filtering support."""
        # Extract metadata from kwargs
        metadata = self._build_metadata("documentation", **kwargs)
        
        # Generate embedding
        embedding = self.generate_embedding(documentation)
        
        # Add to vector store
        ids = self.vector_store.add_documents(
            documents=[documentation],
            embeddings=[embedding],
            metadatas=[metadata]
        )
        
        logger.info(f"Added documentation with metadata: {metadata}")
        return ids[0]
    
    def get_similar_question_sql(self, question: str, **kwargs) -> List[str]:
        """
        Get similar question-SQL pairs with metadata filtering.
        
        This is the key method that enables proper filtering.
        """
        # Get filtering parameters
        database_type = kwargs.get("database_type", self.database_type)
        tenant_id = kwargs.get("tenant_id", self.tenant_id)
        include_shared = kwargs.get("include_shared", settings.ENABLE_SHARED_KNOWLEDGE)
        k = kwargs.get("k", 5)
        
        # Generate query embedding
        query_embedding = self.generate_embedding(question)
        
        # Build metadata filter
        metadata_filter = {
            "database_type": database_type,
            "content_type": "sql"  # Only get SQL examples
        }
        
        results = []
        
        if settings.ENABLE_MULTI_TENANT and tenant_id:
            if include_shared:
                # Get both tenant-specific and shared results
                # First get tenant-specific
                tenant_filter = {**metadata_filter, "tenant_id": tenant_id}
                tenant_results = self.vector_store.similarity_search_with_score_and_filter(
                    query_embedding, k=k, metadata_filter=tenant_filter
                )
                
                # Then get shared
                shared_filter = {**metadata_filter, "is_shared": "true"}
                shared_results = self.vector_store.similarity_search_with_score_and_filter(
                    query_embedding, k=k, metadata_filter=shared_filter
                )
                
                # Combine and sort by score
                all_results = tenant_results + shared_results
                all_results.sort(key=lambda x: x[1], reverse=True)
                results = all_results[:k]
            else:
                # Only tenant-specific
                metadata_filter["tenant_id"] = tenant_id
                results = self.vector_store.similarity_search_with_score_and_filter(
                    query_embedding, k=k, metadata_filter=metadata_filter
                )
        else:
            # No tenant filtering
            results = self.vector_store.similarity_search_with_score_and_filter(
                query_embedding, k=k, metadata_filter=metadata_filter
            )
        
        # Extract SQL from results
        sql_results = []
        for doc, score in results:
            metadata = doc.get("metadata", {})
            if "sql" in metadata:
                sql_results.append(metadata["sql"])
                logger.debug(f"Found similar SQL (score={score:.3f}): {metadata.get('question', 'N/A')}")
        
        return sql_results
    
    def get_related_ddl(self, question: str, **kwargs) -> List[str]:
        """Get related DDL with metadata filtering."""
        # Get filtering parameters
        database_type = kwargs.get("database_type", self.database_type)
        tenant_id = kwargs.get("tenant_id", self.tenant_id)
        include_shared = kwargs.get("include_shared", settings.ENABLE_SHARED_KNOWLEDGE)
        k = kwargs.get("k", 5)
        
        # Generate query embedding
        query_embedding = self.generate_embedding(question)
        
        # Build metadata filter
        metadata_filter = {
            "database_type": database_type,
            "content_type": "ddl"
        }
        
        # Apply tenant filtering if enabled
        if settings.ENABLE_MULTI_TENANT and tenant_id and not include_shared:
            metadata_filter["tenant_id"] = tenant_id
        
        # Search for DDL
        results = self.vector_store.similarity_search_with_score_and_filter(
            query_embedding, k=k, metadata_filter=metadata_filter
        )
        
        # Extract DDL statements
        ddl_results = []
        for doc, score in results:
            ddl_results.append(doc["document"])
            logger.debug(f"Found related DDL (score={score:.3f})")
        
        return ddl_results
    
    def get_related_documentation(self, question: str, **kwargs) -> List[str]:
        """Get related documentation with metadata filtering."""
        # Get filtering parameters
        database_type = kwargs.get("database_type", self.database_type)
        tenant_id = kwargs.get("tenant_id", self.tenant_id)
        include_shared = kwargs.get("include_shared", settings.ENABLE_SHARED_KNOWLEDGE)
        k = kwargs.get("k", 5)
        
        # Generate query embedding
        query_embedding = self.generate_embedding(question)
        
        # Build metadata filter
        metadata_filter = {
            "database_type": database_type,
            "content_type": "documentation"
        }
        
        # Apply tenant filtering if enabled
        if settings.ENABLE_MULTI_TENANT and tenant_id and not include_shared:
            metadata_filter["tenant_id"] = tenant_id
        
        # Search for documentation
        results = self.vector_store.similarity_search_with_score_and_filter(
            query_embedding, k=k, metadata_filter=metadata_filter
        )
        
        # Extract documentation
        doc_results = []
        for doc, score in results:
            doc_results.append(doc["document"])
            logger.debug(f"Found related documentation (score={score:.3f})")
        
        return doc_results
    
    def generate_sql(self, question: str, **kwargs) -> str:
        """
        Generate SQL with proper context filtering.
        
        This method now properly filters training data by database type and tenant.
        """
        # Get filtering parameters
        database_type = kwargs.get("database_type", self.database_type)
        tenant_id = kwargs.get("tenant_id", self.tenant_id)
        include_shared = kwargs.get("include_shared", settings.ENABLE_SHARED_KNOWLEDGE)
        
        # Get similar questions with filtering
        similar_sql = self.get_similar_question_sql(
            question, 
            database_type=database_type,
            tenant_id=tenant_id,
            include_shared=include_shared,
            k=3
        )
        
        # Get related DDL with filtering
        related_ddl = self.get_related_ddl(
            question,
            database_type=database_type,
            tenant_id=tenant_id,
            include_shared=include_shared,
            k=5
        )
        
        # Get related documentation with filtering
        related_docs = self.get_related_documentation(
            question,
            database_type=database_type,
            tenant_id=tenant_id,
            include_shared=include_shared,
            k=3
        )
        
        # Build context for SQL generation
        context_parts = []
        
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
                context_parts.append(sql)
        
        context = "\n".join(context_parts)
        
        # Generate SQL using LLM with context
        prompt_text = f"""Given the following context about a {database_type} database, generate SQL to answer this question:

{context}

Question: {question}

Generate only the SQL query without any explanation."""
        
        # Convert to proper message format
        messages = [
            {"role": "system", "content": "You are a SQL expert. Generate only the SQL query without any explanation."},
            {"role": "user", "content": prompt_text}
        ]
        
        sql = self.submit_prompt(messages)
        
        logger.info(f"Generated SQL for {database_type}/{tenant_id}: {sql[:100]}...")
        return sql
    
    def remove_training_data(self, id: str) -> bool:
        """Remove training data by ID."""
        try:
            count = self.vector_store.delete_documents([id])
            return count > 0
        except Exception as e:
            logger.error(f"Error removing training data: {e}")
            return False
    
    def get_training_data(self, **kwargs) -> List[Dict[str, Any]]:
        """Get training data with metadata filtering."""
        # Build metadata filter from kwargs
        metadata_filter = {}
        
        if "database_type" in kwargs:
            metadata_filter["database_type"] = kwargs["database_type"]
        elif hasattr(self, "database_type"):
            metadata_filter["database_type"] = self.database_type
        
        if "tenant_id" in kwargs:
            metadata_filter["tenant_id"] = kwargs["tenant_id"]
        elif settings.ENABLE_MULTI_TENANT and hasattr(self, "tenant_id"):
            metadata_filter["tenant_id"] = self.tenant_id
        
        if "content_type" in kwargs:
            metadata_filter["content_type"] = kwargs["content_type"]
        
        # Get documents matching filters
        documents = self.vector_store.get_documents_by_metadata(metadata_filter)
        
        # Format for return
        training_data = []
        for doc in documents:
            data = {
                "id": doc["id"],
                "content": doc["document"],
                "metadata": doc.get("metadata", {})
            }
            training_data.append(data)
        
        return training_data
    
    def _build_metadata(self, content_type: str, **kwargs) -> Dict[str, Any]:
        """Build metadata dictionary with all required fields."""
        metadata = {
            "content_type": content_type,
            "database_type": kwargs.get("database_type", self.database_type),
            "created_at": datetime.now().isoformat(),
            "created_by": kwargs.get("created_by", "system")
        }
        
        # Add tenant information if multi-tenant is enabled OR if tenant_id is explicitly provided
        if settings.ENABLE_MULTI_TENANT or kwargs.get("tenant_id"):
            if kwargs.get("is_shared", False):
                metadata["is_shared"] = "true"
                metadata["tenant_id"] = "shared"
            else:
                tenant_id = kwargs.get("tenant_id", self.tenant_id)
                if tenant_id:
                    metadata["tenant_id"] = tenant_id
        
        # Add any additional metadata from kwargs
        for key, value in kwargs.items():
            if key not in ["database_type", "tenant_id", "is_shared", "created_by"] and value is not None:
                metadata[key] = value
        
        return metadata
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the training data."""
        # Get overall stats
        stats = self.vector_store.get_statistics()
        
        # Add filtered stats for current context
        if hasattr(self, "database_type"):
            db_stats = self.vector_store.get_statistics({"database_type": self.database_type})
            stats["current_database"] = {
                "database_type": self.database_type,
                "total_documents": db_stats["total_documents"]
            }
        
        if settings.ENABLE_MULTI_TENANT and hasattr(self, "tenant_id"):
            tenant_stats = self.vector_store.get_statistics({
                "database_type": self.database_type,
                "tenant_id": self.tenant_id
            })
            stats["current_tenant"] = {
                "tenant_id": self.tenant_id,
                "total_documents": tenant_stats["total_documents"]
            }
        
        return stats