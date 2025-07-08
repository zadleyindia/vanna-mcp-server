"""
SQL Dialect Translation Utilities
Handles conversion between BigQuery and MS SQL syntax
"""
import re
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class SQLDialectTranslator:
    """Translate SQL between BigQuery and MS SQL dialects"""
    
    @staticmethod
    def translate(sql: str, from_dialect: str, to_dialect: str) -> str:
        """
        Translate SQL from one dialect to another
        
        Args:
            sql: SQL query string
            from_dialect: Source dialect ('bigquery' or 'mssql')
            to_dialect: Target dialect ('bigquery' or 'mssql')
            
        Returns:
            Translated SQL query
        """
        if from_dialect == to_dialect:
            return sql
            
        if from_dialect == "bigquery" and to_dialect == "mssql":
            return SQLDialectTranslator.bigquery_to_mssql(sql)
        elif from_dialect == "mssql" and to_dialect == "bigquery":
            return SQLDialectTranslator.mssql_to_bigquery(sql)
        else:
            logger.warning(f"Unknown dialect translation: {from_dialect} -> {to_dialect}")
            return sql
    
    @staticmethod
    def bigquery_to_mssql(sql: str) -> str:
        """Convert BigQuery SQL to MS SQL syntax"""
        # Save original case for non-SQL parts
        sql_translated = sql
        
        # 1. Replace backticks with square brackets
        sql_translated = re.sub(r'`([^`]+)`', r'[\1]', sql_translated)
        
        # 2. Replace LIMIT with TOP
        # Handle LIMIT at the end
        limit_match = re.search(r'\s+LIMIT\s+(\d+)\s*$', sql_translated, re.IGNORECASE)
        if limit_match:
            limit_value = limit_match.group(1)
            sql_translated = sql_translated[:limit_match.start()]
            # Insert TOP after SELECT
            sql_translated = re.sub(
                r'(SELECT)(\s+)', 
                f'SELECT TOP {limit_value} ', 
                sql_translated, 
                count=1, 
                flags=re.IGNORECASE
            )
        
        # 3. Replace DATE functions
        # DATE_SUB -> DATEADD
        sql_translated = re.sub(
            r'DATE_SUB\s*\(\s*CURRENT_DATE\s*\(\s*\)\s*,\s*INTERVAL\s+(\d+)\s+(\w+)\s*\)',
            lambda m: f"DATEADD({m.group(2).lower()}, -{m.group(1)}, GETDATE())",
            sql_translated,
            flags=re.IGNORECASE
        )
        
        # CURRENT_DATE() -> CAST(GETDATE() AS DATE)
        sql_translated = re.sub(
            r'CURRENT_DATE\s*\(\s*\)',
            'CAST(GETDATE() AS DATE)',
            sql_translated,
            flags=re.IGNORECASE
        )
        
        # 4. Replace data types
        type_mappings = {
            r'\bSTRING\b': 'VARCHAR(MAX)',
            r'\bINT64\b': 'BIGINT',
            r'\bFLOAT64\b': 'FLOAT',
            r'\bBOOL\b': 'BIT',
            r'\bDATETIME\b': 'DATETIME2',
            r'\bTIMESTAMP\b': 'DATETIME2',
            r'\bNUMERIC\b': 'DECIMAL(38,9)'
        }
        
        for bq_type, mssql_type in type_mappings.items():
            sql_translated = re.sub(bq_type, mssql_type, sql_translated, flags=re.IGNORECASE)
        
        # 5. Replace ARRAY operations with STRING_AGG
        # ARRAY_AGG(column) -> STRING_AGG(column, ',')
        sql_translated = re.sub(
            r'ARRAY_AGG\s*\(\s*([^)]+)\s*\)',
            r"STRING_AGG(\1, ',')",
            sql_translated,
            flags=re.IGNORECASE
        )
        
        # 6. Replace EXTRACT functions
        # EXTRACT(YEAR FROM date_column) -> YEAR(date_column)
        sql_translated = re.sub(
            r'EXTRACT\s*\(\s*(\w+)\s+FROM\s+([^)]+)\s*\)',
            lambda m: f"{m.group(1).upper()}({m.group(2)})",
            sql_translated,
            flags=re.IGNORECASE
        )
        
        # 7. Handle SAFE_ functions (remove SAFE_ prefix)
        sql_translated = re.sub(
            r'\bSAFE_(\w+)',
            r'\1',
            sql_translated,
            flags=re.IGNORECASE
        )
        
        return sql_translated
    
    @staticmethod
    def mssql_to_bigquery(sql: str) -> str:
        """Convert MS SQL to BigQuery syntax"""
        sql_translated = sql
        
        # 1. Replace square brackets with backticks
        sql_translated = re.sub(r'\[([^\]]+)\]', r'`\1`', sql_translated)
        
        # 2. Replace TOP with LIMIT
        top_match = re.search(r'SELECT\s+TOP\s+(\d+)\s+', sql_translated, re.IGNORECASE)
        if top_match:
            top_value = top_match.group(1)
            sql_translated = re.sub(
                r'SELECT\s+TOP\s+\d+\s+',
                'SELECT ',
                sql_translated,
                count=1,
                flags=re.IGNORECASE
            )
            # Add LIMIT at the end
            sql_translated = sql_translated.rstrip(';') + f' LIMIT {top_value}'
        
        # 3. Replace date functions
        # DATEADD -> DATE_SUB/DATE_ADD
        sql_translated = re.sub(
            r'DATEADD\s*\(\s*(\w+)\s*,\s*(-?\d+)\s*,\s*GETDATE\s*\(\s*\)\s*\)',
            lambda m: f"DATE_{'SUB' if m.group(2).startswith('-') else 'ADD'}(CURRENT_DATE(), INTERVAL {abs(int(m.group(2)))} {m.group(1).upper()})",
            sql_translated,
            flags=re.IGNORECASE
        )
        
        # GETDATE() -> CURRENT_TIMESTAMP()
        sql_translated = re.sub(
            r'GETDATE\s*\(\s*\)',
            'CURRENT_TIMESTAMP()',
            sql_translated,
            flags=re.IGNORECASE
        )
        
        # 4. Replace data types
        type_mappings = {
            r'\bVARCHAR\s*\(\s*MAX\s*\)': 'STRING',
            r'\bVARCHAR\s*\(\s*\d+\s*\)': 'STRING',
            r'\bNVARCHAR\s*\(\s*MAX\s*\)': 'STRING',
            r'\bNVARCHAR\s*\(\s*\d+\s*\)': 'STRING',
            r'\bBIGINT\b': 'INT64',
            r'\bINT\b': 'INT64',
            r'\bFLOAT\b': 'FLOAT64',
            r'\bBIT\b': 'BOOL',
            r'\bDATETIME2?\b': 'DATETIME',
            r'\bDECIMAL\s*\(\s*\d+\s*,\s*\d+\s*\)': 'NUMERIC'
        }
        
        for mssql_type, bq_type in type_mappings.items():
            sql_translated = re.sub(mssql_type, bq_type, sql_translated, flags=re.IGNORECASE)
        
        # 5. Replace STRING_AGG with ARRAY_AGG
        sql_translated = re.sub(
            r'STRING_AGG\s*\(\s*([^,]+)\s*,\s*[^)]+\s*\)',
            r'ARRAY_AGG(\1)',
            sql_translated,
            flags=re.IGNORECASE
        )
        
        # 6. Replace date part functions
        # YEAR(column) -> EXTRACT(YEAR FROM column)
        for date_part in ['YEAR', 'MONTH', 'DAY', 'HOUR', 'MINUTE', 'SECOND']:
            sql_translated = re.sub(
                f'{date_part}\\s*\\(\\s*([^)]+)\\s*\\)',
                f'EXTRACT({date_part} FROM \\1)',
                sql_translated,
                flags=re.IGNORECASE
            )
        
        return sql_translated
    
    @staticmethod
    def get_dialect_info(dialect: str) -> Dict[str, Any]:
        """Get information about SQL dialect specifics"""
        if dialect == "bigquery":
            return {
                "identifier_quote": "`",
                "limit_syntax": "LIMIT",
                "date_function": "CURRENT_DATE()",
                "string_type": "STRING",
                "array_support": True,
                "safe_functions": True
            }
        elif dialect == "mssql":
            return {
                "identifier_quote": "[]",
                "limit_syntax": "TOP",
                "date_function": "GETDATE()",
                "string_type": "VARCHAR",
                "array_support": False,
                "safe_functions": False
            }
        else:
            return {}