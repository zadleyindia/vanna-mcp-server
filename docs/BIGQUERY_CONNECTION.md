# BigQuery Connection Guide

This document explains how the Vanna MCP Server connects to and interacts with BigQuery.

## Overview

The Vanna MCP Server uses BigQuery as its primary data source for SQL generation. The connection is managed through Vanna's built-in BigQuery integration, with additional access control and security features.

## Connection Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Claude MCP    │────▶│  Vanna Server   │────▶│    BigQuery     │
│     Client      │     │   (Python)      │     │    Dataset      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │    Supabase     │
                        │  (Vector Store) │
                        └─────────────────┘
```

## Configuration

### Required Settings

```json
{
  "BIGQUERY_PROJECT": "your-project-id",
  "GOOGLE_APPLICATION_CREDENTIALS": "/path/to/service-account.json",  // Optional
  "ACCESS_CONTROL_MODE": "whitelist",
  "ACCESS_CONTROL_DATASETS": "dataset1,dataset2,dataset3"
}
```

### Configuration Parameters

| Parameter | Description | Default | Required |
|-----------|-------------|---------|----------|
| `BIGQUERY_PROJECT` | Your Google Cloud Project ID | - | Yes |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account JSON file | Uses ADC | No |
| `ACCESS_CONTROL_MODE` | Access control type: "whitelist" or "blacklist" | "whitelist" | No |
| `ACCESS_CONTROL_DATASETS` | Comma-separated list of datasets | "" (empty) | No |

## Authentication Methods

The server supports three authentication methods, in order of precedence:

### 1. Service Account JSON (Recommended for Production)

```json
// In MCP configuration
"GOOGLE_APPLICATION_CREDENTIALS": "/path/to/service-account.json"
```

Create a service account with minimal permissions:
- `bigquery.dataViewer` on allowed datasets
- `bigquery.jobUser` for query execution

### 2. Application Default Credentials (Development)

For local development, authenticate using gcloud:

```bash
gcloud auth application-default login
```

### 3. Compute Engine Default Service Account

When running on Google Cloud infrastructure, it automatically uses the attached service account.

## How Connection Works

### 1. Initial Setup

When the server starts:
1. Vanna is initialized with the BigQuery project ID
2. Authentication is established using one of the methods above
3. Connection is validated by listing available datasets

### 2. Query Generation Flow

```python
# When user asks a question:
1. Vanna retrieves relevant training data from Supabase
2. Generates SQL using OpenAI GPT-4
3. Validates the generated SQL against BigQuery schema
4. Returns the SQL query (does not execute)
```

### 3. Training Data Flow

```python
# When adding training data:
1. DDL extraction connects directly to BigQuery
2. Retrieves table schemas and metadata
3. Stores in Supabase vector database
4. Used for future SQL generation
```

## Access Control

### Dataset-Level Security

The server implements dataset-level access control:

```python
# Whitelist mode (recommended)
ACCESS_CONTROL_MODE = "whitelist"
ACCESS_CONTROL_DATASETS = "sales_data,customer_data"
# Only these datasets can be queried

# Blacklist mode
ACCESS_CONTROL_MODE = "blacklist"
ACCESS_CONTROL_DATASETS = "sensitive_data,pii_data"
# These datasets are blocked
```

### Implementation Details

Access control is enforced at multiple levels:

1. **DDL Extraction**: Only allowed datasets are processed
2. **SQL Generation**: Vanna is trained only on allowed tables
3. **Query Validation**: Generated SQL is checked for dataset access

## Setting Up BigQuery Connection

### Step 1: Create Service Account (Recommended)

```bash
# Create service account
gcloud iam service-accounts create vanna-mcp-server \
    --description="Service account for Vanna MCP Server" \
    --display-name="Vanna MCP Server"

# Grant permissions
gcloud projects add-iam-policy-binding YOUR-PROJECT-ID \
    --member="serviceAccount:vanna-mcp-server@YOUR-PROJECT-ID.iam.gserviceaccount.com" \
    --role="roles/bigquery.dataViewer"

gcloud projects add-iam-policy-binding YOUR-PROJECT-ID \
    --member="serviceAccount:vanna-mcp-server@YOUR-PROJECT-ID.iam.gserviceaccount.com" \
    --role="roles/bigquery.jobUser"

# Create and download key
gcloud iam service-accounts keys create ~/vanna-service-account.json \
    --iam-account=vanna-mcp-server@YOUR-PROJECT-ID.iam.gserviceaccount.com
```

### Step 2: Configure MCP Server

Update your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "vanna-mcp": {
      "command": "python",
      "args": ["/path/to/vanna-mcp-server/server.py"],
      "config": {
        "BIGQUERY_PROJECT": "your-project-id",
        "GOOGLE_APPLICATION_CREDENTIALS": "/Users/you/vanna-service-account.json",
        "ACCESS_CONTROL_MODE": "whitelist",
        "ACCESS_CONTROL_DATASETS": "sales_data,customer_data,product_data"
      }
    }
  }
}
```

### Step 3: Test Connection

Use the test script to verify connection:

```bash
cd /path/to/vanna-mcp-server
source venv/bin/activate
python scripts/test_setup.py
```

## Troubleshooting

### Common Issues

1. **"No datasets found"**
   - Check `BIGQUERY_PROJECT` is correct
   - Verify authentication (run `gcloud auth list`)
   - Ensure service account has permissions

2. **"Permission denied"**
   - Service account needs `bigquery.dataViewer` role
   - Check dataset-level permissions
   - Verify `ACCESS_CONTROL_DATASETS` includes your datasets

3. **"Could not find credentials"**
   - Set `GOOGLE_APPLICATION_CREDENTIALS` to service account path
   - Or run `gcloud auth application-default login`

### Debug Mode

Enable debug logging to see connection details:

```json
"LOG_LEVEL": "DEBUG"
```

## Security Best Practices

1. **Use Service Accounts**: Avoid using personal credentials in production
2. **Minimal Permissions**: Grant only required BigQuery permissions
3. **Dataset Whitelisting**: Always use whitelist mode for production
4. **Credential Security**: Store service account keys securely
5. **Audit Logging**: Monitor BigQuery audit logs for usage

## Code References

- BigQuery client initialization: `scripts/extract_bigquery_ddl.py:27`
- Access control implementation: `scripts/extract_bigquery_ddl.py:47-60`
- Vanna BigQuery integration: Built into Vanna base classes
- Dataset validation: `src/tools/vanna_train.py:158-170`

## Next Steps

1. Set up service account with appropriate permissions
2. Configure dataset access control
3. Extract DDL from your BigQuery tables
4. Start training Vanna with your data patterns