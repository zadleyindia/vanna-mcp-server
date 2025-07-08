# Catalog Data Tracking Strategy for Vanna

## Problem Statement

When training Vanna with data from the Data Catalog, we need to:
1. Identify which training data came from the catalog vs manual training
2. Track catalog version/timestamp for each piece of training data
3. Efficiently update when catalog changes
4. Handle deletions when tables/columns are removed from catalog
5. Avoid duplicates and conflicts

## Solution: Metadata Tagging System

### 1. Enhanced Training Data Schema

We'll extend Vanna's training data storage to include source metadata:

```sql
-- Add columns to Vanna's training tables
ALTER TABLE vannabq.ddl_training ADD COLUMNS (
    source_type STRING,           -- 'catalog', 'manual', 'api'
    source_id STRING,             -- catalog table FQDN or unique identifier
    source_version TIMESTAMP,     -- when this data was extracted from catalog
    catalog_hash STRING,          -- hash of the catalog data for change detection
    sync_status STRING,           -- 'current', 'outdated', 'deleted'
    last_sync_attempt TIMESTAMP,  -- last time we tried to sync
    metadata JSON                 -- additional tracking info
);

ALTER TABLE vannabq.documentation_training ADD COLUMNS (
    source_type STRING,
    source_id STRING,
    source_version TIMESTAMP,
    catalog_hash STRING,
    sync_status STRING,
    last_sync_attempt TIMESTAMP,
    metadata JSON
);

ALTER TABLE vannabq.sql_training ADD COLUMNS (
    source_type STRING,
    source_id STRING,           -- view name or hevo model id
    source_version TIMESTAMP,
    catalog_hash STRING,
    sync_status STRING,
    last_sync_attempt TIMESTAMP,
    metadata JSON
);
```

### 2. Catalog Source Identification

```python
class CatalogTrainingTracker:
    """Track and manage catalog-sourced training data"""
    
    def generate_training_metadata(self, catalog_item):
        """Generate metadata for catalog-sourced training"""
        return {
            'source_type': 'catalog',
            'source_id': catalog_item.get('table_fqdn'),
            'source_version': catalog_item.get('last_updated_ts'),
            'catalog_hash': self._compute_hash(catalog_item),
            'sync_status': 'current',
            'last_sync_attempt': datetime.now(),
            'metadata': {
                'catalog_version': catalog_item.get('catalog_export_version'),
                'business_domain': catalog_item.get('business_domain'),
                'object_type': catalog_item.get('object_type'),
                'extraction_query': self._get_extraction_query()
            }
        }
    
    def _compute_hash(self, catalog_item):
        """Compute hash of relevant catalog fields"""
        # Hash only fields that affect training
        relevant_fields = {
            'table_structure': catalog_item.get('columns'),
            'description': catalog_item.get('grain_description'),
            'business_domain': catalog_item.get('business_domain'),
            'owner': catalog_item.get('owner_email'),
            'row_count': catalog_item.get('row_count'),
            'column_stats': catalog_item.get('column_statistics')
        }
        return hashlib.sha256(
            json.dumps(relevant_fields, sort_keys=True).encode()
        ).hexdigest()
```

### 3. Training with Source Tracking

```python
async def train_from_catalog_with_tracking():
    """Enhanced training that tracks catalog source"""
    
    # Step 1: Get current catalog data
    catalog_data = await fetch_catalog_data()
    
    # Step 2: Get existing training data from catalog
    existing_training = await get_catalog_training_records()
    
    # Step 3: Process each catalog item
    for item in catalog_data:
        metadata = CatalogTrainingTracker().generate_training_metadata(item)
        
        # Check if we already have training for this item
        existing = existing_training.get(item['table_fqdn'])
        
        if existing:
            # Compare hashes to detect changes
            if existing['catalog_hash'] != metadata['catalog_hash']:
                await update_training_data(item, metadata)
            else:
                # No changes, just update sync timestamp
                await update_sync_timestamp(item['table_fqdn'])
        else:
            # New item, create training data
            await create_training_data(item, metadata)
    
    # Step 4: Handle deletions
    catalog_ids = {item['table_fqdn'] for item in catalog_data}
    for existing_id in existing_training.keys():
        if existing_id not in catalog_ids:
            await mark_as_deleted(existing_id)
```

### 4. Change Detection and Sync Strategy

```python
class CatalogSyncManager:
    """Manage synchronization between catalog and Vanna training"""
    
    async def detect_changes(self):
        """Detect what needs to be synced"""
        changes = {
            'new': [],
            'modified': [],
            'deleted': [],
            'unchanged': []
        }
        
        # Query for comparison
        query = """
        WITH catalog_current AS (
            SELECT 
                table_fqdn,
                MD5(CONCAT(
                    IFNULL(grain_description, ''),
                    IFNULL(business_domain, ''),
                    CAST(column_count AS STRING),
                    CAST(last_updated_ts AS STRING)
                )) as content_hash,
                last_updated_ts
            FROM `bigquerylascoot.metadata_data_dictionary.Table_Metadata`
            WHERE status = 'In Use' AND exists_flag = TRUE
        ),
        vanna_training AS (
            SELECT 
                source_id as table_fqdn,
                catalog_hash,
                source_version
            FROM `{project}.{dataset}.ddl_training`
            WHERE source_type = 'catalog'
        )
        SELECT 
            c.table_fqdn,
            c.content_hash as catalog_hash,
            v.catalog_hash as vanna_hash,
            c.last_updated_ts as catalog_version,
            v.source_version as vanna_version,
            CASE
                WHEN v.table_fqdn IS NULL THEN 'new'
                WHEN c.content_hash != v.catalog_hash THEN 'modified'
                ELSE 'unchanged'
            END as sync_status
        FROM catalog_current c
        FULL OUTER JOIN vanna_training v
            ON c.table_fqdn = v.table_fqdn
        """
        
        results = await run_query(query)
        
        for row in results:
            if row['sync_status'] == 'new':
                changes['new'].append(row['table_fqdn'])
            elif row['sync_status'] == 'modified':
                changes['modified'].append(row['table_fqdn'])
            elif row['table_fqdn'] is None:  # Exists in Vanna but not catalog
                changes['deleted'].append(row['table_fqdn'])
            else:
                changes['unchanged'].append(row['table_fqdn'])
        
        return changes
    
    async def sync_changes(self, changes):
        """Apply detected changes"""
        
        # Handle new tables
        for table_fqdn in changes['new']:
            catalog_data = await fetch_catalog_table(table_fqdn)
            await train_new_table(catalog_data)
            logger.info(f"Added new training for {table_fqdn}")
        
        # Handle modified tables
        for table_fqdn in changes['modified']:
            catalog_data = await fetch_catalog_table(table_fqdn)
            await update_table_training(catalog_data)
            logger.info(f"Updated training for {table_fqdn}")
        
        # Handle deleted tables
        for table_fqdn in changes['deleted']:
            await remove_table_training(table_fqdn)
            logger.info(f"Removed training for {table_fqdn}")
```

### 5. Versioning Strategy

```python
class CatalogVersionManager:
    """Manage catalog versions and training data versions"""
    
    def __init__(self):
        self.version_table = "catalog_sync_versions"
    
    async def create_sync_snapshot(self):
        """Create a snapshot before sync"""
        snapshot_id = str(uuid.uuid4())
        
        query = f"""
        INSERT INTO `{self.version_table}` (
            snapshot_id,
            snapshot_timestamp,
            catalog_export_version,
            tables_count,
            sync_status,
            metadata
        )
        SELECT 
            '{snapshot_id}',
            CURRENT_TIMESTAMP(),
            MAX(last_updated_ts) as catalog_export_version,
            COUNT(DISTINCT table_fqdn) as tables_count,
            'in_progress' as sync_status,
            TO_JSON_STRING(STRUCT(
                COUNT(DISTINCT business_domain) as domains_count,
                SUM(row_count) as total_rows
            )) as metadata
        FROM `bigquerylascoot.metadata_data_dictionary.Table_Metadata`
        WHERE status = 'In Use'
        """
        
        await run_query(query)
        return snapshot_id
    
    async def complete_sync_snapshot(self, snapshot_id, changes):
        """Mark snapshot as complete with results"""
        query = f"""
        UPDATE `{self.version_table}`
        SET 
            sync_status = 'completed',
            sync_completed_ts = CURRENT_TIMESTAMP(),
            changes_applied = TO_JSON_STRING(STRUCT(
                {len(changes['new'])} as new_count,
                {len(changes['modified'])} as modified_count,
                {len(changes['deleted'])} as deleted_count
            ))
        WHERE snapshot_id = '{snapshot_id}'
        """
        
        await run_query(query)
```

### 6. Bulk Operations

```python
class CatalogBulkOperations:
    """Handle bulk sync operations efficiently"""
    
    async def full_resync(self):
        """Complete resync from catalog"""
        
        # Step 1: Create backup
        backup_table = f"ddl_training_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        await create_backup(backup_table)
        
        # Step 2: Mark all catalog-sourced training as pending deletion
        await mark_all_pending_deletion()
        
        # Step 3: Sync all current catalog data
        catalog_data = await fetch_all_catalog_data()
        
        # Step 4: Bulk insert with source tracking
        batch_size = 100
        for i in range(0, len(catalog_data), batch_size):
            batch = catalog_data[i:i+batch_size]
            await bulk_train_with_tracking(batch)
        
        # Step 5: Delete items not found in current catalog
        await delete_pending_items()
        
        # Step 6: Verify integrity
        await verify_sync_integrity()
    
    async def incremental_sync(self, since_timestamp=None):
        """Incremental sync based on timestamp"""
        
        if not since_timestamp:
            # Get last successful sync
            since_timestamp = await get_last_sync_timestamp()
        
        # Only process items changed since last sync
        query = f"""
        SELECT * FROM `bigquerylascoot.metadata_data_dictionary.Table_Metadata`
        WHERE last_updated_ts > '{since_timestamp}'
            AND status = 'In Use'
        """
        
        changed_items = await run_query(query)
        
        for item in changed_items:
            await sync_single_item(item)
```

### 7. Deduplication Strategy

```python
async def prevent_duplicates():
    """Ensure no duplicate training data"""
    
    # Remove duplicates keeping the most recent
    dedup_query = """
    DELETE FROM `{project}.{dataset}.ddl_training` t1
    WHERE source_type = 'catalog'
        AND EXISTS (
            SELECT 1 
            FROM `{project}.{dataset}.ddl_training` t2
            WHERE t1.source_id = t2.source_id
                AND t1.source_type = t2.source_type
                AND t1.id < t2.id  -- Keep the newer record
        )
    """
    
    await run_query(dedup_query)
```

### 8. Monitoring and Alerting

```python
class CatalogSyncMonitor:
    """Monitor catalog sync health"""
    
    async def check_sync_health(self):
        """Check for sync issues"""
        
        health_query = """
        WITH sync_stats AS (
            SELECT 
                source_type,
                sync_status,
                COUNT(*) as count,
                MIN(last_sync_attempt) as oldest_sync,
                MAX(last_sync_attempt) as newest_sync
            FROM `{project}.{dataset}.ddl_training`
            WHERE source_type = 'catalog'
            GROUP BY source_type, sync_status
        )
        SELECT 
            *,
            TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), oldest_sync, DAY) as days_since_oldest
        FROM sync_stats
        """
        
        results = await run_query(health_query)
        
        alerts = []
        for stat in results:
            if stat['sync_status'] == 'outdated' and stat['count'] > 10:
                alerts.append(f"Warning: {stat['count']} outdated catalog items")
            
            if stat['days_since_oldest'] > 7:
                alerts.append(f"Warning: Some items haven't synced in {stat['days_since_oldest']} days")
        
        return alerts
```

## Implementation in Vanna MCP Tools

### Enhanced vanna_train Tool

```python
@mcp_server.tool()
async def vanna_train_from_catalog(
    source: str = "catalog",
    mode: str = "incremental",  # 'incremental', 'full', 'verify'
    dry_run: bool = False
) -> Dict[str, Any]:
    """Train Vanna from Data Catalog with source tracking"""
    
    tracker = CatalogTrainingTracker()
    sync_manager = CatalogSyncManager()
    
    # Detect changes
    changes = await sync_manager.detect_changes()
    
    if dry_run:
        return {
            'mode': mode,
            'changes_detected': {
                'new': len(changes['new']),
                'modified': len(changes['modified']),
                'deleted': len(changes['deleted']),
                'unchanged': len(changes['unchanged'])
            },
            'dry_run': True
        }
    
    # Create snapshot
    snapshot_id = await CatalogVersionManager().create_sync_snapshot()
    
    try:
        if mode == 'full':
            await CatalogBulkOperations().full_resync()
        elif mode == 'incremental':
            await sync_manager.sync_changes(changes)
        elif mode == 'verify':
            await verify_catalog_sync()
        
        # Complete snapshot
        await CatalogVersionManager().complete_sync_snapshot(snapshot_id, changes)
        
        return {
            'success': True,
            'snapshot_id': snapshot_id,
            'changes_applied': changes
        }
        
    except Exception as e:
        logger.error(f"Catalog sync failed: {str(e)}")
        raise
```

## Benefits of This Approach

1. **Traceability**: Every piece of training data knows its source
2. **Efficient Updates**: Only sync what changed
3. **Rollback Capability**: Can revert to previous versions
4. **No Duplicates**: Deduplication built-in
5. **Monitoring**: Know sync health at all times
6. **Selective Sync**: Can sync specific domains or tables
7. **Audit Trail**: Complete history of all syncs

This tracking system ensures we always know which training data came from the catalog and can efficiently manage updates without corrupting the training dataset.