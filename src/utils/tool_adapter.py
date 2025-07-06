"""
Adapter to convert MCP tool definitions to FastMCP format
"""

def convert_mcp_to_fastmcp_tool(mcp_tool_def):
    """
    Convert MCP tool definition format to FastMCP format
    
    MCP uses: input_schema
    FastMCP uses: different parameter structure
    """
    # FastMCP tool decorator doesn't accept these parameters directly
    # Instead, it infers them from the function signature and docstring
    # We'll return just the metadata that FastMCP needs
    return {
        "name": mcp_tool_def["name"],
        "description": mcp_tool_def["description"]
    }