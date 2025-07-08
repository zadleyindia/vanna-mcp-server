# Data Catalog System - Understanding Document

## Executive Summary

The Data Catalog system is a Google Apps Script-based metadata management solution that maintains a comprehensive inventory of BigQuery datasets, tables, columns, and their associated business metadata. It serves as a central repository for understanding the data warehouse structure, data quality, and business context.

## System Architecture

### Technology Stack
- **Frontend**: Google Sheets (UI for metadata management)
- **Backend**: Google Apps Script
- **Storage**: BigQuery (`bigquerylascoot.metadata_data_dictionary`)
- **Integration**: Hevo API for data pipeline metadata
- **Export**: Google Drive (JSON catalog exports)

### Data Flow
```
BigQuery INFORMATION_SCHEMA → Apps Script → Google Sheets → User Edits → BigQuery Storage
                                    ↓
                              Hevo API → Pipeline Metadata
                                    ↓
                            JSON Export → Google Drive
```

## Core Components

### 1. Dataset Management
**Purpose**: Track and manage BigQuery dataset metadata

**Key Features**:
- Automatic sync from BigQuery to Sheets
- Bi-directional description updates
- Business metadata tracking (owner, domain, refresh cadence)
- Aggregate row count calculation
- Status management (In Use / Deprecated)

**Data Points**:
- Dataset identification (project, dataset_id)
- Business domain classification
- Owner email
- Source system
- Refresh cadence
- Row count (aggregated)
- Last update timestamp

### 2. Table Management
**Purpose**: Comprehensive table and view inventory

**Key Features**:
- Distinguishes between tables and views
- Tracks table-level metrics (rows, columns)
- Column profiling scheduling
- Business grain descriptions
- Excludes raw tables (sql_ prefix) optionally
- Captures view SQL queries

**Data Points**:
- Table/view identification
- Object type (TABLE/VIEW/MATERIALIZED_VIEW)
- Row and column counts
- Last modified timestamp
- Business domain
- Grain description
- Column profiling status

### 3. Column Profiling
**Purpose**: Deep column-level analysis and statistics

**Key Features**:
- Statistical profiling (distinct, null, blank counts)
- Value distribution (min, max, average)
- Top 5 frequent values identification
- Sample value collection
- PII-aware sampling (hides PII data)
- Error logging for failed profiles

**Data Points**:
- Column identification and data type
- Nullability constraints
- Statistical metrics
- Value samples
- PII flags
- Profile timestamps

### 4. View Query Tracking
**Purpose**: Maintain SQL definitions for all views

**Features**:
- Captures complete view SQL
- Distinguishes standard vs materialized views
- Links to table metadata
- Version tracking through timestamps

### 5. Hevo Integration
**Purpose**: Track data pipeline transformations

**Features**:
- Fetches transformation models via API
- Maps Hevo models to BigQuery tables
- Stores transformation SQL
- Tracks pipeline execution status

## Key BigQuery Tables

### 1. `Dataset_Metadata`
```sql
CREATE TABLE metadata_data_dictionary.Dataset_Metadata (
  project_id STRING,
  dataset_id STRING,
  dataset_fqdn STRING,
  business_domain STRING,
  dataset_type STRING,
  owner_email STRING,
  refresh_cadence STRING,
  source_system STRING,
  description STRING,
  row_count_last_audit INT64,
  last_updated_ts TIMESTAMP,
  status STRING
)
```

### 2. `Table_Metadata`
```sql
CREATE TABLE metadata_data_dictionary.Table_Metadata (
  project_id STRING,
  dataset_id STRING,
  table_id STRING,
  table_fqdn STRING,
  object_type STRING,
  business_domain STRING,
  grain_description STRING,
  row_count INT64,
  column_count INT64,
  last_updated_ts TIMESTAMP,
  column_profile_last_audit TIMESTAMP,
  column_profile_due BOOL,
  status STRING,
  exists_flag BOOL
)
```

### 3. `Column_Metadata`
```sql
CREATE TABLE metadata_data_dictionary.Column_Metadata (
  project_id STRING,
  dataset_id STRING,
  table_id STRING,
  column_name STRING,
  data_type STRING,
  is_nullable STRING,
  description STRING,
  distinct_count INT64,
  null_count INT64,
  blank_count INT64,
  row_count INT64,
  min_value STRING,
  max_value STRING,
  average_value STRING,
  top_5_values STRING,
  sample_values STRING,
  profile_timestamp TIMESTAMP,
  pii_flag BOOL,
  exists_flag BOOL
)
```

### 4. `View_Queries`
```sql
CREATE TABLE metadata_data_dictionary.View_Queries (
  project_id STRING,
  dataset_id STRING,
  view_name STRING,
  sql_query STRING,
  view_type STRING
)
```

### 5. `Hevo_Models`
```sql
CREATE TABLE metadata_data_dictionary.Hevo_Models (
  table_fqdn STRING,
  hevo_model_id STRING,
  hevo_model_name STRING,
  hevo_query STRING,
  hevo_model_last_run_at TIMESTAMP,
  hevo_model_status STRING
)
```

## Business Value

### 1. Data Discovery
- Quick identification of relevant tables/columns
- Business context through descriptions and domains
- Understanding of data freshness and update patterns

### 2. Data Quality
- Column-level statistics reveal data quality issues
- Null/blank analysis helps understand completeness
- Sample values provide quick data understanding

### 3. Compliance
- PII flagging for sensitive data
- Owner tracking for accountability
- Status tracking for deprecated objects

### 4. Development Support
- View SQL provides query examples
- Hevo queries show transformation logic
- Column statistics inform query optimization

## Integration Opportunities with Vanna

### 1. Enhanced Context Building
```python
# Query catalog for table context
SELECT 
  t.table_fqdn,
  t.grain_description,
  t.business_domain,
  t.row_count,
  t.column_count
FROM `bigquerylascoot.metadata_data_dictionary.Table_Metadata` t
WHERE t.status = 'In Use' 
  AND t.exists_flag = TRUE
```

### 2. Column Understanding
```python
# Get column details with statistics
SELECT 
  c.column_name,
  c.data_type,
  c.description,
  c.distinct_count,
  c.null_count,
  c.top_5_values,
  c.sample_values
FROM `bigquerylascoot.metadata_data_dictionary.Column_Metadata` c
WHERE c.table_id = 'target_table'
  AND c.exists_flag = TRUE
```

### 3. Query Pattern Learning
```python
# Analyze view queries for patterns
SELECT 
  v.view_name,
  v.sql_query
FROM `bigquerylascoot.metadata_data_dictionary.View_Queries` v
WHERE v.dataset_id = 'target_dataset'
```

### 4. JSON Catalog Import
```python
# The exported JSON structure
{
  "datasets": [
    {
      "dataset_id": "example_dataset",
      "tables": [
        {
          "table_id": "example_table",
          "columns": [
            {
              "column_name": "id",
              "data_type": "INT64",
              "statistics": {...}
            }
          ]
        }
      ]
    }
  ]
}
```

## Recommended Integration Strategy

### Phase 1: Direct Metadata Query
- Configure Vanna to query catalog tables directly
- Use metadata for enriched table/column descriptions
- Leverage statistics for query optimization hints

### Phase 2: Training Data Enhancement
- Use view queries as SQL examples for training
- Extract common patterns from Hevo transformations
- Include business descriptions in training context

### Phase 3: Real-time Context
- Implement periodic sync of catalog data
- Use column statistics for smart query generation
- Apply PII flags for security considerations

### Phase 4: Advanced Features
- Auto-generate documentation from catalog
- Suggest queries based on similar view patterns
- Provide data quality warnings based on statistics

## Security Considerations

1. **PII Handling**: System flags PII columns and hides sample data
2. **Access Control**: Leverages Google Sheets permissions
3. **Audit Trail**: Tracks all updates with timestamps
4. **Data Masking**: Sample values excluded for sensitive columns

## Maintenance and Updates

The catalog is maintained through:
1. **Scheduled Syncs**: Regular updates from BigQuery
2. **Manual Triggers**: Menu-driven updates in Sheets
3. **API Integration**: Automatic Hevo metadata refresh
4. **Export Schedule**: Periodic JSON exports to Drive

## Conclusion

The Data Catalog system provides a robust foundation for understanding the data warehouse. Its comprehensive metadata, statistical profiling, and business context make it an ideal complement to Vanna's natural language SQL capabilities. Integration would significantly enhance Vanna's ability to generate accurate, context-aware queries while respecting data governance requirements.