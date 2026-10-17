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
title: Markdown Cadence
description: Seasonal price reduction schedule, thresholds, and sell-through triggers
tags: [pricing, markdown, season, buying]
generated:
  by: data-team@fashion-cymbal.example
  at: 2026-10-01T10:00:00Z
verified:
  - by: head-of-buying@fashion-cymbal.example
    at: 2026-10-02T09:00:00Z
status: active
stale_after: 2027-04-01T00:00:00Z
---

## Definition
The schedule and rules governing when and how much prices are reduced
during a collection season's lifecycle. Markdown decisions are the
single largest lever on [[gross-margin]].

## Standard Markdown Schedule
| Stage          | Timing (SS)     | Timing (FW)       | Discount Range |
|----------------|-----------------|---------------------|----------------|
| First Markdown | Week 1 of June  | Week 1 of December | 20-30% off     |
| Mid-Season Sale| Week 3 of June  | Week 3 of December | 30-40% off     |
| End-of-Season  | Week 2 of July  | Week 2 of January  | 40-60% off     |
| Final Clearance| Week 4 of July  | Week 4 of January  | 60-70% off     |

## Sell-Through Triggers
Markdown can be accelerated (applied earlier than schedule) when
[[sell-through-rate]] falls below thresholds:

```sql
-- Check if early markdown is triggered
SELECT
  product_category,
  brand_name,
  sell_through_rate,
  CASE
    WHEN sell_through_rate < 0.30 AND weeks_in_season >= 4
      THEN 'IMMEDIATE_MARKDOWN_30'
    WHEN sell_through_rate < 0.40 AND weeks_in_season >= 6
      THEN 'ACCELERATED_MARKDOWN_20'
    WHEN sell_through_rate < 0.50 AND weeks_in_season >= 8
      THEN 'SCHEDULED_MARKDOWN'
    ELSE 'HOLD_FULL_PRICE'
  END AS markdown_action
FROM sell_through_by_category
```

## Rules
1. Private label brands ([[brand]] tier = 'Private') can be marked down
   at any time — no schedule constraint
2. Premium brands require buying team approval for any markdown > 30%
3. Markdown is always applied category-wide, never per-SKU
   (exception: end-of-season clearance can be per-SKU)
4. Marketplace channels follow platform-specific sale events,
   not the internal calendar

## Markdown vs. Outlet Transfer
A product that has been through Final Clearance and still has remaining
stock is transferred to outlet — see [[outlet-vs-fullprice]].
Outlet pricing is a separate calculation, not a further markdown.

## Related
- [[sell-through-rate]] — triggers for accelerated markdown
- [[gross-margin]] — each markdown step erodes margin by the discount percentage
- [[collection-season]] — markdown timing is anchored to the season calendar
- [[outlet-vs-fullprice]] — what happens after markdown exhaustion
