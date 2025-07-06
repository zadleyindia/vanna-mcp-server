#!/bin/bash

# Template for Claude Code configuration
# Copy this to setup_claude_code.sh and fill in your actual values
# DO NOT commit setup_claude_code.sh with real credentials!

cat > ~/.config/claude-code/config.json << 'EOF'
{
  "OPENAI_API_KEY": "${OPENAI_API_KEY}",
  "SUPABASE_URL": "${SUPABASE_URL}",
  "SUPABASE_KEY": "${SUPABASE_KEY}",
  "SUPABASE_DB_PASSWORD": "${SUPABASE_DB_PASSWORD}",
  "BIGQUERY_PROJECT": "${BIGQUERY_PROJECT}",
  "DATABASE_TYPE": "bigquery",
  "VANNA_SCHEMA": "vannabq",
  "ENABLE_MULTI_TENANT": "true",
  "TENANT_ID": "${DEFAULT_TENANT_ID}",
  "ENABLE_SHARED_KNOWLEDGE": "true",
  "ALLOWED_TENANTS": "${ALLOWED_TENANTS}",
  "ACCESS_CONTROL_MODE": "whitelist",
  "ACCESS_CONTROL_DATASETS": "${ACCESS_CONTROL_DATASETS}",
  "MANDATORY_QUERY_VALIDATION": "true",
  "MAX_QUERY_RESULTS": "10000",
  "LOG_LEVEL": "INFO",
  "INCLUDE_LEGACY_DATA": "false",
  "STRICT_TENANT_ISOLATION": "true"
}
EOF

echo "Configuration template created."
echo "To use this template:"
echo "1. Copy to setup_claude_code.sh"
echo "2. Replace all \${VARIABLE} placeholders with actual values"
echo "3. Run: chmod +x setup_claude_code.sh && ./setup_claude_code.sh"
echo ""
echo "Example environment variables to set:"
echo "export OPENAI_API_KEY='your-openai-key'"
echo "export SUPABASE_URL='https://your-project.supabase.co'"
echo "export SUPABASE_KEY='your-anon-key'"
echo "export SUPABASE_DB_PASSWORD='your-db-password'"
echo "export BIGQUERY_PROJECT='your-project-id'"
echo "export DEFAULT_TENANT_ID='default-tenant'"
echo "export ALLOWED_TENANTS='tenant1,tenant2,tenant3'"
echo "export ACCESS_CONTROL_DATASETS='DATASET1,DATASET2'"