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
type: Entity
title: Sales Channel
description: Transaction channel classification — online, store, outlet, marketplace
resource: analytics.orders.sales_channel
tags: [channel, omnichannel, distribution]
generated:
  by: data-team@fashion-cymbal.example
  at: 2026-10-01T10:00:00Z
status: active
stale_after: 2027-04-01T00:00:00Z
---

## Definition
The channel through which a transaction was completed. Every order
carries exactly one `sales_channel` value. Cross-channel journeys
(browse online, buy in store) are attributed to the completing channel.

## Channel Values
| Channel      | Code        | Description                                    |
|--------------|-------------|------------------------------------------------|
| Online       | ONLINE      | fashion-cymbal.example / Fashion Cymbal online shop           |
| Store        | STORE       | Physical retail locations                      |
| Outlet       | OUTLET      | Factory outlet and off-price stores            |
| Marketplace  | MARKETPLACE | Third-party platforms (Modavia, Trendora)     |
| Click&Collect| CNC         | Ordered online, picked up in store             |

## Reporting Rules
- Click&Collect (`CNC`) counts as ONLINE for revenue attribution
  but as STORE for fulfillment cost allocation
- Marketplace orders have different return handling — see [[return-window-policy]]
- Outlet transactions are excluded from full-price metrics — see [[outlet-vs-fullprice]]

## Grain
- `sales_channel` is set at order level, not item level
- One order = one channel (no split-channel orders)
- Channel is immutable after order creation

## Data Quality Notes
- Store channel requires POS system ID mapping — ~0.5% unmapped transactions per month
- Marketplace data arrives with 24-48h delay vs real-time for online/store

## Related
- [[outlet-vs-fullprice]] — channel is part of but not sufficient for the full-price/outlet split
- [[return-window-policy]] — return windows differ by channel
- [[average-basket-value]] — ABV benchmarks are channel-specific
