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
title: Gross Margin
description: Revenue minus cost of goods sold as a percentage of revenue, after returns
resource: analytics.order_items.gross_margin_pct
tags: [profitability, margin, finance, core-metric]
generated:
  by: data-team@fashion-cymbal.example
  at: 2026-10-01T10:00:00Z
sources:
  - id: order_items
    resource: analytics.order_items
    title: Order Items Fact Table
    usage_count: 450
    last_modified: 2026-09-28T08:00:00Z
verified:
  - by: cfo-office@fashion-cymbal.example
    at: 2026-10-03T11:00:00Z
status: active
stale_after: 2027-04-01T00:00:00Z
---

## Definition
Revenue minus cost of goods sold (COGS), expressed as a percentage of revenue.
Calculated AFTER returns — a returned item removes both its revenue and COGS
from the calculation. This is gross margin, not contribution margin (does not
include fulfillment, marketing, or overhead costs).

## Calculation
```sql
SELECT
  product_category,
  brand_name,
  collection_season,
  SUM(CASE WHEN return_status != 'returned' THEN net_selling_price ELSE 0 END) AS net_revenue,
  SUM(CASE WHEN return_status != 'returned' THEN cogs ELSE 0 END) AS total_cogs,
  SAFE_DIVIDE(
    SUM(CASE WHEN return_status != 'returned' THEN net_selling_price - cogs ELSE 0 END),
    NULLIF(SUM(CASE WHEN return_status != 'returned' THEN net_selling_price ELSE 0 END), 0)
  ) AS gross_margin_pct
FROM `analytics.order_items`
WHERE order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
  AND order_status NOT IN ('cancelled', 'test', 'fraud')
  AND is_internal_order = FALSE
  AND is_employee_purchase = FALSE
GROUP BY product_category, brand_name, collection_season
```

## Exclusions
- Same as [[return-rate]]: cancelled/test/fraud, internal, employee
- Returned items are excluded from both revenue and COGS (net calculation)

## Time Window
- Default: trailing 90 days
- For buying decisions: calculate per collection season via [[collection-season]]
- COGS is frozen at receipt — no revaluation mid-season

## Thresholds
- Target: > 55% for full-price, > 35% for markdown, > 20% for outlet
- Warning: full-price margin < 50% — investigate pricing or COGS creep
- Classification: see [[outlet-vs-fullprice]] for which bucket applies

## Related Metrics
- [[sell-through-rate]] — high sell-through at full price = highest margin
- [[return-rate]] — returns destroy margin; a 30% return rate on 55% margin items cuts effective margin significantly
- [[average-basket-value]] — ABV * margin = absolute margin per order
