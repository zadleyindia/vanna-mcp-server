"""
Catalog Integration Module for Vanna MCP Server

This module provides integration with the BigQuery Data Catalog system,
allowing Vanna to leverage rich metadata for improved SQL generation.

Components:
- CatalogQuerier: Fetches data from catalog tables
- CatalogChunker: Breaks down catalog data into manageable chunks
- CatalogStorage: Stores chunked data with embeddings
- vanna_catalog_sync: MCP tool for synchronization

Usage:
1. Enable catalog integration in config: CATALOG_ENABLED=true
2. Initialize tables: vanna_catalog_sync(mode="init")
3. Sync data: vanna_catalog_sync(mode="full")
4. Use enhanced context in vanna_ask
"""

from .querier import CatalogQuerier
from .chunker import CatalogChunker
from .storage import CatalogStorage
from .schema import CATALOG_SCHEMAS

__all__ = [
    'CatalogQuerier',
    'CatalogChunker', 
    'CatalogStorage',
    'CATALOG_SCHEMAS'
]