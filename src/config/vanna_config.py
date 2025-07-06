"""
Vanna configuration for MCP server.
This is the main entry point that the server uses.
"""

# Import the production-ready implementation with all features
from .production_vanna import VannaMCP, get_vanna

__all__ = ['VannaMCP', 'get_vanna']