#!/usr/bin/env python3
# DISCLAIMER — DEMONSTRATION CODE, NOT FOR PRODUCTION USE
#
# This project is a demonstration example, provided solely to illustrate
# concepts and for learning purposes. It is not an official Google product
# and is not supported by Google.
#
# The code is provided "as is", without warranty of any kind, express or
# implied. It has not been hardened, security-reviewed, or tested for
# production workloads, and it must not be relied upon to run production
# systems or to process business-critical data.
#
# The author accepts no responsibility or liability for any failure, defect,
# data loss, cost, or other damage arising from the use, adaptation, or
# deployment of this example in any environment, including customer
# environments. Anyone reusing any part of it does so at their own risk and
# should review, test, and adapt it thoroughly first.

"""
Step 1: Create sample BigQuery tables with fashion retail demo data.

Tables:
  - order_items  — fact table: one row per item in an order
  - orders       — fact table: one row per order
  - products     — dimension: product catalog
  - inventory_movement — fact: units received and sold

Run: python -I setup/01_create_sample_bq.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.cloud import bigquery
from config import GCP_PROJECT, GCP_REGION, BQ_DATASET

client = bigquery.Client(project=GCP_PROJECT)

# Create dataset (idempotent)
dataset_ref = bigquery.DatasetReference(GCP_PROJECT, BQ_DATASET)
dataset = bigquery.Dataset(dataset_ref)
dataset.location = GCP_REGION
dataset = client.create_dataset(dataset, exists_ok=True)
print(f"Dataset {BQ_DATASET} ready in {dataset.location}")


# --- Products dimension ----------------------------------------------------
PRODUCTS_DDL = f"""
CREATE OR REPLACE TABLE `{GCP_PROJECT}.{BQ_DATASET}.products` AS
SELECT * FROM UNNEST([
  STRUCT('SKU001' AS sku, 'Wool Blend Coat' AS product_name, 'Women' AS department, 'Outerwear' AS product_category, 'Coats' AS subcategory, 'Aurelio Vance' AS brand_name, 'Premium' AS brand_tier, 'FW26' AS collection_season, 249.00 AS original_price, 125.00 AS cogs, FALSE AS is_outlet_exclusive, FALSE AS is_sample),
  STRUCT('SKU002', 'Slim Fit Suit', 'Men', 'Suits', 'Business', 'Aurelio Vance', 'Premium', 'FW26', 399.00, 180.00, FALSE, FALSE),
  STRUCT('SKU003', 'Casual T-Shirt', 'Women', 'Tops', 'T-Shirts', 'Kestrelline', 'Core', 'SS26', 29.90, 10.00, FALSE, FALSE),
  STRUCT('SKU004', 'Summer Dress', 'Women', 'Dresses', 'Casual', 'Saltmere', 'Core', 'SS26', 79.90, 28.00, FALSE, FALSE),
  STRUCT('SKU005', 'Leather Sneakers', 'Accessories', 'Shoes', 'Sneakers', 'Hartwell & Rowe', 'Premium', 'FW26', 129.00, 48.00, FALSE, FALSE),
  STRUCT('SKU006', 'Basic Polo', 'Men', 'Shirts', 'Polo', 'Plainora', 'Entry', 'SS26', 19.90, 6.00, FALSE, FALSE),
  STRUCT('SKU007', 'Crossbody Bag', 'Accessories', 'Bags', 'Handbags', 'Hartwell & Rowe', 'Premium', 'FW26', 89.00, 32.00, FALSE, FALSE),
  STRUCT('SKU008', 'Knit Sweater', 'Women', 'Tops', 'Knitwear', 'Velvi', 'Entry', 'FW26', 39.90, 13.00, FALSE, FALSE),
  STRUCT('SKU009', 'Outlet Blazer', 'Men', 'Outerwear', 'Blazers', 'Kestrelline', 'Core', 'SS25', 59.90, 22.00, TRUE, FALSE),
  STRUCT('SKU010', 'Evening Dress', 'Women', 'Dresses', 'Evening', 'Aurelio Vance', 'Premium', 'FW26', 349.00, 140.00, FALSE, FALSE)
])
"""

# --- Orders fact ------------------------------------------------------------
ORDERS_DDL = f"""
CREATE OR REPLACE TABLE `{GCP_PROJECT}.{BQ_DATASET}.orders` AS
WITH raw AS (
  SELECT * FROM UNNEST(GENERATE_ARRAY(1, 200)) AS order_num
),
generated AS (
  SELECT
    CONCAT('ORD-', LPAD(CAST(order_num AS STRING), 5, '0')) AS order_id,
    DATE_SUB(CURRENT_DATE(), INTERVAL CAST(FLOOR(RAND() * 120) AS INT64) DAY) AS order_date,
    -- Channel distribution: 45% online, 30% store, 10% outlet, 10% marketplace, 5% CNC
    CASE
      WHEN MOD(order_num, 20) < 9  THEN 'ONLINE'
      WHEN MOD(order_num, 20) < 15 THEN 'STORE'
      WHEN MOD(order_num, 20) < 17 THEN 'OUTLET'
      WHEN MOD(order_num, 20) < 19 THEN 'MARKETPLACE'
      ELSE 'CNC'
    END AS sales_channel,
    -- Status: 85% completed, 8% cancelled, 5% test, 2% fraud
    CASE
      WHEN MOD(order_num, 100) < 85 THEN 'completed'
      WHEN MOD(order_num, 100) < 93 THEN 'cancelled'
      WHEN MOD(order_num, 100) < 98 THEN 'test'
      ELSE 'fraud'
    END AS order_status,
    ROUND(50 + RAND() * 300, 2) AS net_order_value,
    MOD(order_num, 50) = 0 AS is_internal_order,
    MOD(order_num, 40) = 0 AS is_employee_purchase,
    CASE WHEN MOD(order_num, 20) >= 17 THEN 'Modavia' ELSE NULL END AS marketplace_name
  FROM raw
)
SELECT * FROM generated
"""

# --- Order Items fact -------------------------------------------------------
ORDER_ITEMS_DDL = f"""
CREATE OR REPLACE TABLE `{GCP_PROJECT}.{BQ_DATASET}.order_items` AS
WITH orders AS (SELECT * FROM `{GCP_PROJECT}.{BQ_DATASET}.orders`),
     products AS (SELECT * FROM `{GCP_PROJECT}.{BQ_DATASET}.products`),
     item_nums AS (SELECT * FROM UNNEST(GENERATE_ARRAY(1, 3)) AS item_num),
     combos AS (
       SELECT
         o.order_id, o.order_date, o.sales_channel, o.order_status,
         o.is_internal_order, o.is_employee_purchase,
         p.sku, p.product_name, p.department, p.product_category,
         p.brand_name, p.brand_tier, p.collection_season,
         p.original_price, p.cogs, p.is_outlet_exclusive,
         item_num,
         -- Assign products semi-randomly to orders
         MOD(ABS(FARM_FINGERPRINT(CONCAT(o.order_id, CAST(item_num AS STRING)))), 10) AS prod_idx
       FROM orders o
       CROSS JOIN item_nums
       CROSS JOIN (SELECT *, ROW_NUMBER() OVER (ORDER BY sku) - 1 AS idx FROM products) p
       WHERE p.idx = MOD(ABS(FARM_FINGERPRINT(CONCAT(o.order_id, CAST(item_num AS STRING)))), 10)
         AND item_num <= 1 + MOD(ABS(FARM_FINGERPRINT(o.order_id)), 3)
     )
SELECT
  CONCAT(order_id, '-', CAST(item_num AS STRING)) AS item_id,
  order_id, order_date, sales_channel, order_status,
  is_internal_order, is_employee_purchase,
  sku, product_name, department, product_category,
  brand_name, brand_tier, collection_season,
  -- Apply discounts for outlet/markdown
  CASE
    WHEN sales_channel = 'OUTLET' OR is_outlet_exclusive THEN ROUND(original_price * 0.4, 2)
    WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(order_id, sku))), 5) = 0 THEN ROUND(original_price * 0.7, 2)
    ELSE original_price
  END AS net_selling_price,
  cogs,
  -- Return status: 20% returned, 3% defect
  CASE
    WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(order_id, sku, 'ret'))), 100) < 20 THEN 'returned'
    WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(order_id, sku, 'ret'))), 100) < 23 THEN 'defect'
    ELSE 'kept'
  END AS return_status,
  DATE_ADD(order_date, INTERVAL 2 DAY) AS delivery_date,
  CASE
    WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(order_id, sku, 'ret'))), 100) < 23
    THEN DATE_ADD(order_date, INTERVAL (5 + MOD(ABS(FARM_FINGERPRINT(CONCAT(order_id, sku, 'rd'))), 25)) DAY)
    ELSE NULL
  END AS return_date,
  CASE
    WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(order_id, sku, 'ret'))), 100) < 20 THEN 'wrong_size'
    WHEN MOD(ABS(FARM_FINGERPRINT(CONCAT(order_id, sku, 'ret'))), 100) < 23 THEN 'defect'
    ELSE NULL
  END AS return_reason,
  FALSE AS is_final_sale,
  CASE
    WHEN sales_channel = 'OUTLET' THEN 'OUTLET_WH'
    ELSE 'MAIN_WH'
  END AS warehouse_code,
  '' AS product_lifecycle_stage
FROM combos
"""

# --- Inventory Movement fact ------------------------------------------------
INVENTORY_DDL = f"""
CREATE OR REPLACE TABLE `{GCP_PROJECT}.{BQ_DATASET}.inventory_movement` AS
WITH products AS (SELECT * FROM `{GCP_PROJECT}.{BQ_DATASET}.products`),
     months AS (SELECT * FROM UNNEST(GENERATE_ARRAY(1, 6)) AS month_offset)
SELECT
  CONCAT(p.sku, '-', CAST(m.month_offset AS STRING), '-R') AS movement_id,
  p.sku, p.product_name, p.product_category, p.brand_name,
  p.collection_season,
  'receipt' AS movement_type,
  DATE_SUB(CURRENT_DATE(), INTERVAL (m.month_offset * 30) DAY) AS receipt_date,
  50 + MOD(ABS(FARM_FINGERPRINT(CONCAT(p.sku, CAST(m.month_offset AS STRING)))), 150) AS units_received,
  CAST(ROUND(
    (30 + MOD(ABS(FARM_FINGERPRINT(CONCAT(p.sku, CAST(m.month_offset AS STRING), 'sold'))), 120))
    * (0.5 + RAND() * 0.4)
  , 0) AS INT64) AS units_sold,
  CASE WHEN p.is_outlet_exclusive THEN 'OUTLET_WH' ELSE 'MAIN_WH' END AS warehouse_code,
  p.is_sample
FROM products p
CROSS JOIN months m
"""

if __name__ == "__main__":
    for name, ddl in [
        ("products", PRODUCTS_DDL),
        ("orders", ORDERS_DDL),
        ("order_items", ORDER_ITEMS_DDL),
        ("inventory_movement", INVENTORY_DDL),
    ]:
        print(f"Creating {name}...", end=" ", flush=True)
        client.query(ddl).result()
        count = client.query(
            f"SELECT COUNT(*) AS n FROM `{GCP_PROJECT}.{BQ_DATASET}.{name}`"
        ).result()
        for row in count:
            print(f"{row.n} rows")

    print("\nAll tables ready.")
