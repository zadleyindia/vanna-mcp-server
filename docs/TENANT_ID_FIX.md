# Fix: Added tenant_id Parameter to vanna_train

## Issue
The initial implementation was missing the `tenant_id` parameter in the `vanna_train` tool, which meant users couldn't override the default tenant when training data.

## Solution
Added `tenant_id` parameter to `vanna_train` to match the functionality in `vanna_ask`.

## Changes Made

### 1. server.py
- Added `tenant_id: Optional[str] = None` parameter to `handle_vanna_train()`
- Updated docstring to document the parameter
- Pass tenant_id to the vanna_train implementation

### 2. src/tools/vanna_train.py
- Added `tenant_id: Optional[str] = None` parameter to `vanna_train()`
- Updated docstring to document the parameter
- Pass tenant_id to all vn.train() calls
- Updated success message to show effective tenant (tenant_id or settings.TENANT_ID)
- Updated _store_training_history() to include tenant_id

### 3. scripts/test_multi_tenant.py
- Added test case 2.5 to demonstrate training for a different tenant

## Usage Example

```python
# Train for default tenant (from settings)
await vanna_train(
    training_type="ddl",
    content="CREATE TABLE ...",
)

# Train for specific tenant (override)
await vanna_train(
    training_type="ddl", 
    content="CREATE TABLE ...",
    tenant_id="singla"  # Override default tenant
)

# Train as shared knowledge (all tenants)
await vanna_train(
    training_type="documentation",
    content="Best practices...",
    is_shared=True  # Ignores tenant_id, uses "shared"
)
```

## Behavior

1. If `is_shared=True`, the data is stored with `tenant_id="shared"` (ignores tenant_id parameter)
2. If `is_shared=False` and `tenant_id` is provided, uses the provided tenant_id
3. If `is_shared=False` and `tenant_id` is None, uses `settings.TENANT_ID`
4. In single-tenant mode (`ENABLE_MULTI_TENANT=false`), tenant_id is ignored

This gives users full control over which tenant receives the training data, matching the flexibility provided in vanna_ask.