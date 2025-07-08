# Data Catalog Integration Approaches for Vanna MCP Server

## Overview

The Data Catalog system provides a rich semantic layer that can significantly enhance Vanna's SQL generation capabilities. Here are multiple approaches to leverage this information, from simple to advanced.

## Approach 1: Direct Metadata Enrichment (Quick Win)

### Implementation
Create a new tool or enhance existing training to query the catalog tables directly.

```python
# Example: Enhanced DDL training with business context
def train_from_catalog():
    # Get enriched table metadata
    query = """
    SELECT 
        t.table_fqdn,
        t.business_domain,
        t.grain_description,
        t.row_count,
        d.description as dataset_description,
        d.owner_email,
        d.refresh_cadence
    FROM `bigquerylascoot.metadata_data_dictionary.Table_Metadata` t
    JOIN `bigquerylascoot.metadata_data_dictionary.Dataset_Metadata` d
        ON t.dataset_id = d.dataset_id
    WHERE t.status = 'In Use' 
        AND t.exists_flag = TRUE
    """
    
    # Train Vanna with enriched context
    for table in results:
        context = f"""
        Table: {table.table_fqdn}
        Business Domain: {table.business_domain}
        Description: {table.grain_description}
        Dataset Context: {table.dataset_description}
        Data Owner: {table.owner_email}
        Update Frequency: {table.refresh_cadence}
        Current Row Count: {table.row_count:,}
        """
        vanna.train(documentation=context)
```

### Benefits
- Immediate context improvement
- Business terminology understanding
- Data freshness awareness
- Owner identification for questions

## Approach 2: Column-Level Intelligence

### Implementation
Enhance column understanding with statistical profiling data.

```python
# Column profiling integration
def enhance_column_context():
    query = """
    SELECT 
        c.table_id,
        c.column_name,
        c.data_type,
        c.description,
        c.distinct_count,
        c.null_count,
        c.row_count,
        SAFE_DIVIDE(c.null_count, c.row_count) as null_percentage,
        c.top_5_values,
        c.sample_values,
        c.pii_flag
    FROM `bigquerylascoot.metadata_data_dictionary.Column_Metadata` c
    WHERE c.exists_flag = TRUE
    """
    
    # Use statistics for query optimization hints
    for col in results:
        if col.null_percentage > 0.5:
            hint = f"Note: {col.column_name} has {col.null_percentage:.1%} null values"
        
        if col.distinct_count < 100:
            hint = f"Note: {col.column_name} has only {col.distinct_count} distinct values: {col.top_5_values}"
```

### Benefits
- Smart filter suggestions
- NULL handling awareness
- Cardinality-based optimization
- PII-aware query generation

## Approach 3: Query Pattern Learning from Views

### Implementation
Train Vanna with actual SQL patterns from views and Hevo transformations.

```python
# Extract and learn from view queries
def train_from_view_patterns():
    # Get all view definitions
    view_query = """
    SELECT 
        v.view_name,
        v.sql_query,
        t.business_domain,
        t.grain_description
    FROM `bigquerylascoot.metadata_data_dictionary.View_Queries` v
    JOIN `bigquerylascoot.metadata_data_dictionary.Table_Metadata` t
        ON v.view_name = t.table_id
    WHERE t.status = 'In Use'
    """
    
    # Get Hevo transformation queries
    hevo_query = """
    SELECT 
        h.table_fqdn,
        h.hevo_query,
        h.hevo_model_name
    FROM `bigquerylascoot.metadata_data_dictionary.Hevo_Models` h
    WHERE h.hevo_model_status = 'ACTIVE'
    """
    
    # Train with SQL examples
    for view in view_results:
        vanna.train(
            sql=view.sql_query,
            question=f"How to query {view.view_name} for {view.business_domain}?"
        )
```

### Benefits
- Learn from proven query patterns
- Understand complex joins
- Business-specific SQL idioms
- Transformation logic understanding

## Approach 4: Automated Documentation Generation

### Implementation
Generate comprehensive documentation from catalog data.

```python
def generate_table_documentation():
    """Generate markdown documentation for each table"""
    template = """
    # Table: {table_name}
    
    ## Overview
    - **Business Domain**: {business_domain}
    - **Description**: {grain_description}
    - **Row Count**: {row_count:,}
    - **Last Updated**: {last_updated}
    
    ## Columns
    {column_details}
    
    ## Sample Queries
    {sample_queries}
    
    ## Data Quality Notes
    {quality_notes}
    """
    
    # Generate for each table and train Vanna
    for table in tables:
        doc = template.format(...)
        vanna.train(documentation=doc)
```

### Benefits
- Comprehensive context
- Structured information
- Easy to maintain
- Version controlled

## Approach 5: Real-time Context Enhancement

### Implementation
Query catalog in real-time during SQL generation.

```python
class CatalogEnhancedVanna:
    def ask(self, question):
        # Extract table references from question
        tables = extract_table_mentions(question)
        
        # Get real-time metadata
        context = []
        for table in tables:
            metadata = query_catalog_metadata(table)
            context.append(metadata)
        
        # Include context in prompt
        enhanced_question = f"""
        Question: {question}
        
        Context:
        {format_context(context)}
        """
        
        return vanna.ask(enhanced_question)
```

### Benefits
- Always current information
- Dynamic context building
- Handles schema changes
- No retraining needed

## Approach 6: Multi-Tenant Catalog Integration

### Implementation
Extend catalog for multi-tenant support.

```python
# Add tenant awareness to catalog queries
def get_tenant_catalog(tenant_id):
    """Get catalog filtered by tenant access"""
    query = f"""
    SELECT DISTINCT
        t.*,
        c.column_name,
        c.data_type,
        c.description
    FROM `bigquerylascoot.metadata_data_dictionary.Table_Metadata` t
    JOIN `bigquerylascoot.metadata_data_dictionary.Column_Metadata` c
        ON t.table_id = c.table_id
    WHERE t.dataset_id LIKE '%{tenant_id}%'
        OR t.business_domain = '{tenant_id}'
    """
    
    return tenant_specific_catalog
```

### Benefits
- Tenant-specific training
- Access control alignment
- Personalized context
- Security compliance

## Approach 7: JSON Catalog Sync

### Implementation
Periodic sync of the exported JSON catalog.

```python
def sync_catalog_from_json():
    """Sync from Google Drive JSON export"""
    # Download latest catalog export
    catalog_json = download_from_drive("latest_catalog.json")
    
    # Parse hierarchical structure
    for dataset in catalog_json['datasets']:
        for table in dataset['tables']:
            # Create training data
            ddl = generate_ddl_from_catalog(table)
            docs = generate_docs_from_catalog(table)
            
            vanna.train(ddl=ddl)
            vanna.train(documentation=docs)
```

### Benefits
- Offline capability
- Batch processing
- Version control
- Backup/restore

## Approach 8: Intelligent Query Suggestions

### Implementation
Use catalog statistics for smart suggestions.

```python
class SmartSuggestions:
    def suggest_filters(self, table_name):
        """Suggest appropriate filters based on column statistics"""
        columns = get_column_stats(table_name)
        
        suggestions = []
        for col in columns:
            if col.distinct_count < 20:
                suggestions.append(f"Filter by {col.column_name} (values: {col.top_5_values})")
            
            if col.data_type == 'DATE':
                suggestions.append(f"Filter by date range on {col.column_name}")
        
        return suggestions
    
    def warn_about_joins(self, table1, table2):
        """Warn about expensive joins based on cardinality"""
        t1_rows = get_row_count(table1)
        t2_rows = get_row_count(table2)
        
        if t1_rows * t2_rows > 1_000_000_000:
            return "Warning: This join may be expensive. Consider filtering first."
```

### Benefits
- Performance optimization
- User guidance
- Cost awareness
- Better UX

## Implementation Roadmap

### Phase 1: Foundation (Week 1)
1. Create catalog query utilities
2. Implement basic metadata enrichment
3. Add catalog-based training command
4. Test with sample tables

### Phase 2: Enhanced Training (Week 2)
1. View pattern extraction
2. Column statistics integration
3. Documentation generation
4. Bulk training from catalog

### Phase 3: Real-time Integration (Week 3)
1. Dynamic context enhancement
2. Query suggestion system
3. Performance optimization
4. Multi-tenant support

### Phase 4: Advanced Features (Week 4)
1. JSON sync automation
2. Change detection
3. Quality scoring
4. Usage analytics

## Technical Integration Points

### 1. New MCP Tool: `vanna_train_from_catalog`
```python
@mcp_server.tool()
async def vanna_train_from_catalog(
    dataset_filter: Optional[str] = None,
    business_domain: Optional[str] = None,
    include_views: bool = True,
    include_statistics: bool = True
) -> Dict[str, Any]:
    """Train Vanna using Data Catalog metadata"""
    # Implementation
```

### 2. Enhanced `vanna_ask` with Catalog Context
```python
# Modify existing vanna_ask to include catalog lookup
async def enhanced_ask(question: str):
    # Extract entities
    entities = extract_entities(question)
    
    # Get catalog context
    context = await get_catalog_context(entities)
    
    # Include in prompt
    enhanced_prompt = build_enhanced_prompt(question, context)
    
    return vanna.ask(enhanced_prompt)
```

### 3. Catalog Sync Service
```python
# Background service for catalog updates
class CatalogSyncService:
    async def sync_periodically(self):
        while True:
            await self.sync_catalog()
            await asyncio.sleep(3600)  # Hourly
```

## Expected Benefits

1. **Accuracy Improvement**: 40-60% better SQL generation with business context
2. **Reduced Training Time**: Auto-training from catalog vs manual DDL
3. **Better User Experience**: Contextual suggestions and warnings
4. **Maintenance Efficiency**: Single source of truth for metadata
5. **Security Enhancement**: PII awareness and access control

## Challenges and Mitigations

### Challenge 1: Catalog Freshness
- **Mitigation**: Implement change detection and incremental updates

### Challenge 2: Performance Impact
- **Mitigation**: Cache frequently accessed metadata

### Challenge 3: Schema Evolution
- **Mitigation**: Version tracking and migration scripts

### Challenge 4: Multi-tenant Complexity
- **Mitigation**: Tenant-aware catalog views

## Conclusion

The Data Catalog integration offers multiple approaches from simple metadata enrichment to sophisticated real-time context enhancement. Starting with basic metadata queries and progressively adding advanced features will provide immediate value while building toward a comprehensive solution.

The recommended approach is to start with Approach 1 and 3 (metadata enrichment and view pattern learning) as they provide the highest ROI with minimal complexity, then progressively add other approaches based on user feedback and requirements.