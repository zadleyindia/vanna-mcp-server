# Supabase Setup for Vanna MCP Server

## Important: Database Password vs JWT Keys

When connecting to Supabase PostgreSQL, you need to understand the difference between:

1. **JWT Keys (API Keys)** - Used for Supabase client libraries and REST API
   - `anon` key - Public key with RLS (Row Level Security)
   - `service_role` key - Bypasses RLS, full access

2. **Database Password** - Used for direct PostgreSQL connections
   - Found in: Supabase Dashboard > Settings > Database > Connection string
   - This is what you need for `psycopg2` or `sqlalchemy` connections

## Getting Your Database Password

1. Go to your Supabase project dashboard
2. Navigate to Settings > Database
3. Look for "Connection string" section
4. You'll see a connection string like:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.xxxxxxxxxxxx.supabase.co:5432/postgres
   ```
5. The `[YOUR-PASSWORD]` is your database password (not the JWT key!)

## Connection String Formats

### Direct Connection (Recommended for DDL/Schema operations)
```
postgresql://postgres:[YOUR-DATABASE-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
```

### Transaction Pooler (Recommended for applications)
```
postgresql://postgres.[PROJECT-REF]:[YOUR-DATABASE-PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
```

## Current Issue

The error "Tenant or user not found" indicates we're trying to use a JWT key as a database password. These are different!

- JWT keys (like `eyJhbGciOiJIUzI1NiIs...`) are for API access
- Database passwords are regular strings for PostgreSQL connections

## Solution

1. Get your actual database password from Supabase dashboard
2. Update the SUPABASE_KEY in your .env to use the database password
3. Or create a new variable like SUPABASE_DB_PASSWORD

## Testing Connection

Once you have the correct password:

```python
import psycopg2

# Using database password, not JWT key!
conn_str = "postgresql://postgres:[DB-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres"
conn = psycopg2.connect(conn_str)
```

## For Vanna Configuration

Update your configuration to use:
- `SUPABASE_DB_PASSWORD` - Your PostgreSQL password
- `SUPABASE_API_KEY` - Your JWT service_role key (if needed for API calls)

This separation makes it clear which credential is used for what purpose.