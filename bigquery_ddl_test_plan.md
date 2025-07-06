# BigQuery DDL Testing Plan

## Overview
Testing BigQuery DDL extraction and metadata integration with 3 sample e-commerce tables to verify enhanced SQL generation.

## Test Tables

### 1. Orders Table (sales.orders)
**BigQuery Features to Test:**
- Partitioning by DATE(order_date)  
- Clustering by customer_id, product_id
- STRUCT data types (shipping_address)
- NUMERIC precision types
- Fully qualified table names
- BigQuery-specific functions (EXTRACT, CURRENT_TIMESTAMP)

**DDL:**
```sql
CREATE TABLE `ecommerce-project.sales.orders` (
  order_id STRING NOT NULL,
  customer_id STRING NOT NULL,
  product_id STRING NOT NULL,
  order_date DATE NOT NULL,
  order_timestamp TIMESTAMP NOT NULL,
  quantity INTEGER NOT NULL,
  unit_price NUMERIC(10,2) NOT NULL,
  total_amount NUMERIC(12,2) NOT NULL,
  discount_percent NUMERIC(5,2),
  payment_method STRING,
  shipping_address STRUCT<
    street STRING,
    city STRING,
    state STRING,
    zip_code STRING,
    country STRING
  >,
  order_status STRING NOT NULL
)
PARTITION BY DATE(order_date)
CLUSTER BY customer_id, product_id;
```

### 2. Customers Table (customers.profiles)
**BigQuery Features to Test:**
- Partitioning by DATE(registration_date)
- Clustering by customer_tier, DATE(registration_date)
- STRUCT types for address
- BOOLEAN and INTEGER defaults
- Nested field access

**DDL:**
```sql
CREATE TABLE `ecommerce-project.customers.profiles` (
  customer_id STRING NOT NULL,
  email STRING NOT NULL,
  first_name STRING,
  last_name STRING,
  date_of_birth DATE,
  gender STRING,
  phone STRING,
  registration_date TIMESTAMP NOT NULL,
  last_login_timestamp TIMESTAMP,
  customer_tier STRING,
  lifetime_value NUMERIC(15,2),
  total_orders INTEGER DEFAULT 0,
  marketing_consent BOOLEAN DEFAULT FALSE,
  address STRUCT<
    street STRING,
    city STRING,
    state STRING,
    zip_code STRING,
    country STRING
  >
)
PARTITION BY DATE(registration_date)
CLUSTER BY customer_tier, DATE(registration_date);
```

### 3. Products Table (inventory.products) 
**BigQuery Features to Test:**
- Partitioning by DATE(created_at)
- Clustering by category, brand
- Complex STRUCT with nested NUMERIC types
- Multiple precision NUMERIC fields

**DDL:**
```sql
CREATE TABLE `ecommerce-project.inventory.products` (
  product_id STRING NOT NULL,
  sku STRING NOT NULL,
  product_name STRING NOT NULL,
  category STRING NOT NULL,
  subcategory STRING,
  brand STRING,
  cost_price NUMERIC(10,2) NOT NULL,
  retail_price NUMERIC(10,2) NOT NULL,
  current_stock INTEGER NOT NULL,
  reorder_level INTEGER DEFAULT 10,
  weight_kg NUMERIC(8,3),
  dimensions STRUCT<
    length_cm NUMERIC(6,2),
    width_cm NUMERIC(6,2), 
    height_cm NUMERIC(6,2)
  >,
  product_status STRING NOT NULL,
  launch_date DATE,
  last_restocked_date DATE
)
PARTITION BY DATE(created_at)
CLUSTER BY category, brand;
```

## Test Queries to Validate DDL Training

### Sales Analysis Queries
1. **"Show me total sales revenue for this month"**
   - Expected: Uses EXTRACT(MONTH FROM order_date), SUM(total_amount)
   - Should reference `ecommerce-project.sales.orders`
   - May use partitioning optimization

2. **"Which customers spent the most money last quarter?"**
   - Expected: JOINs orders and customers tables
   - Uses EXTRACT(QUARTER FROM order_date)
   - Groups by customer info

3. **"Show me sales by shipping state"**
   - Expected: Accesses STRUCT field shipping_address.state
   - Uses proper STRUCT syntax for BigQuery

### Customer Analysis Queries  
4. **"Which customers have the highest lifetime value?"**
   - Expected: Uses customers.profiles table
   - Orders by lifetime_value DESC
   - May cluster optimization

5. **"Show me new customer registrations this month"**
   - Expected: Uses EXTRACT(MONTH FROM registration_date)
   - Filters on current month

### Inventory Analysis Queries
6. **"What products are low in stock and need reordering?"**
   - Expected: WHERE current_stock <= reorder_level
   - Uses inventory.products table
   - May use clustering on category

7. **"Show me products by weight category"**
   - Expected: CASE WHEN weight_kg logic
   - Uses NUMERIC field weight_kg

## Expected Improvements After DDL Training

### Before DDL Training (Current State)
- Confidence scores: ~0.5
- Generic table names (sales_table, inventory)
- Basic SQL without BigQuery optimizations
- No STRUCT field access
- Simple WHERE clauses

### After DDL Training (Expected)
- **Higher confidence scores** (0.7-0.9)
- **Proper fully qualified names** (`project.dataset.table`)
- **BigQuery-specific functions** (EXTRACT, STRUCT access)
- **Partition-aware queries** for performance
- **Cluster-optimized WHERE clauses**
- **Proper data type usage** (NUMERIC precision)

## Validation Criteria

✅ **DDL Training Success:**
- All 3 table DDLs stored without errors
- Training metadata includes BigQuery features
- Multi-tenant isolation maintained

✅ **SQL Generation Improvement:**
- Confidence scores increase from 0.5 to 0.7+
- Generated SQL uses fully qualified table names
- BigQuery-specific functions appear in queries
- STRUCT field access works correctly

✅ **BigQuery Feature Detection:**
- EXTRACT functions for date operations
- Proper STRUCT syntax (table.field.subfield)
- NUMERIC precision preserved
- Partitioning hints in complex queries

## Manual Test Steps

1. **Use vanna_train tool** to add each DDL with tenant_id="zadley"
2. **Use vanna_ask tool** to test each query
3. **Compare before/after** confidence scores and SQL quality
4. **Verify BigQuery features** in generated SQL
5. **Check query_history** for improved analytics

This plan will demonstrate that the Vanna MCP Server can effectively extract and utilize BigQuery-specific metadata to generate higher-quality, more optimized SQL queries.