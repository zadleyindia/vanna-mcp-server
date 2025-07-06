#!/usr/bin/env python3
"""
Test script for BigQuery DDL training and SQL generation
"""
import asyncio
import sys
from pathlib import Path

# Add project to path
sys.path.append(str(Path(__file__).parent))

from src.tools.vanna_train import vanna_train
from src.tools.vanna_ask import vanna_ask

async def test_bigquery_ddl():
    """Test BigQuery DDL training and improved SQL generation"""
    
    print("🧪 Testing BigQuery DDL Training and SQL Generation")
    print("=" * 60)
    
    # Test 1: Train with Orders table DDL (BigQuery-specific features)
    print("\n1. Training with BigQuery Orders Table DDL...")
    
    orders_ddl = """CREATE TABLE `ecommerce-project.sales.orders` (
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
  order_status STRING NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY DATE(order_date)
CLUSTER BY customer_id, product_id
OPTIONS(
  description="E-commerce sales orders with customer and product details",
  labels=[("team", "sales"), ("env", "production")]
);"""
    
    try:
        result1 = await vanna_train(
            training_type="ddl",
            content=orders_ddl,
            tenant_id="zadley",
            metadata={
                "table_name": "orders",
                "dataset": "sales",
                "project": "ecommerce-project",
                "partition_field": "order_date",
                "cluster_fields": ["customer_id", "product_id"]
            }
        )
        print(f"   ✅ Orders DDL training: {result1.get('status', 'success')}")
    except Exception as e:
        print(f"   ❌ Orders DDL training failed: {e}")
        return False
    
    # Test 2: Train with Customers table DDL
    print("\n2. Training with BigQuery Customers Table DDL...")
    
    customers_ddl = """CREATE TABLE `ecommerce-project.customers.profiles` (
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
  preferred_language STRING DEFAULT 'en',
  address STRUCT<
    street STRING,
    city STRING,
    state STRING,
    zip_code STRING,
    country STRING
  >,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY DATE(registration_date)
CLUSTER BY customer_tier, DATE(registration_date)
OPTIONS(
  description="Customer profile data with demographics and preferences",
  labels=[("team", "marketing"), ("pii", "true"), ("env", "production")]
);"""
    
    try:
        result2 = await vanna_train(
            training_type="ddl",
            content=customers_ddl,
            tenant_id="zadley",
            metadata={
                "table_name": "profiles",
                "dataset": "customers", 
                "project": "ecommerce-project",
                "partition_field": "registration_date",
                "cluster_fields": ["customer_tier", "registration_date"]
            }
        )
        print(f"   ✅ Customers DDL training: {result2.get('status', 'success')}")
    except Exception as e:
        print(f"   ❌ Customers DDL training failed: {e}")
        return False
    
    # Test 3: Train with Products table DDL  
    print("\n3. Training with BigQuery Products Table DDL...")
    
    products_ddl = """CREATE TABLE `ecommerce-project.inventory.products` (
  product_id STRING NOT NULL,
  sku STRING NOT NULL,
  product_name STRING NOT NULL,
  category STRING NOT NULL,
  subcategory STRING,
  brand STRING,
  supplier_id STRING,
  cost_price NUMERIC(10,2) NOT NULL,
  retail_price NUMERIC(10,2) NOT NULL,
  current_stock INTEGER NOT NULL,
  reorder_level INTEGER DEFAULT 10,
  max_stock_level INTEGER,
  weight_kg NUMERIC(8,3),
  dimensions STRUCT<
    length_cm NUMERIC(6,2),
    width_cm NUMERIC(6,2),
    height_cm NUMERIC(6,2)
  >,
  product_status STRING NOT NULL,
  launch_date DATE,
  last_restocked_date DATE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY DATE(created_at)
CLUSTER BY category, brand
OPTIONS(
  description="Product inventory with stock levels and product details",
  labels=[("team", "inventory"), ("env", "production")]
);"""
    
    try:
        result3 = await vanna_train(
            training_type="ddl",
            content=products_ddl,
            tenant_id="zadley",
            metadata={
                "table_name": "products",
                "dataset": "inventory",
                "project": "ecommerce-project", 
                "partition_field": "created_at",
                "cluster_fields": ["category", "brand"]
            }
        )
        print(f"   ✅ Products DDL training: {result3.get('status', 'success')}")
    except Exception as e:
        print(f"   ❌ Products DDL training failed: {e}")
        return False
    
    # Test 4: Test improved SQL generation
    print("\n4. Testing SQL generation after DDL training...")
    
    test_queries = [
        "Show me total sales revenue for this month",
        "Which customers have the highest lifetime value?", 
        "What products are low in stock and need reordering?"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n   Query {i}: {query}")
        try:
            result = await vanna_ask(
                query=query,
                tenant_id="zadley",
                include_confidence=True,
                include_explanation=True
            )
            
            if result.get('sql'):
                print(f"   ✅ Generated SQL (confidence: {result.get('confidence', 0):.2f})")
                print(f"   📝 SQL: {result['sql'][:100]}...")
                print(f"   📊 Tables used: {result.get('tables_referenced', [])}")
                print(f"   🎯 BigQuery features detected: {_check_bigquery_features(result['sql'])}")
            else:
                print(f"   ❌ No SQL generated: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"   ❌ Query failed: {e}")
    
    print(f"\n🎉 BigQuery DDL testing completed!")
    return True

def _check_bigquery_features(sql):
    """Check for BigQuery-specific features in generated SQL"""
    features = []
    sql_upper = sql.upper()
    
    if "EXTRACT(" in sql_upper:
        features.append("EXTRACT function")
    if "STRUCT<" in sql_upper or "STRUCT(" in sql_upper:
        features.append("STRUCT types")  
    if "`" in sql and "." in sql:
        features.append("Fully qualified names")
    if "NUMERIC(" in sql_upper:
        features.append("NUMERIC types")
    if "PARTITION BY" in sql_upper:
        features.append("Partitioning")
    if "CLUSTER BY" in sql_upper:
        features.append("Clustering")
        
    return features if features else ["Standard SQL"]

if __name__ == "__main__":
    asyncio.run(test_bigquery_ddl())