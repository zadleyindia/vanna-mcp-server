"""
MCP Configuration Adapter
Supports both .env files (development) and MCP configuration (production)
"""
import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class MCPConfigAdapter:
    """Adapter to handle configuration from both .env and MCP sources"""
    
    _mcp_config: Optional[Dict[str, Any]] = None
    _initialized: bool = False
    
    @classmethod
    def initialize_from_mcp(cls, config: Dict[str, Any]) -> None:
        """
        Initialize configuration from MCP server config
        Called by MCP init handler in production
        """
        logger.info("Initializing configuration from MCP")
        cls._mcp_config = config
        cls._initialized = True
        
        # Set environment variables from MCP config
        # This allows the rest of the code to work unchanged
        for key, value in config.items():
            if key.upper() == key:  # Only uppercase keys (convention for env vars)
                os.environ[key] = str(value)
                logger.debug(f"Set {key} from MCP config")
    
    @classmethod
    def get(cls, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get configuration value with fallback order:
        1. MCP configuration (if initialized)
        2. Environment variable
        3. Default value
        """
        # First try MCP config
        if cls._mcp_config and key in cls._mcp_config:
            return cls._mcp_config[key]
        
        # Fall back to environment
        return os.getenv(key, default)
    
    @classmethod
    def is_mcp_initialized(cls) -> bool:
        """Check if running with MCP configuration"""
        return cls._initialized
    
    @classmethod
    def get_config_source(cls) -> str:
        """Get the current configuration source"""
        if cls._initialized:
            return "MCP Configuration"
        elif os.path.exists('.env'):
            return ".env file"
        else:
            return "Environment variables"

# Convenience function
def get_config(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get configuration value from MCP or environment"""
    value = MCPConfigAdapter.get(key, default)
    # Log tenant_id specifically to debug
    if key == "TENANT_ID":
        logger.info(f"get_config({key}) = '{value}' (source: {MCPConfigAdapter.get_config_source()})")
    return value