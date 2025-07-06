"""
A wrapper that intercepts Vanna operations to enforce schema usage
"""
import psycopg2
from contextlib import contextmanager
from typing import Any, Optional
import logging

logger = logging.getLogger(__name__)

class SchemaEnforcingConnection:
    """Wrapper for psycopg2 connection that enforces schema"""
    
    def __init__(self, real_conn, schema: str):
        self.real_conn = real_conn
        self.schema = schema
        self._set_search_path()
    
    def _set_search_path(self):
        """Set search path on every operation"""
        cursor = self.real_conn.cursor()
        cursor.execute(f"SET search_path TO {self.schema}, public")
        cursor.close()
    
    def cursor(self):
        """Return cursor with schema set"""
        self._set_search_path()
        return self.real_conn.cursor()
    
    def commit(self):
        return self.real_conn.commit()
    
    def rollback(self):
        return self.real_conn.rollback()
    
    def close(self):
        return self.real_conn.close()
    
    def __getattr__(self, name):
        """Proxy all other attributes to real connection"""
        return getattr(self.real_conn, name)

@contextmanager
def schema_enforcing_connect(dsn: str, schema: str):
    """Context manager that returns schema-enforcing connection"""
    real_conn = psycopg2.connect(dsn)
    wrapped_conn = SchemaEnforcingConnection(real_conn, schema)
    try:
        yield wrapped_conn
    finally:
        wrapped_conn.close()

# Monkey patch psycopg2.connect when Vanna is used
_original_connect = psycopg2.connect
_enforced_schema = None

def patched_connect(*args, **kwargs):
    """Patched connect that enforces schema"""
    conn = _original_connect(*args, **kwargs)
    
    if _enforced_schema:
        # Wrap the connection to enforce schema
        return SchemaEnforcingConnection(conn, _enforced_schema)
    
    return conn

def enable_schema_enforcement(schema: str):
    """Enable schema enforcement for all connections"""
    global _enforced_schema
    _enforced_schema = schema
    psycopg2.connect = patched_connect
    logger.info(f"Enabled schema enforcement for: {schema}")

def disable_schema_enforcement():
    """Disable schema enforcement"""
    global _enforced_schema
    _enforced_schema = None
    psycopg2.connect = _original_connect
    logger.info("Disabled schema enforcement")