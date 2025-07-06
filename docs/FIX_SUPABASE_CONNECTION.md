# Fixing Supabase Connection for Vanna

## The Issue

The current configuration is using the Supabase **anon key** in the connection string, but Vanna's pgvector integration requires the actual **postgres database password**.

## Current (Incorrect) Setup

```python
# ❌ This is wrong - using anon key
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
connection_string = f"postgresql://postgres.{project_ref}:{SUPABASE_KEY}@..."
```

## Correct Setup

You need the actual postgres password from your Supabase dashboard.

### Step 1: Get Your Postgres Password

1. Go to your [Supabase Dashboard](https://supabase.com/dashboard)
2. Select your project: `lohggakrufbclcccamaj`
3. Click the **"Connect"** button at the top of the page
4. Look for the connection string, which will show:
   ```
   postgres://postgres.lohggakrufbclcccamaj:[YOUR-PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:6543/postgres
   ```
5. Copy the password (the part after the colon and before the @)

### Step 2: Update Configuration

Create a new environment variable for the database password:

```bash
# In your .env file
SUPABASE_DB_PASSWORD=your-actual-postgres-password
```

### Step 3: Update Connection String

The connection string format should be:

```python
# For pooled connection (recommended) - Note: Check your region!
postgresql://postgres.lohggakrufbclcccamaj:{password}@aws-0-ap-south-1.pooler.supabase.com:6543/postgres

# For direct connection
postgresql://postgres.lohggakrufbclcccamaj:{password}@db.lohggakrufbclcccamaj.supabase.co:5432/postgres
```

### Step 4: Update Settings

Modify `src/config/settings.py` to use the database password:

```python
@classmethod
def get_supabase_connection_string(cls) -> str:
    """Build PostgreSQL connection string for Supabase"""
    if not cls.SUPABASE_URL:
        raise ValueError("SUPABASE_URL must be set")
    
    # Get database password (not the anon key!)
    db_password = get_config("SUPABASE_DB_PASSWORD", "")
    if not db_password:
        raise ValueError("SUPABASE_DB_PASSWORD must be set")
    
    # Extract project ref from URL
    import re
    match = re.search(r'https://([^.]+)\.supabase\.co', cls.SUPABASE_URL)
    if not match:
        raise ValueError("Invalid SUPABASE_URL format")
    
    project_ref = match.group(1)
    
    # Use pooled connection for better performance
    return f"postgresql://postgres.{project_ref}:{db_password}@aws-0-us-west-1.pooler.supabase.com:6543/postgres?options=-csearch_path%3D{cls.VANNA_SCHEMA}"
```

## Important Notes

1. **Security**: The postgres password gives full database access. Keep it secure!
2. **URL Encoding**: If your password contains special characters, URL-encode them:
   - `@` → `%40`
   - `:` → `%3A`
   - `/` → `%2F`
   - `#` → `%23`
3. **Anon Key vs DB Password**: 
   - Anon key: For Supabase client libraries (JavaScript, Python SDK)
   - DB password: For direct PostgreSQL connections (what Vanna uses)

## Testing the Fix

After updating, test with:

```bash
python scripts/test_setup.py
```

Or try a simple connection test:

```python
import psycopg2

conn_string = "postgresql://postgres.lohggakrufbclcccamaj:YOUR_PASSWORD@aws-0-ap-south-1.pooler.supabase.com:6543/postgres"
conn = psycopg2.connect(conn_string)
print("Connected successfully!")
conn.close()
```

## Update Status

**✅ This fix has been implemented in the codebase:**
- `src/config/settings.py` now includes URL encoding for passwords
- Connection string uses the correct region (ap-south-1)
- Configuration files updated to include SUPABASE_DB_PASSWORD
- Both .env and MCP configurations support the database password