"""
Configuration settings for Vanna MCP Server
"""
import os
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from .mcp_config import get_config, MCPConfigAdapter

# Load environment variables (for development)
load_dotenv()

# Log available environment variables for debugging
import logging
logger = logging.getLogger(__name__)

class Settings:
    """Application settings from environment variables"""
    
    # Supabase Configuration
    SUPABASE_URL: str = get_config("SUPABASE_URL", "")
    SUPABASE_KEY: str = get_config("SUPABASE_KEY", "")  # Anon key for Supabase client
    SUPABASE_DB_PASSWORD: str = get_config("SUPABASE_DB_PASSWORD", "")  # Postgres password for direct connection
    
    # Multi-Database/Multi-Tenant Configuration
    DATABASE_TYPE: str = get_config("DATABASE_TYPE", "bigquery")  # bigquery, mssql, postgres, mysql
    ENABLE_MULTI_TENANT: bool = get_config("ENABLE_MULTI_TENANT", "false").lower() == "true"
    # IMPORTANT: tenant_id is mandatory when multi-tenant is enabled
    TENANT_ID: str = get_config("TENANT_ID", "")  # Tenant identifier - mandatory when multi-tenant enabled
    ENABLE_SHARED_KNOWLEDGE: bool = get_config("ENABLE_SHARED_KNOWLEDGE", "true").lower() == "true"
    ALLOWED_TENANTS: str = get_config("ALLOWED_TENANTS", "")  # Comma-separated list of allowed tenants
    
    # Legacy Data Handling
    INCLUDE_LEGACY_DATA: bool = get_config("INCLUDE_LEGACY_DATA", "false").lower() == "true"  # Include records without tenant_id
    
    # Security Settings
    STRICT_TENANT_ISOLATION: bool = get_config("STRICT_TENANT_ISOLATION", "false").lower() == "true"  # Block cross-tenant queries entirely
    
    # Legacy - keeping for backward compatibility but not used with public schema
    VANNA_SCHEMA: str = get_config("VANNA_SCHEMA", "public")
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = get_config("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = get_config("OPENAI_MODEL", "gpt-4")
    OPENAI_EMBEDDING_MODEL: str = get_config("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    
    # BigQuery Configuration
    BIGQUERY_PROJECT: str = get_config("BIGQUERY_PROJECT", "")
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = get_config("GOOGLE_APPLICATION_CREDENTIALS")
    
    # MS SQL Server Configuration
    MSSQL_SERVER: Optional[str] = get_config("MSSQL_SERVER")
    MSSQL_DATABASE: Optional[str] = get_config("MSSQL_DATABASE")
    MSSQL_USERNAME: Optional[str] = get_config("MSSQL_USERNAME")
    MSSQL_PASSWORD: Optional[str] = get_config("MSSQL_PASSWORD")
    MSSQL_DRIVER: str = get_config("MSSQL_DRIVER", "ODBC Driver 17 for SQL Server")
    MSSQL_ENCRYPT: bool = get_config("MSSQL_ENCRYPT", "true").lower() == "true"
    MSSQL_TRUST_SERVER_CERTIFICATE: bool = get_config("MSSQL_TRUST_SERVER_CERTIFICATE", "false").lower() == "true"
    
    # PostgreSQL Configuration (for additional databases)
    POSTGRES_CONNECTION_STRING: Optional[str] = get_config("POSTGRES_CONNECTION_STRING")
    POSTGRES_DATABASE: Optional[str] = get_config("POSTGRES_DATABASE")
    
    # Vanna Configuration
    VANNA_MODEL_NAME: str = get_config("VANNA_MODEL_NAME", "bigquery-assistant")
    
    # Access Control
    ACCESS_CONTROL_MODE: str = get_config("ACCESS_CONTROL_MODE", "whitelist")  # whitelist or blacklist
    ACCESS_CONTROL_DATASETS: str = get_config("ACCESS_CONTROL_DATASETS", "")  # comma-separated list
    
    # Query Validation
    MANDATORY_QUERY_VALIDATION: bool = get_config("MANDATORY_QUERY_VALIDATION", "true").lower() == "true"
    MAX_QUERY_RESULTS: int = int(get_config("MAX_QUERY_RESULTS", "10000"))
    
    # Logging
    LOG_LEVEL: str = get_config("LOG_LEVEL", "INFO")
    LOG_FILE: Optional[str] = get_config("LOG_FILE")
    
    # Development
    DEBUG: bool = get_config("DEBUG", "false").lower() == "true"
    
    @classmethod
    def get_supabase_connection_string(cls) -> str:
        """Build PostgreSQL connection string for Supabase"""
        if not cls.SUPABASE_URL:
            raise ValueError("SUPABASE_URL must be set")
        
        # Must use database password, NOT the anon key
        db_password = cls.SUPABASE_DB_PASSWORD
        if not db_password:
            raise ValueError("SUPABASE_DB_PASSWORD must be set (not the anon key!)")
        
        # Extract host from Supabase URL
        # Format: https://xxxxx.supabase.co -> xxxxx
        import re
        match = re.search(r'https://([^.]+)\.supabase\.co', cls.SUPABASE_URL)
        if not match:
            raise ValueError("Invalid SUPABASE_URL format")
        
        project_ref = match.group(1)
        
        # URL-encode the password to handle special characters
        from urllib.parse import quote_plus
        encoded_password = quote_plus(db_password)
        
        # Supabase PostgreSQL connection format
        # Using transaction pooler for better connection management
        # Note: For pooler, use 'postgres' as username, not 'postgres.project_ref'
        return f"postgresql://postgres:{encoded_password}@aws-0-ap-south-1.pooler.supabase.com:6543/postgres"
    
    @classmethod
    def get_access_control_list(cls) -> list[str]:
        """Parse access control dataset list"""
        if not cls.ACCESS_CONTROL_DATASETS:
            return []
        return [ds.strip() for ds in cls.ACCESS_CONTROL_DATASETS.split(",")]
    
    @classmethod
    def get_allowed_tenants(cls) -> list[str]:
        """Parse allowed tenants list"""
        if not cls.ALLOWED_TENANTS:
            return []  # Empty list means all tenants are allowed
        return [t.strip() for t in cls.ALLOWED_TENANTS.split(",") if t.strip()]
    
    @classmethod
    def is_tenant_allowed(cls, tenant_id: str) -> bool:
        """Check if a tenant ID is allowed"""
        if not cls.ENABLE_MULTI_TENANT:
            return True  # No restrictions in single-tenant mode
        
        # Special case for shared knowledge
        if tenant_id == "shared":
            return cls.ENABLE_SHARED_KNOWLEDGE
        
        allowed_tenants = cls.get_allowed_tenants()
        if not allowed_tenants:
            return True  # No restrictions if list is empty
        
        return tenant_id in allowed_tenants
    
    @classmethod
    def get_mssql_connection_string(cls) -> Optional[str]:
        """Build MS SQL Server connection string"""
        if not all([cls.MSSQL_SERVER, cls.MSSQL_DATABASE, cls.MSSQL_USERNAME, cls.MSSQL_PASSWORD]):
            return None
        
        # Build pyodbc connection string
        conn_parts = [
            f"DRIVER={{{cls.MSSQL_DRIVER}}}",
            f"SERVER={cls.MSSQL_SERVER}",
            f"DATABASE={cls.MSSQL_DATABASE}",
            f"UID={cls.MSSQL_USERNAME}",
            f"PWD={cls.MSSQL_PASSWORD}"
        ]
        
        if cls.MSSQL_ENCRYPT:
            conn_parts.append("Encrypt=yes")
        
        if cls.MSSQL_TRUST_SERVER_CERTIFICATE:
            conn_parts.append("TrustServerCertificate=yes")
        
        return ";".join(conn_parts)
    
    @classmethod
    def validate_config(cls) -> Dict[str, Any]:
        """Validate required configuration and return status"""
        errors = []
        warnings = []
        
        # Common required configurations
        if not cls.SUPABASE_URL:
            errors.append("SUPABASE_URL is not set")
        if not cls.SUPABASE_KEY:
            errors.append("SUPABASE_KEY is not set")
        if not cls.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY is not set")
        
        # Database-specific validation
        if cls.DATABASE_TYPE == "bigquery":
            if not cls.BIGQUERY_PROJECT:
                errors.append("BIGQUERY_PROJECT is not set for BigQuery database type")
            if not cls.GOOGLE_APPLICATION_CREDENTIALS:
                warnings.append("GOOGLE_APPLICATION_CREDENTIALS not set - using default credentials")
        
        elif cls.DATABASE_TYPE == "mssql":
            if not all([cls.MSSQL_SERVER, cls.MSSQL_DATABASE, cls.MSSQL_USERNAME, cls.MSSQL_PASSWORD]):
                errors.append("MS SQL Server configuration incomplete (need SERVER, DATABASE, USERNAME, PASSWORD)")
        
        elif cls.DATABASE_TYPE == "postgres":
            if not cls.POSTGRES_CONNECTION_STRING:
                errors.append("POSTGRES_CONNECTION_STRING is not set for PostgreSQL database type")
        
        else:
            errors.append(f"Unknown DATABASE_TYPE: {cls.DATABASE_TYPE}")
        
        # Multi-tenant validation
        if cls.ENABLE_MULTI_TENANT:
            if not cls.TENANT_ID:
                errors.append("TENANT_ID is mandatory when ENABLE_MULTI_TENANT is true")
            
            # Check if default tenant is in allowed list
            allowed_tenants = cls.get_allowed_tenants()
            if cls.TENANT_ID and allowed_tenants and cls.TENANT_ID not in allowed_tenants:
                errors.append(f"TENANT_ID '{cls.TENANT_ID}' is not in ALLOWED_TENANTS list")
            
            if allowed_tenants:
                logger.info(f"Allowed tenants: {', '.join(allowed_tenants)}")
            
            # Legacy data handling
            if cls.INCLUDE_LEGACY_DATA:
                warnings.append("Legacy data (records without tenant_id) will be included in results")
            else:
                logger.info("Strict tenant isolation - only records with matching tenant_id will be returned")
        
        if cls.DEBUG:
            warnings.append("DEBUG mode is enabled")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "config": {
                "database_type": cls.DATABASE_TYPE,
                "tenant_id": cls.TENANT_ID if cls.ENABLE_MULTI_TENANT else None,
                "multi_tenant": cls.ENABLE_MULTI_TENANT,
                "shared_knowledge": cls.ENABLE_SHARED_KNOWLEDGE,
                "access_control_mode": cls.ACCESS_CONTROL_MODE,
                "debug": cls.DEBUG,
                "config_source": MCPConfigAdapter.get_config_source()
            }
        }

# Create singleton instance
settings = Settings()

# Log configuration at startup
logger.info(f"Settings initialized - Multi-tenant: {settings.ENABLE_MULTI_TENANT}, Tenant ID: '{settings.TENANT_ID}'")