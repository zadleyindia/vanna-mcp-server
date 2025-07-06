"""
Export utilities for data formatting and file generation
"""
import json
import csv
import io
import base64
from typing import List, Dict, Any, Optional
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)

# Optional dependencies
try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

def export_to_json(data: List[Dict[str, Any]], filename_prefix: str = "export") -> Dict[str, Any]:
    """
    Export data to JSON format
    
    Args:
        data: List of dictionaries containing the data
        filename_prefix: Prefix for the generated filename
    
    Returns:
        Dict containing export information
    """
    try:
        # Convert data to JSON with proper serialization
        json_data = json.dumps(data, indent=2, default=_json_serializer)
        
        filename = f"{filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        return {
            "success": True,
            "format": "json",
            "data": json_data,
            "filename": filename,
            "size_bytes": len(json_data.encode('utf-8')),
            "row_count": len(data)
        }
        
    except Exception as e:
        logger.error(f"JSON export failed: {e}")
        return {
            "success": False,
            "error": f"JSON export failed: {str(e)}"
        }

def export_to_csv(data: List[Dict[str, Any]], filename_prefix: str = "export") -> Dict[str, Any]:
    """
    Export data to CSV format
    
    Args:
        data: List of dictionaries containing the data
        filename_prefix: Prefix for the generated filename
    
    Returns:
        Dict containing export information
    """
    try:
        if not data:
            return {
                "success": True,
                "format": "csv",
                "data": "",
                "filename": f"{filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                "size_bytes": 0,
                "row_count": 0
            }
        
        if PANDAS_AVAILABLE:
            # Use pandas for better CSV handling
            df = pd.DataFrame(data)
            csv_buffer = io.StringIO()
            df.to_csv(csv_buffer, index=False)
            csv_content = csv_buffer.getvalue()
        else:
            # Manual CSV creation
            csv_buffer = io.StringIO()
            fieldnames = list(data[0].keys())
            writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
            
            writer.writeheader()
            for row in data:
                # Convert values to strings and handle None values
                clean_row = {k: _csv_serialize_value(v) for k, v in row.items()}
                writer.writerow(clean_row)
            
            csv_content = csv_buffer.getvalue()
        
        filename = f"{filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return {
            "success": True,
            "format": "csv",
            "data": csv_content,
            "filename": filename,
            "size_bytes": len(csv_content.encode('utf-8')),
            "row_count": len(data)
        }
        
    except Exception as e:
        logger.error(f"CSV export failed: {e}")
        return {
            "success": False,
            "error": f"CSV export failed: {str(e)}"
        }

def export_to_excel(data: List[Dict[str, Any]], filename_prefix: str = "export") -> Dict[str, Any]:
    """
    Export data to Excel format (requires pandas and openpyxl)
    
    Args:
        data: List of dictionaries containing the data
        filename_prefix: Prefix for the generated filename
    
    Returns:
        Dict containing export information
    """
    try:
        if not PANDAS_AVAILABLE:
            return {
                "success": False,
                "error": "Excel export requires pandas. Install with: pip install pandas openpyxl"
            }
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Create Excel file in memory
        excel_buffer = io.BytesIO()
        
        try:
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Data')
        except ImportError:
            return {
                "success": False,
                "error": "Excel export requires openpyxl. Install with: pip install openpyxl"
            }
        
        excel_content = excel_buffer.getvalue()
        
        # Encode as base64 for JSON transmission
        excel_b64 = base64.b64encode(excel_content).decode('utf-8')
        
        filename = f"{filename_prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return {
            "success": True,
            "format": "excel",
            "data": excel_b64,
            "encoding": "base64",
            "filename": filename,
            "size_bytes": len(excel_content),
            "row_count": len(data)
        }
        
    except Exception as e:
        logger.error(f"Excel export failed: {e}")
        return {
            "success": False,
            "error": f"Excel export failed: {str(e)}"
        }

def create_download_instructions(export_result: Dict[str, Any]) -> str:
    """
    Create user-friendly download instructions based on export result
    
    Args:
        export_result: Result from export function
    
    Returns:
        String with download instructions
    """
    if not export_result.get("success"):
        return f"Export failed: {export_result.get('error', 'Unknown error')}"
    
    format_type = export_result["format"]
    filename = export_result["filename"]
    size = export_result.get("size_bytes", 0)
    row_count = export_result.get("row_count", 0)
    
    # Format file size
    if size < 1024:
        size_str = f"{size} bytes"
    elif size < 1024 * 1024:
        size_str = f"{size / 1024:.1f} KB"
    else:
        size_str = f"{size / (1024 * 1024):.1f} MB"
    
    instructions = [
        f"✅ Export successful: {row_count} rows exported to {format_type.upper()} format",
        f"📄 Filename: {filename}",
        f"📊 File size: {size_str}"
    ]
    
    if format_type == "excel":
        instructions.append("💡 Excel file is base64 encoded - decode before saving")
    elif format_type == "csv":
        instructions.append("💡 CSV file ready for spreadsheet applications")
    elif format_type == "json":
        instructions.append("💡 JSON file ready for data processing")
    
    return "\n".join(instructions)

def _json_serializer(obj):
    """JSON serializer for special data types"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, bytes):
        return base64.b64encode(obj).decode('utf-8')
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

def _csv_serialize_value(value) -> str:
    """Serialize value for CSV output"""
    if value is None:
        return ""
    elif isinstance(value, (datetime, date)):
        return value.isoformat()
    elif isinstance(value, bool):
        return "true" if value else "false"
    elif isinstance(value, (list, dict)):
        return json.dumps(value)
    else:
        return str(value)

def get_export_capabilities() -> Dict[str, bool]:
    """
    Check which export formats are available based on installed dependencies
    
    Returns:
        Dict mapping format names to availability
    """
    return {
        "json": True,  # Always available
        "csv": True,   # Always available (manual implementation)
        "excel": PANDAS_AVAILABLE  # Requires pandas + openpyxl
    }