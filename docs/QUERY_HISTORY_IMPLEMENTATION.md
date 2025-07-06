# Query History Implementation

## Overview

The Vanna MCP Server now includes a dedicated query history system that tracks all SQL generation requests for analytics and monitoring purposes, completely separate from Vanna's training data.

## Architecture

### Separate Table Design
- **Table**: `{VANNA_SCHEMA}.query_history`
- **Purpose**: Store operational query history separate from training data
- **Schema**: Uses configurable `VANNA_SCHEMA` setting for consistency

### Why Separate from Training Data?
1. **Avoid Confusion**: Query history doesn't interfere with Vanna's similarity search
2. **Better Performance**: Dedicated table with purpose-built indexes
3. **Clean Analytics**: Easy to query and analyze usage patterns
4. **Future Extensibility**: Can add history-specific fields without affecting training

## Database Schema

```sql
CREATE TABLE {VANNA_SCHEMA}.query_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question TEXT NOT NULL,
    generated_sql TEXT NOT NULL,
    execution_time_ms INTEGER,
    confidence_score NUMERIC(3,2), -- 0.00 to 1.00
    tenant_id VARCHAR(255),
    database_type VARCHAR(50),
    executed BOOLEAN DEFAULT false,
    row_count INTEGER,
    error_message TEXT,
    user_feedback VARCHAR(20), -- 'correct', 'incorrect', 'helpful', etc.
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Indexes for Performance
- `idx_{schema}_query_history_created` - Most recent queries first
- `idx_{schema}_query_history_tenant` - Fast tenant filtering
- `idx_{schema}_query_history_confidence` - Performance analysis

## Implementation

### Automatic Storage
Every `vanna_ask` request automatically stores:
- Original natural language question
- Generated SQL query
- Execution time and confidence score
- Tenant ID (for multi-tenant isolation)
- Database type and timestamp

### Storage Function
```python
async def _store_query_history(query: str, sql: str, execution_time_ms: float, confidence: float, tenant_id: str):
    """Store query in dedicated query_history table"""
    # Uses settings.VANNA_SCHEMA for table location
    # Handles multi-tenant isolation
    # Graceful error handling (doesn't break main flow)
```

### Retrieval Tool
The `vanna_get_query_history` MCP tool provides:
- Recent query history with filtering
- Performance analytics and insights
- Multi-tenant aware results
- Configurable limits and options

## Analytics Features

### Basic Metrics
- Total queries and execution count
- Average execution time and confidence scores
- Success rate (queries without errors)
- Database types in use

### Confidence Distribution
- High confidence: ≥ 0.8
- Medium confidence: 0.5 - 0.8
- Low confidence: < 0.5

### Performance Metrics
- Fastest and slowest query times
- Execution time trends
- Error rate analysis

## Multi-Tenant Support

### Tenant Isolation
- All queries tagged with `tenant_id`
- History retrieval filtered by tenant
- Cross-tenant data never exposed

### Shared vs Tenant-Specific
- Tenant-specific queries stored with tenant ID
- Shared knowledge queries marked appropriately
- Analytics respect tenant boundaries

## Configuration

### Schema Configuration
```bash
# Uses same schema as Vanna tables
VANNA_SCHEMA=public  # or custom schema name
```

### Multi-Tenant Settings
```bash
ENABLE_MULTI_TENANT=true
TENANT_ID=default_tenant
STRICT_TENANT_ISOLATION=true
```

## Usage Examples

### View Recent History
```python
# Get last 10 queries for current tenant
result = await vanna_get_query_history(limit=10)

# Get history for specific tenant
result = await vanna_get_query_history(tenant_id="zadley_india", limit=20)

# Get history with detailed analytics
result = await vanna_get_query_history(include_analytics=True)
```

### Sample Response
```json
{
  "queries": [
    {
      "id": "uuid",
      "question": "Show me total sales",
      "sql": "SELECT SUM(amount) FROM sales",
      "confidence_score": 0.85,
      "execution_time_ms": 1250,
      "tenant_id": "zadley",
      "database_type": "bigquery",
      "executed": false,
      "created_at": "2025-01-06T10:30:00Z"
    }
  ],
  "analytics": {
    "total_queries": 47,
    "average_execution_time_ms": 1150,
    "average_confidence_score": 0.78,
    "queries_by_confidence": {
      "high_confidence": 32,
      "medium_confidence": 12,
      "low_confidence": 3
    },
    "success_rate": 0.95
  }
}
```

## Benefits

### For Developers
- **Performance Monitoring**: Track query generation speed
- **Quality Assessment**: Monitor confidence score trends
- **Usage Analytics**: Understand user patterns
- **Debugging**: Error tracking and analysis

### For Users
- **Query History**: See previous questions and results
- **Learning Tool**: Review successful query patterns
- **Performance Insights**: Understand system behavior

### For Administrators
- **Tenant Analytics**: Per-tenant usage statistics
- **System Monitoring**: Overall performance metrics
- **Capacity Planning**: Usage trend analysis
- **Quality Control**: Confidence score monitoring

## Future Enhancements

### Planned Features
- Query execution tracking (when `vanna_execute` is implemented)
- User feedback collection and analysis
- Query similarity detection and recommendations
- Export capabilities (CSV, JSON)
- Dashboard and visualization tools

### Integration Points
- `vanna_execute` tool will update execution status
- Future feedback tools will enhance analytics
- Monitoring systems can query history table directly
- BI tools can connect for advanced analytics

## Database Maintenance

### Data Retention
- Consider implementing automatic cleanup for old records
- Archive historical data for long-term analysis
- Monitor table size and performance impact

### Backup and Recovery
- Include query_history table in backup procedures
- Test restoration processes
- Consider read replicas for analytics workloads

## Security Considerations

### Data Privacy
- Query history may contain sensitive business information
- Implement appropriate access controls
- Consider data retention policies

### Tenant Isolation
- Strict enforcement of tenant boundaries
- No cross-tenant data leakage
- Audit trails for access patterns

## Monitoring and Alerting

### Key Metrics to Monitor
- Query volume trends
- Average response times
- Error rates and patterns
- Confidence score distributions
- Tenant usage patterns

### Suggested Alerts
- Unusual spike in query volume
- Significant increase in error rates
- Drop in average confidence scores
- Long-running query generation times