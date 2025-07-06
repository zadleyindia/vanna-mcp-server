# Installation Guide

This guide provides detailed instructions for installing and configuring the Vanna MCP Server with multi-database and multi-tenant support.

## Prerequisites

### Required Software
- Python 3.10 or higher
- pip (Python package manager)
- Git

### Required Accounts
- **Supabase Account**: For vector storage with pgvector
- **OpenAI API Key**: For embeddings and SQL generation
- **Database Access**: Depending on your chosen database type:
  - **BigQuery**: Google Cloud account with BigQuery enabled
  - **PostgreSQL**: PostgreSQL server credentials
  - **MS SQL Server**: SQL Server credentials

## Installation Steps

### 1. Clone the Repository

```bash
git clone <repository-url>
cd vanna-mcp-server
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### 3. Install Dependencies

The project uses a forked version of Vanna with metadata support:

```bash
pip install -r requirements.txt
```

This will install:
- Forked Vanna from https://github.com/zadleyindia/vanna
- FastMCP for MCP server functionality
- Database drivers (psycopg2, google-cloud-bigquery, etc.)
- Other required dependencies

### 4. Configure Environment

#### Option A: Using .env file (Development)

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# OpenAI Configuration
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4  # or gpt-3.5-turbo

# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
SUPABASE_DB_PASSWORD=your-db-password

# Database Type Configuration
DATABASE_TYPE=bigquery  # Options: bigquery, postgres, mssql

# BigQuery Configuration (if using BigQuery)
BIGQUERY_PROJECT=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# PostgreSQL Configuration (if using PostgreSQL)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DATABASE=your-db
POSTGRES_USER=your-user
POSTGRES_PASSWORD=your-password

# MS SQL Server Configuration (if using MS SQL)
MSSQL_SERVER=your-server
MSSQL_DATABASE=your-db
MSSQL_USER=your-user
MSSQL_PASSWORD=your-password

# Multi-Tenant Configuration
ENABLE_MULTI_TENANT=false  # Set to true for multi-tenant support
TENANT_ID=default
ALLOWED_TENANTS=tenant1,tenant2,tenant3
ENABLE_SHARED_KNOWLEDGE=true

# Access Control (optional)
ACCESS_CONTROL_MODE=whitelist
ACCESS_CONTROL_DATASETS=dataset1,dataset2

# Other Settings
LOG_LEVEL=INFO
VANNA_SCHEMA=public  # Schema for Vanna tables
```

#### Option B: Using MCP Configuration (Production)

For Claude Desktop integration, configure in `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "vanna-mcp": {
      "command": "python",
      "args": ["/Users/mohit/claude/vanna-mcp-server/server.py"],
      "env": {
        "PYTHONPATH": "/Users/mohit/claude/vanna-mcp-server"
      },
      "config": {
        "OPENAI_API_KEY": "sk-...",
        "SUPABASE_URL": "https://lohggakrufbclcccamaj.supabase.co",
        "SUPABASE_KEY": "eyJ...",
        "SUPABASE_DB_PASSWORD": "your-password",
        "BIGQUERY_PROJECT": "bigquerylascoot",
        "DATABASE_TYPE": "bigquery",
        "ENABLE_MULTI_TENANT": "true",
        "TENANT_ID": "default",
        "ALLOWED_TENANTS": "acme_corp,xyz_inc,test_corp",
        "ENABLE_SHARED_KNOWLEDGE": "true"
      }
    }
  }
}
```

### 5. Initialize Database Schema

The vector store requires proper table structure in Supabase:

```bash
python scripts/setup_database.py
```

This script will:
- Connect to your Supabase instance
- Create necessary tables if they don't exist
- Verify pgvector extension is enabled
- Set up proper indexes for performance

### 6. Verify Installation

Run the test script to verify everything is working:

```bash
python scripts/test_basic_functionality.py
```

This will test:
- Database connectivity
- Vector store operations
- Basic training and retrieval
- Multi-tenant isolation (if enabled)

## Database-Specific Setup

### BigQuery Setup

1. Create a service account in Google Cloud Console
2. Download the JSON key file
3. Set `GOOGLE_APPLICATION_CREDENTIALS` to the path of the JSON file
4. Grant necessary BigQuery permissions to the service account

### PostgreSQL Setup

1. Ensure PostgreSQL server is running
2. Create a database for your application
3. Configure connection details in `.env`

### MS SQL Server Setup

1. Ensure SQL Server is accessible
2. Create a database for your application
3. Configure connection details in `.env`

## Troubleshooting

### Common Issues

1. **Import Error for fastmcp**
   ```bash
   pip install fastmcp --upgrade
   ```

2. **Supabase Connection Error**
   - Verify your Supabase URL and keys
   - Check if pgvector extension is enabled
   - Ensure database password is correct

3. **Vector Type Casting Error**
   - This is a known limitation with the current implementation
   - The filtered vector store uses placeholder similarity scores
   - Functionality is not affected, only ranking quality

4. **Permission Denied**
   - Ensure Python has execute permissions
   - Check file ownership and permissions

### Verification Commands

Test individual components:

```bash
# Test Supabase connection
python scripts/test_supabase_connection.py

# Test vector store
python scripts/test_filtered_vector_isolation.py

# Test MCP server
python scripts/test_mcp_server.py
```

## Next Steps

1. **Configure for your use case**:
   - Single database or multi-database
   - Single tenant or multi-tenant
   - Access control requirements

2. **Train initial data**:
   - Load DDL statements
   - Add documentation
   - Train with example queries

3. **Integrate with Claude Desktop**:
   - Update claude_desktop_config.json
   - Restart Claude Desktop
   - Test the MCP tools

See [docs/CLAUDE_DESKTOP_TENANT_USAGE.md](CLAUDE_DESKTOP_TENANT_USAGE.md) for usage instructions.