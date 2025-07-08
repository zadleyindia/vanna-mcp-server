# Data Catalog Integration Quick Start

## Overview

This guide helps you quickly set up and use the Data Catalog integration with Vanna MCP Server.

## Prerequisites

1. ✅ Vanna MCP Server is installed and working
2. ✅ Access to BigQuery project `bigquerylascoot` with catalog tables
3. ✅ OpenAI API key configured
4. ✅ Supabase connection working

## Step 1: Enable Catalog Integration

Add to your environment configuration (Claude Desktop config or `.env` file):

```env
# Enable catalog integration
CATALOG_ENABLED=true

# Catalog source (defaults)
CATALOG_PROJECT=bigquerylascoot
CATALOG_DATASET=metadata_data_dictionary

# Chunking settings (optional)
CATALOG_CHUNK_SIZE=20
CATALOG_MAX_TOKENS=1500
CATALOG_INCLUDE_VIEWS=true
CATALOG_INCLUDE_COLUMN_STATS=true
```

## Step 2: Initialize Catalog Tables

Run the initialization command:

```python
# In Claude Desktop or via MCP
await vanna_catalog_sync(mode="init")
```

Expected output:
```json
{
  "success": true,
  "mode": "init",
  "tables_created": {
    "catalog_datasets": true,
    "catalog_table_context": true,
    "catalog_column_chunks": true,
    "catalog_view_queries": true,
    "catalog_summary": true
  },
  "summary": "Created 5/5 tables successfully"
}
```

## Step 3: Perform Initial Sync

Sync catalog data to Vanna:

```python
# Full sync (first time)
await vanna_catalog_sync(mode="full", dry_run=true)  # Preview first

# If preview looks good, do actual sync
await vanna_catalog_sync(mode="full")
```

Expected output:
```json
{
  "success": true,
  "mode": "full",
  "source": "bigquery",
  "duration_seconds": 45.2,
  "results": {
    "datasets_processed": 8,
    "tables_synced": 298,
    "column_chunks_created": 1247,
    "view_chunks_created": 89,
    "summary_chunks_created": 8
  }
}
```

## Step 4: Test Enhanced Queries

Now Vanna will use catalog context automatically:

```python
# Before catalog: Basic SQL generation
await vanna_ask("Show me sales by product category")

# After catalog: Enhanced with business context
# - Knows product_category has specific values
# - Understands table relationships
# - Includes relevant business descriptions
```

## Step 5: Monitor Sync Status

Check catalog sync health:

```python
await vanna_catalog_sync(mode="status")
```

## Common Commands

### Full Sync (Refresh Everything)
```python
await vanna_catalog_sync(mode="full")
```

### Incremental Sync (Only Changes)
```python
await vanna_catalog_sync(mode="incremental")
```

### Sync Specific Dataset
```python
await vanna_catalog_sync(dataset_filter="SQL_ZADLEY")
```

### Preview Changes (Dry Run)
```python
await vanna_catalog_sync(mode="full", dry_run=true)
```

### Load from JSON Export
```python
await vanna_catalog_sync(
    source="json", 
    json_path="/path/to/catalog.json"
)
```

## Configuration Options

| Setting | Default | Description |
|---------|---------|-------------|
| `CATALOG_ENABLED` | `false` | Enable/disable catalog integration |
| `CATALOG_PROJECT` | `bigquerylascoot` | BigQuery project with catalog |
| `CATALOG_DATASET` | `metadata_data_dictionary` | Catalog dataset name |
| `CATALOG_CHUNK_SIZE` | `20` | Columns per chunk |
| `CATALOG_MAX_TOKENS` | `1500` | Max tokens per chunk |
| `CATALOG_INCLUDE_VIEWS` | `true` | Include view SQL patterns |
| `CATALOG_INCLUDE_COLUMN_STATS` | `true` | Include column statistics |
| `CATALOG_DATASET_FILTER` | `null` | Filter specific datasets |

## Troubleshooting

### Problem: "Catalog integration is not enabled"
**Solution**: Set `CATALOG_ENABLED=true` in your config

### Problem: "CATALOG_PROJECT is not set"
**Solution**: Add `CATALOG_PROJECT=bigquerylascoot` to config

### Problem: "Failed to create table catalog_datasets"
**Solution**: Check BigQuery permissions, ensure project access

### Problem: "BigQuery error while fetching catalog"
**Solution**: 
1. Verify catalog tables exist in `bigquerylascoot.metadata_data_dictionary`
2. Check BigQuery authentication
3. Ensure service account has read access

### Problem: Sync is slow or fails with large datasets
**Solution**:
1. Use `dataset_filter` to sync one dataset at a time
2. Try `dry_run=true` first to estimate scope
3. Check embedding generation (OpenAI API limits)

### Problem: Embeddings fail to generate
**Solution**:
1. Verify `OPENAI_API_KEY` is set and valid
2. Check OpenAI API rate limits
3. Review logs for specific embedding errors

## Expected Benefits

After successful catalog integration, you should see:

1. **Better Context**: Queries include business terminology
2. **Smarter Joins**: Understands table relationships
3. **Column Awareness**: Knows data types, cardinality, sample values
4. **Domain Knowledge**: Uses business descriptions and ownership info
5. **Query Patterns**: Learns from existing view definitions

## Next Steps

1. **Test Enhanced Queries**: Try natural language questions that use business terms
2. **Monitor Performance**: Check if SQL generation accuracy improves
3. **Regular Sync**: Set up periodic sync (daily/weekly) for fresh metadata
4. **Expand Coverage**: Consider syncing additional datasets as needed

## Support

For issues or questions:
1. Check logs: `/Users/mohit/Library/Logs/Claude/mcp-server-vanna-mcp.log`
2. Review documentation in `/docs/data-catalog/`
3. Test with simple queries first before complex ones
4. Use `dry_run=true` to preview changes before applying