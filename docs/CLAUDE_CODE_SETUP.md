# Claude Code CLI Setup

This guide explains how to configure the Vanna MCP Server for use with Claude Code (the CLI version).

## Configuration Locations

Claude Code looks for MCP server configurations in these locations (in order):

1. `~/.config/claude-code/settings.json` (default)
2. Path specified in `CLAUDE_CODE_SETTINGS_PATH` environment variable

## Quick Setup

### Option 1: Run the Setup Script

```bash
cd /Users/mohit/claude/vanna-mcp-server
./setup_claude_code.sh
```

### Option 2: Manual Configuration

1. Create the configuration directory:
```bash
mkdir -p ~/.config/claude-code
```

2. Create/edit `~/.config/claude-code/settings.json`:
```json
{
  "mcpServers": {
    "vanna-mcp": {
      "command": "python",
      "args": [
        "/Users/mohit/claude/vanna-mcp-server/server.py"
      ],
      "env": {
        "PYTHONPATH": "/Users/mohit/claude/vanna-mcp-server"
      },
      "config": {
        "OPENAI_API_KEY": "your-api-key",
        "SUPABASE_URL": "your-supabase-url",
        "SUPABASE_KEY": "your-supabase-anon-or-service-key",
        "SUPABASE_DB_PASSWORD": "your-database-password",
        "BIGQUERY_PROJECT": "your-project",
        "VANNA_SCHEMA": "vannabq",
        "ACCESS_CONTROL_MODE": "whitelist",
        "ACCESS_CONTROL_DATASETS": "your-datasets",
        "MANDATORY_QUERY_VALIDATION": "true",
        "MAX_QUERY_RESULTS": "10000",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

### Configuration Notes

- **SUPABASE_KEY**: Your Supabase anon or service role key (JWT token for API access)
- **SUPABASE_DB_PASSWORD**: Your PostgreSQL database password (get from Supabase Dashboard > Settings > Database)
- Both are required: the key for Supabase client operations, the password for direct database connections

## Verifying the Setup

1. Start Claude Code:
```bash
claude code
```

2. Check if the MCP server is loaded by asking:
```
What MCP tools are available?
```

3. Test the Vanna tools:
```
Use vanna_suggest_questions to see what questions I can ask
```

## Using with Virtual Environment

If you're using a Python virtual environment, you have two options:

### Option 1: Update the command path
```json
{
  "mcpServers": {
    "vanna-mcp": {
      "command": "/Users/mohit/claude/vanna-mcp-server/venv/bin/python",
      "args": [
        "/Users/mohit/claude/vanna-mcp-server/server.py"
      ]
    }
  }
}
```

### Option 2: Use a wrapper script
Create a wrapper script that activates the virtual environment:

```bash
#!/bin/bash
source /Users/mohit/claude/vanna-mcp-server/venv/bin/activate
python /Users/mohit/claude/vanna-mcp-server/server.py
```

## Troubleshooting

### MCP Server Not Loading

1. Check the settings file syntax:
```bash
cat ~/.config/claude-code/settings.json | jq .
```

2. Verify the server path exists:
```bash
ls -la /Users/mohit/claude/vanna-mcp-server/server.py
```

3. Check Python dependencies:
```bash
cd /Users/mohit/claude/vanna-mcp-server
source venv/bin/activate
python -c "import fastmcp; import vanna"
```

### Permission Errors

Make sure the server script is executable:
```bash
chmod +x /Users/mohit/claude/vanna-mcp-server/server.py
```

### Debugging

Enable debug logging by setting:
```json
"LOG_LEVEL": "DEBUG"
```

Then check the logs:
```bash
# Claude Code logs are typically in:
tail -f ~/.local/share/claude-code/logs/*.log
```

## Differences from Claude Desktop

| Feature | Claude Desktop | Claude Code |
|---------|---------------|-------------|
| Config Location | `~/Library/Application Support/Claude/claude_desktop_config.json` | `~/.config/claude-code/settings.json` |
| Config Format | Same JSON structure | Same JSON structure |
| MCP Support | Full support | Full support |
| Auto-reload | Yes (on restart) | Yes (on restart) |

## Next Steps

1. Ensure your virtual environment has all dependencies installed
2. Test the connection to BigQuery and Supabase
3. Start using natural language SQL queries:
   ```
   What are the total sales for last month?
   ```