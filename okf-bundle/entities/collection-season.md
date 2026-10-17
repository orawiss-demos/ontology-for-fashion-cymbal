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
title: Collection Season
description: Seasonal collection lifecycle stages driving buying, pricing, and markdown timing
resource: analytics.products.collection_season
tags: [season, collection, lifecycle, buying]
generated:
  by: data-team@fashion-cymbal.example
  at: 2026-10-01T10:00:00Z
status: active
stale_after: 2027-04-01T00:00:00Z
---

## Definition
The season a product was bought for, combined with its current lifecycle
stage. Every product is assigned to a `collection_season` at receipt
(e.g., "FW26" for Fall/Winter 2026). The lifecycle stage determines
pricing and markdown rules.

## Season Codes
| Code  | Season              | Receipt Window         |
|-------|---------------------|------------------------|
| SS26  | Spring/Summer 2026  | Jan 2026 – Mar 2026   |
| FW26  | Fall/Winter 2026    | Jul 2026 – Sep 2026   |
| SS27  | Spring/Summer 2027  | Jan 2027 – Mar 2027   |

## Lifecycle Stages
| Stage        | Description                              | Typical Duration |
|--------------|------------------------------------------|------------------|
| Pre-Season   | Ordered, not yet in stores               | 2-3 months       |
| In-Season    | Full-price selling period                | 8-12 weeks       |
| Markdown     | Price reductions applied                 | 4-8 weeks        |
| End-of-Season| Final clearance (> 50% off)             | 2-4 weeks        |
| Outlet       | Transferred to outlet channel            | Ongoing          |

## Season Calendar (Central European market)
| Season | In-Season Start | First Markdown | End-of-Season | Outlet Transfer |
|--------|-----------------|----------------|---------------|-----------------|
| SS     | February        | June           | July          | August          |
| FW     | August          | December       | January       | February        |

## Grain
- `collection_season` is set at product receipt and never changes
- Lifecycle stage is derived from dates, not stored — compute it from the calendar above
- A product's lifecycle stage drives its margin bucket: see [[gross-margin]]

## Related
- [[sell-through-rate]] — measured per collection season
- [[markdown-cadence]] — timing of price reductions within the lifecycle
- [[outlet-vs-fullprice]] — outlet transfer marks end of full-price lifecycle
