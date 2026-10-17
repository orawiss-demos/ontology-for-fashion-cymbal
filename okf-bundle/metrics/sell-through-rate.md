---
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
type: Metric
title: Sell-Through Rate
description: Ratio of units sold to total units received into inventory, by collection season
resource: analytics.inventory_movement.sell_through_rate
tags: [inventory, efficiency, buying, core-metric]
generated:
  by: data-team@fashion-cymbal.example
  at: 2026-10-01T10:00:00Z
sources:
  - id: inventory_movement
    resource: analytics.inventory_movement
    title: Inventory Movement Fact Table
    usage_count: 320
    last_modified: 2026-09-25T14:00:00Z
verified:
  - by: head-of-buying@fashion-cymbal.example
    at: 2026-10-02T09:00:00Z
status: active
stale_after: 2027-04-01T00:00:00Z
---

## Definition
The ratio of units sold to total units received into inventory for a given
product or category, within a specific collection season. This is the primary
metric the buying team uses to evaluate assortment decisions.

## Calculation
```sql
SELECT
  collection_season,
  product_category,
  brand_name,
  SUM(units_sold) / NULLIF(SUM(units_received), 0) AS sell_through_rate
FROM `analytics.inventory_movement`
WHERE receipt_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 180 DAY)
  AND movement_type IN ('sale', 'receipt')
  AND warehouse_code != 'OUTLET_WH'
  AND is_sample = FALSE
GROUP BY collection_season, product_category, brand_name
```

## Exclusions
- Outlet warehouse transactions (`warehouse_code = 'OUTLET_WH'`) — outlet is measured separately; see [[outlet-vs-fullprice]]
- Sample inventory (`is_sample = TRUE`) — photo shoots, showroom samples
- Inter-warehouse transfers are not sales

## Time Window
- Default: trailing 180 days (one full season cycle)
- For in-season tracking: filter by `collection_season` instead of date range
- Season mapping: see [[collection-season]]

## Thresholds
- Target: > 65% at end of season (before outlet transfer)
- Warning: < 50% at mid-season — triggers markdown consideration
- Critical: < 40% — triggers early markdown; see [[markdown-cadence]]

## Related Metrics
- [[return-rate]] — net sell-through adjusts for returns
- [[gross-margin]] — sell-through drives whether margin is captured at full price or markdown
