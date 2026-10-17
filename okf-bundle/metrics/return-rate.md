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
title: Return Rate
description: Ratio of returned items to total items sold, measured by units not revenue
resource: analytics.order_items.return_rate
tags: [returns, profitability, core-metric]
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
  - by: head-of-analytics@fashion-cymbal.example
    at: 2026-10-01T12:00:00Z
status: active
stale_after: 2027-04-01T00:00:00Z
---

## Definition
The ratio of units returned to total units sold, calculated over a configurable
trailing window. Measured by unit count, NOT by revenue — a returned EUR 200
jacket counts the same as a returned EUR 20 t-shirt in this metric.

## Calculation
```sql
SELECT
  product_category,
  brand_name,
  sales_channel,
  COUNT(CASE WHEN return_status = 'returned' THEN 1 END)
    / NULLIF(COUNT(item_id), 0) AS return_rate
FROM `analytics.order_items`
WHERE order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
  AND order_status NOT IN ('cancelled', 'test')
  AND is_internal_order = FALSE
  AND is_employee_purchase = FALSE
GROUP BY product_category, brand_name, sales_channel
```

## Exclusions
- Orders with status 'cancelled' or 'test' — never shipped, not a return
- Internal orders (`is_internal_order = TRUE`) — warehouse transfers, photo samples
- Employee purchases (`is_employee_purchase = TRUE`) — staff discount orders with different return behavior

## Time Window
- Default: trailing 90 days (fashion return cycles are longer than travel)
- Exception: during end-of-season sale periods, use trailing 120 days
  because markdown purchases have delayed return patterns
- Sale periods: see [[markdown-cadence]]
- Return eligibility window: see [[return-window-policy]]

## Thresholds
- Healthy: < 25% (industry benchmark for fashion e-commerce)
- Warning: 25-35%
- Critical: > 35% — triggers category review

## Related Metrics
- [[sell-through-rate]] — high sell-through with high returns signals sizing issues
- [[gross-margin]] — returns directly erode margin
- [[average-basket-value]] — higher baskets often correlate with higher return rates (bracketing behavior)
