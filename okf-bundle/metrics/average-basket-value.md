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
title: Average Basket Value
description: Mean net order value per transaction, after discounts and before returns
resource: analytics.orders.avg_basket_value
tags: [revenue, aov, basket, core-metric]
generated:
  by: data-team@fashion-cymbal.example
  at: 2026-10-01T10:00:00Z
sources:
  - id: orders
    resource: analytics.orders
    title: Orders Fact Table
    usage_count: 510
    last_modified: 2026-09-30T06:00:00Z
verified:
  - by: head-of-analytics@fashion-cymbal.example
    at: 2026-10-01T12:00:00Z
status: active
stale_after: 2027-04-01T00:00:00Z
---

## Definition
Mean net order value per completed transaction, calculated after applying
discounts and vouchers but BEFORE returns are processed. This represents
what the customer paid at checkout, not what was ultimately retained.

## Calculation
```sql
SELECT
  sales_channel,
  product_category,
  AVG(net_order_value) AS avg_basket_value
FROM `analytics.orders`
WHERE order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
  AND order_status NOT IN ('cancelled', 'test', 'fraud')
  AND is_internal_order = FALSE
  AND is_employee_purchase = FALSE
  AND net_order_value > 0
GROUP BY sales_channel, product_category
```

## Exclusions
- Cancelled, test, and fraud-flagged orders
- Internal orders and employee purchases
- Zero-value orders (gift card redemptions counted separately)

## Time Window
- Default: trailing 30 days
- For seasonal comparison: use same calendar weeks year-over-year
- During sale periods ([[markdown-cadence]]), ABV typically drops 15-25% — this is expected, not anomalous

## Channel Benchmarks (EUR)
- Online full-price: EUR 95-120
- Store: EUR 75-95
- Outlet: EUR 45-65
- Marketplace: EUR 60-80

## Related Metrics
- [[return-rate]] — high ABV + high return rate = bracketing behavior (ordering multiple sizes)
- [[gross-margin]] — ABV alone does not indicate profitability
