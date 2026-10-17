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
title: Return Window Policy
description: Channel-specific return eligibility periods and exclusion logic for return rate calculation
tags: [returns, policy, channel-specific]
generated:
  by: data-team@fashion-cymbal.example
  at: 2026-10-01T10:00:00Z
verified:
  - by: head-of-operations@fashion-cymbal.example
    at: 2026-10-02T14:00:00Z
status: active
stale_after: 2027-04-01T00:00:00Z
---

## Definition
Rules governing which returns count toward [[return-rate]] calculation
and how return windows differ by [[sales-channel]].

## Return Windows by Channel
| Channel      | Return Window | Notes                                  |
|--------------|---------------|----------------------------------------|
| Online       | 30 days       | From delivery date, not order date     |
| Store        | 14 days       | From purchase date, receipt required   |
| Outlet       | 14 days       | Final sale items excluded entirely     |
| Marketplace  | Per platform  | Modavia: 100 days; Trendora: 30 days |
| Click&Collect| 30 days       | Follows online policy                 |

## Exclusion Rules for Return Rate
When calculating [[return-rate]], exclude the following:

```sql
-- Returns that should NOT count toward return rate
WHERE NOT (
  -- Warranty/defect returns (not customer choice)
  return_reason = 'defect'
  -- Returns outside the eligible window
  OR CASE
    WHEN sales_channel IN ('ONLINE', 'CNC') THEN
      DATE_DIFF(return_date, delivery_date, DAY) > 30
    WHEN sales_channel = 'STORE' THEN
      DATE_DIFF(return_date, order_date, DAY) > 14
    WHEN sales_channel = 'OUTLET' AND is_final_sale = TRUE THEN
      TRUE  -- final sale = no returns
    WHEN sales_channel = 'MARKETPLACE' AND marketplace_name = 'Modavia' THEN
      DATE_DIFF(return_date, delivery_date, DAY) > 100
    ELSE
      DATE_DIFF(return_date, delivery_date, DAY) > 30
  END
)
```

## Holiday Season Exception
During November 15 – January 15 (holiday season), all online purchases
get an extended 60-day return window. This is a promotional policy,
not a permanent change. When computing return rate for Q4, use:
```sql
CASE
  WHEN order_date BETWEEN DATE('2026-11-15') AND DATE('2027-01-15')
    AND sales_channel IN ('ONLINE', 'CNC')
  THEN DATE_DIFF(return_date, delivery_date, DAY) <= 60
  ELSE DATE_DIFF(return_date, delivery_date, DAY) <= 30
END
```

## Related
- [[return-rate]] — this policy determines what counts as a valid return
- [[sales-channel]] — channel determines which window applies
- [[outlet-vs-fullprice]] — outlet final-sale items are never returnable
