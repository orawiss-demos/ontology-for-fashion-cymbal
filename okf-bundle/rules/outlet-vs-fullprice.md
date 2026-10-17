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
type: Business Rule
title: Outlet vs Full-Price Classification
description: Rules for classifying transactions as outlet or full-price in analytics
tags: [outlet, full-price, classification, reporting]
generated:
  by: data-team@fashion-cymbal.example
  at: 2026-10-01T10:00:00Z
verified:
  - by: head-of-analytics@fashion-cymbal.example
    at: 2026-10-01T12:00:00Z
status: active
stale_after: 2027-04-01T00:00:00Z
---

## Definition
Rules for classifying a transaction as "outlet" or "full-price" in
all reporting and metric calculations. This distinction is critical
because outlet and full-price have fundamentally different margin
structures, and mixing them produces meaningless averages.

## Classification Logic
A transaction is classified as **outlet** when ANY of these conditions is true:

```sql
CASE
  WHEN sales_channel = 'OUTLET' THEN 'outlet'
  WHEN warehouse_code = 'OUTLET_WH' THEN 'outlet'
  WHEN product_lifecycle_stage = 'outlet' THEN 'outlet'
  WHEN is_outlet_exclusive = TRUE THEN 'outlet'
  ELSE 'fullprice'
END AS price_classification
```

## Important: Channel Alone Is Not Sufficient
A `sales_channel = 'ONLINE'` order can be outlet if the product was
sourced from `OUTLET_WH` or is an outlet-exclusive SKU. The classification
must check all four conditions, not just channel.

## Reporting Implications
| Metric                    | Full-Price | Outlet  | Mixed (DO NOT USE) |
|---------------------------|------------|---------|---------------------|
| [[gross-margin]] target   | > 55%      | > 20%   | Meaningless         |
| [[sell-through-rate]] target | > 65%   | > 80%   | Misleading          |
| [[return-rate]] benchmark | < 25%      | < 15%   | Distorted           |
| [[average-basket-value]]  | EUR 95-120 | EUR 45-65| Inflated/deflated  |

## SQL Filter Pattern
Always apply this filter in metric queries. When the user asks for
"full-price metrics" or "outlet metrics", use:

```sql
-- Full-price only
WHERE sales_channel != 'OUTLET'
  AND warehouse_code != 'OUTLET_WH'
  AND COALESCE(product_lifecycle_stage, '') != 'outlet'
  AND is_outlet_exclusive = FALSE

-- Outlet only
WHERE (
  sales_channel = 'OUTLET'
  OR warehouse_code = 'OUTLET_WH'
  OR product_lifecycle_stage = 'outlet'
  OR is_outlet_exclusive = TRUE
)
```

## Related
- [[sales-channel]] — OUTLET channel is one signal but not the only one
- [[gross-margin]] — margin targets differ by classification
- [[collection-season]] — outlet transfer marks end of full-price lifecycle
- [[markdown-cadence]] — markdown exhaustion triggers outlet transfer
