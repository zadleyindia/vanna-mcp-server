# Testing Multi-Tenant Filtering in Claude Desktop

## Quick Test Guide

### Step 1: Add Training Data for Each Tenant

Copy and paste these commands one by one in Claude Desktop:

#### 1.1 Add DDL for zadley (default tenant)
```
Use the vanna_train tool with:
training_type: ddl
content: CREATE TABLE zadley_orders (order_id INT64, customer_id INT64, order_date DATE, total_amount NUMERIC(10,2), status STRING)
```

#### 1.2 Add DDL for zadley_india tenant
```
Use the vanna_train tool with:
training_type: ddl
content: CREATE TABLE india_sales (sale_id INT64, product_id INT64, sale_date DATE, quantity INT64, revenue NUMERIC(10,2))
tenant_id: zadley_india
```

#### 1.3 Add DDL for zadley_retail tenant
```
Use the vanna_train tool with:
training_type: ddl
content: CREATE TABLE retail_inventory (product_id INT64, store_id INT64, stock_quantity INT64, last_updated TIMESTAMP)
tenant_id: zadley_retail
```

### Step 2: Add SQL Examples for Each Tenant

#### 2.1 SQL for zadley
```
Use the vanna_train tool with:
training_type: sql
question: What are the total orders by status?
content: SELECT status, COUNT(*) as order_count, SUM(total_amount) as total_revenue FROM zadley_orders GROUP BY status
```

#### 2.2 SQL for zadley_india
```
Use the vanna_train tool with:
training_type: sql
question: What are the top selling products?
content: SELECT product_id, SUM(quantity) as total_sold FROM india_sales GROUP BY product_id ORDER BY total_sold DESC LIMIT 10
tenant_id: zadley_india
```

### Step 3: Test Tenant Filtering

#### 3.1 Query as default tenant (zadley)
```
Use the vanna_ask tool with:
query: Show me all orders
```
Expected: Should generate SQL using zadley_orders table

#### 3.2 Query as zadley_india tenant
```
Use the vanna_ask tool with:
query: Show me top products
tenant_id: zadley_india
```
Expected: Should generate SQL using india_sales table

#### 3.3 Test Cross-Tenant Isolation
```
Use the vanna_ask tool with:
query: Show me data from india_sales table
tenant_id: zadley
```
Expected: Should NOT find india_sales table (wrong tenant)

### Step 4: Test Shared Knowledge

#### 4.1 Add shared documentation
```
Use the vanna_train tool with:
training_type: documentation
content: All monetary values are stored in USD. Date fields use YYYY-MM-DD format. Revenue calculations should include tax.
is_shared: true
```

#### 4.2 Query with shared knowledge
```
Use the vanna_ask tool with:
query: What currency are the amounts in?
include_shared: true
```
Expected: Should mention USD from shared documentation

### Step 5: Check Configuration
```
Use the vanna_list_tenants tool
```
This will show current configuration and allowed tenants.

## Expected Results

✅ **Tenant Isolation**: Each tenant only sees their own tables
✅ **Shared Knowledge**: Available to all tenants when include_shared=true
✅ **Cross-Tenant Protection**: Cannot access other tenant's data
✅ **Metadata Storage**: tenant_id stored in JSONB column

## Verification in Supabase

Check the `vanna_embeddings` table in Supabase:
- Look at the `cmetadata` JSONB column
- Verify `tenant_id` field matches the tenant used for training
- Shared items should have `"is_shared": "true"`