# Troubleshooting Guide

> **Last Updated**: 2025-01-06

Common issues and solutions for Vanna MCP Server.

## Installation Issues

### ModuleNotFoundError: No module named 'fastmcp'
```bash
pip install fastmcp --upgrade
```

### ModuleNotFoundError: No module named 'vanna'
The project uses a forked version. Reinstall:
```bash
pip install git+https://github.com/zadleyindia/vanna.git@add-metadata-support
```

## Connection Issues

### Supabase Connection Failed

#### Error: "Tenant or user not found"
- **Cause**: Wrong region or credentials
- **Solution**: 
  - Verify region is `ap-south-1` (Mumbai)
  - Use service role key, not anon key
  - Check database password is correct

#### Error: "Connection refused"
- **Cause**: Network or firewall issues
- **Solution**:
  - Check Supabase URL is correct
  - Verify network connectivity
  - Check if Supabase project is paused

### BigQuery Connection Failed

#### Error: "Permission denied"
- **Cause**: Service account lacks permissions
- **Solution**:
  - Grant `bigquery.dataViewer` on datasets
  - Grant `bigquery.jobUser` for queries
  - Verify service account JSON path

#### Error: "Project not found"
- **Cause**: Wrong project ID or region
- **Solution**:
  - Verify BIGQUERY_PROJECT value
  - Check service account has access to project

## Vector Store Issues

### Error: "operator does not exist: vector <=> numeric[]"
- **Status**: Known limitation, doesn't affect functionality
- **Impact**: Similarity scores are placeholders (0.5)
- **Solution**: Already handled in FilteredPGVectorStore

### Error: "column cmetadata does not exist"
- **Cause**: Using old table structure
- **Solution**: Check if you're in the correct schema (public)

## Metadata Filtering Issues

### Training Data Not Isolated
- **Cause**: Metadata not properly set
- **Solution**:
  1. Verify DATABASE_TYPE is set in config
  2. Check tenant_id if multi-tenant enabled
  3. Run test script: `python scripts/test_filtered_vector_isolation.py`

### Cross-Database Contamination
- **Cause**: Old data without metadata
- **Solution**: Run migration script
  ```bash
  python scripts/migrate_to_filtered_vector.py
  ```

## MCP Server Issues

### Server Won't Start

#### Check logs
```bash
# Check Claude Desktop logs
tail -f ~/Library/Logs/Claude/mcp*.log
```

#### Common causes:
1. Invalid JSON in claude_desktop_config.json
2. Missing required configuration
3. Python path issues

### Tools Not Appearing
- **Cause**: Server failed to initialize
- **Solution**:
  1. Restart Claude Desktop
  2. Check server logs
  3. Verify python path is correct

## Multi-Tenant Issues

### Error: "Tenant 'xyz' is not allowed"
- **Cause**: Tenant not in ALLOWED_TENANTS
- **Solution**: Add tenant to configuration or use allowed tenant

### Shared Knowledge Not Working
- **Cause**: ENABLE_SHARED_KNOWLEDGE not set
- **Solution**: Set to "true" in configuration

## Performance Issues

### Slow Query Generation
- **Cause**: Large vector store
- **Solution**:
  1. Clean old training data
  2. Optimize PostgreSQL:
     ```sql
     VACUUM ANALYZE langchain_pg_embedding;
     REINDEX TABLE langchain_pg_embedding;
     ```

### High Token Usage
- **Cause**: Too much context being retrieved
- **Solution**: Reduce n_results in configuration

## Debug Mode

Enable detailed logging:

### In .env file
```env
LOG_LEVEL=DEBUG
FASTMCP_DEBUG=true
```

### In MCP config
```json
{
  "LOG_LEVEL": "DEBUG",
  "FASTMCP_DEBUG": "true"
}
```

## Test Scripts

Run these to diagnose issues:

```bash
# Test basic connectivity
python scripts/test_supabase_connection.py

# Test vector store
python scripts/test_basic_functionality.py

# Test filtering
python scripts/test_filtered_vector_isolation.py

# Test MCP server
python scripts/test_mcp_server.py
```

## Getting Help

When reporting issues, include:
1. Error message (full traceback)
2. Configuration (without secrets)
3. Steps to reproduce
4. Output of test scripts
5. Log files (with DEBUG enabled)

## Quick Fixes

### Reset Everything
```bash
# Backup first!
pg_dump ... > backup.sql

# Clear all data
python scripts/clear_all_training_data.py

# Reinitialize
python scripts/setup_database.py
```

### Force Metadata Update
```bash
# Add metadata to all existing data
python scripts/force_metadata_update.py \
  --database-type bigquery \
  --tenant-id default
```

### Validate Configuration
```bash
# Check if configuration is valid
python scripts/validate_config.py
```