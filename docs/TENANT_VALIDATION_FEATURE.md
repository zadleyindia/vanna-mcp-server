# Tenant Validation Feature

## Overview
Added tenant validation to prevent mistakes and unauthorized access by maintaining an allowed tenants list in the configuration.

## Configuration

### New Setting
```bash
ALLOWED_TENANTS="zaldey,singla,customer1"  # Comma-separated list
```

### Behavior
- **Empty/Not Set**: All tenant IDs are allowed (default behavior)
- **Set with values**: Only listed tenants can be used
- **Special case**: "shared" is always allowed when `ENABLE_SHARED_KNOWLEDGE=true`

## Implementation Details

### 1. Settings.py Changes
- Added `ALLOWED_TENANTS` configuration parameter
- Added `get_allowed_tenants()` method to parse the comma-separated list
- Added `is_tenant_allowed(tenant_id)` method for validation
- Updated `validate_config()` to check if default tenant is allowed

### 2. Tool Validation
Both `vanna_ask` and `vanna_train` now validate tenant_id:
- Check if multi-tenant mode is enabled
- Check if provided tenant_id is in allowed list
- Return error with helpful message if not allowed

### 3. Error Response
When validation fails:
```json
{
  "error": "Tenant 'invalid_tenant' is not allowed",
  "allowed_tenants": ["zaldey", "singla", "customer1"],
  "suggestions": ["Use one of the allowed tenants", "Check your tenant configuration"]
}
```

## Usage Examples

### Configuration Examples

#### 1. Development Environment
```json
{
  "ALLOWED_TENANTS": "dev,test,staging",
  "TENANT_ID": "dev"
}
```

#### 2. Production Lock
```json
{
  "ALLOWED_TENANTS": "production",
  "TENANT_ID": "production"
}
```

#### 3. Multi-Customer Setup
```json
{
  "ALLOWED_TENANTS": "customer1,customer2,customer3,demo",
  "TENANT_ID": "customer1"
}
```

### Code Examples

```python
# This will fail if "unauthorized" is not in ALLOWED_TENANTS
result = await vanna_ask(
    query="Show sales data",
    tenant_id="unauthorized"
)
# Error: Tenant 'unauthorized' is not allowed

# This will succeed if "customer2" is in ALLOWED_TENANTS
result = await vanna_train(
    training_type="ddl",
    content="CREATE TABLE ...",
    tenant_id="customer2"
)
# Success: Added training data for tenant 'customer2'
```

## Benefits

1. **Typo Prevention**: Catches misspelled tenant IDs immediately
2. **Security**: Prevents unauthorized tenant access
3. **Clarity**: Makes authorized tenants explicit in configuration
4. **Flexibility**: Can be disabled by leaving empty
5. **Helpful Errors**: Shows allowed tenants when validation fails

## Testing

Run the validation test:
```bash
# Test without restrictions
python scripts/test_tenant_validation.py

# Test with restrictions
ALLOWED_TENANTS="test1,test2" python scripts/test_tenant_validation.py
```

## Migration Guide

### For Existing Deployments
1. No action required - feature is backward compatible
2. Leave `ALLOWED_TENANTS` empty to maintain current behavior
3. Add restrictions when ready: `ALLOWED_TENANTS="tenant1,tenant2"`

### For New Deployments
1. Consider setting `ALLOWED_TENANTS` from the start
2. Include all legitimate tenants
3. Add new tenants as needed

## Best Practices

1. **Use in Production**: Always set `ALLOWED_TENANTS` in production
2. **Document Tenants**: Keep a list of what each tenant represents
3. **Regular Review**: Periodically review and clean up tenant list
4. **Consistent Naming**: Use consistent tenant naming conventions
5. **Test Changes**: Test tenant changes in development first