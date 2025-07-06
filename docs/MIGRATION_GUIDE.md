# Migration Guide

> **Last Updated**: 2025-01-06  
> **Target Version**: 2.0 with Filtered Vector Store

This guide helps you migrate existing Vanna MCP Server installations to the latest version with filtered vector store and forked Vanna support.

## Overview of Changes

### Major Updates in v2.0
1. **Filtered Vector Store**: Custom implementation for proper metadata filtering
2. **Forked Vanna**: Native metadata support in train() method
3. **Multi-Database Support**: True isolation between database types
4. **Multi-Tenant Isolation**: Proper filtering at query time
5. **Improved Configuration**: Better structure and validation

## Migration Scenarios

### Scenario 1: From Basic Vanna Installation (v1.x)

If you're using the original implementation without metadata filtering:

#### Step 1: Backup Existing Data
```bash
# Backup your vector store
pg_dump -h your-supabase-host -U postgres -d postgres \
  -t langchain_pg_embedding -t langchain_pg_collection \
  > vanna_backup_v1_$(date +%Y%m%d).sql
```

#### Step 2: Update Dependencies
```bash
# Activate your virtual environment
source venv/bin/activate

# Update requirements (includes forked Vanna)
pip install -r requirements.txt --upgrade
```

#### Step 3: Run Migration Script
```bash
python scripts/migrate_to_filtered_vector.py
```

This script will:
- Add metadata to existing embeddings
- Set default database_type and tenant_id
- Update table structure if needed

#### Step 4: Update Configuration

Add new configuration parameters:

```json
{
  "DATABASE_TYPE": "bigquery",  // Required
  "ENABLE_MULTI_TENANT": "false",  // Set to true if needed
  "TENANT_ID": "default"  // If multi-tenant enabled
}
```

### Scenario 2: From Multi-Schema Setup

If you were using multiple schemas (vannabq, vannapg, etc.):

#### Step 1: Consolidate to Public Schema
```bash
# This was already done if you followed previous instructions
python scripts/consolidate_to_public_schema.py
```

#### Step 2: Update Training Data
The migration script will tag existing data with appropriate metadata:
```bash
python scripts/migrate_to_filtered_vector.py --tag-by-schema
```

#### Step 3: Remove Old Configuration
Remove schema-related configuration:
```diff
- "VANNA_SCHEMA": "vannabq"  # No longer used
+ "DATABASE_TYPE": "bigquery"  # Use this instead
```

### Scenario 3: From Development to Production

#### Step 1: Export Development Data
```bash
# Export training data with metadata
python scripts/export_training_data.py \
  --output training_export_$(date +%Y%m%d).json
```

#### Step 2: Set Up Production Environment
Follow the [PRODUCTION_DEPLOYMENT.md](../PRODUCTION_DEPLOYMENT.md) guide.

#### Step 3: Import Training Data
```bash
# In production environment
python scripts/import_training_data.py \
  --input training_export_20250106.json \
  --database-type bigquery \
  --tenant-id production
```

## Configuration Changes

### Deprecated Parameters
These parameters are no longer used:
- `VANNA_SCHEMA` - Everything is now in public schema
- `SCHEMA_PREFIX` - Use DATABASE_TYPE instead

### New Required Parameters
- `DATABASE_TYPE` - Specify your database type (bigquery, postgres, mssql)

### New Optional Parameters
- `ENABLE_MULTI_TENANT` - Enable tenant isolation
- `TENANT_ID` - Default tenant ID
- `ALLOWED_TENANTS` - Comma-separated list of allowed tenants
- `ENABLE_SHARED_KNOWLEDGE` - Allow shared training data

## Code Changes

### If You Have Custom Code

#### Update Imports
```python
# Old
from src.config.multi_database_vanna import MultiDatabaseVanna

# New
from src.config.vanna_config import VannaMCP
```

#### Update Training Calls
```python
# Old
vn.train(
    question="Show users",
    sql="SELECT * FROM users"
)

# New - metadata is now supported
vn.train(
    question="Show users",
    sql="SELECT * FROM users",
    metadata={
        "database_type": "bigquery",
        "tenant_id": "acme_corp"
    }
)
```

#### Update Tool Calls
The MCP tools now support additional parameters:
- `tenant_id` - Override default tenant
- `is_shared` - Mark as shared knowledge

## Testing After Migration

### 1. Verify Installation
```bash
python scripts/test_basic_functionality.py
```

### 2. Test Metadata Filtering
```bash
python scripts/test_filtered_vector_isolation.py
```

### 3. Test Multi-Tenant (if enabled)
```bash
python scripts/test_multi_tenant_enabled.py
```

### 4. Verify in Claude Desktop
```
Ask: "List available tenants"
Ask: "What tables are available?"
```

## Rollback Plan

If you need to rollback:

### 1. Restore Database Backup
```bash
psql -h your-supabase-host -U postgres -d postgres \
  < vanna_backup_v1_20250106.sql
```

### 2. Revert Code
```bash
git checkout v1.0  # Or your previous version tag
```

### 3. Reinstall Old Dependencies
```bash
pip install -r requirements.old.txt
```

## Common Issues During Migration

### Issue 1: Import Errors
**Error**: `ModuleNotFoundError: No module named 'filtered_pgvector'`

**Solution**: Ensure you've installed the updated requirements:
```bash
pip install -r requirements.txt --upgrade
```

### Issue 2: Metadata Missing
**Error**: `KeyError: 'database_type'`

**Solution**: Run the migration script to add metadata:
```bash
python scripts/migrate_to_filtered_vector.py
```

### Issue 3: Vector Type Casting
**Error**: `operator does not exist: vector <=> numeric[]`

**Solution**: This is expected and handled by the filtered vector store. It doesn't affect functionality.

### Issue 4: Permission Denied
**Error**: `permission denied for schema vannabq`

**Solution**: The old schemas have been dropped. Ensure all operations use public schema.

## Performance Considerations

### After Migration
1. **Reindex**: The filtered vector store may benefit from reindexing:
   ```sql
   REINDEX TABLE langchain_pg_embedding;
   ```

2. **Vacuum**: Clean up after migration:
   ```sql
   VACUUM ANALYZE langchain_pg_embedding;
   ```

3. **Monitor**: Watch query performance for the first few days

## Next Steps

After successful migration:

1. **Update Documentation**: Document your specific configuration
2. **Train Team**: Ensure everyone knows about new features
3. **Monitor Usage**: Track tenant usage and query patterns
4. **Plan Training**: Retrain any incorrect data with proper metadata

## Support

If you encounter issues:

1. Check the [troubleshooting guide](troubleshooting.md)
2. Review logs with DEBUG enabled
3. Test with the provided test scripts
4. Create an issue with:
   - Error messages
   - Configuration (without secrets)
   - Migration steps attempted

## Conclusion

The migration to v2.0 provides significant improvements:
- Proper metadata filtering
- True multi-database support
- Tenant isolation
- Better maintainability

While the migration requires some effort, the benefits of proper data isolation and the cleaner architecture make it worthwhile.