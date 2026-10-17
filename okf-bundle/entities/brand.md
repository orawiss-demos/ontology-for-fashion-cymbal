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
title: Brand
description: Brand identity with tier classification driving pricing and margin targets
resource: analytics.products.brand_name
tags: [brand, pricing, assortment]
generated:
  by: data-team@fashion-cymbal.example
  at: 2026-10-01T10:00:00Z
status: active
stale_after: 2027-04-01T00:00:00Z
---

## Definition
The brand label on a product, combined with a `brand_tier` classification
that drives pricing strategy, margin expectations, and markdown behavior.

The `brand_name` field is the display name. The `brand_tier` field is
the strategic classification used for reporting aggregation.

## Brand Tiers
| Tier       | Description                          | Margin Target | Examples (illustrative) |
|------------|--------------------------------------|---------------|-------------------------|
| Premium    | Designer and luxury brands           | > 60%         | Aurelio Vance, Hartwell & Rowe |
| Core       | Mid-market, volume-driving brands    | 50-60%        | Kestrelline, Saltmere        |
| Entry      | Price-point and value brands         | 40-50%        | Plainora, Velvi         |
| Private    | Own-label / exclusive brands         | > 65%         | (Fashion Cymbal exclusive labels)  |

## Grain
- Brand tier is assigned by the buying team and stored in `products.brand_tier`
- One brand can appear across multiple departments and categories
- Brand tier can change between seasons but not mid-season

## Data Quality Notes
- Brand names are normalized (e.g., "AURELIO VANCE" → "Aurelio Vance") — always use `brand_name`, not raw supplier labels
- ~50 active brands per season; tier assignment reviewed annually
- Private label brands have a different COGS structure — comparison across tiers requires caution

## Related
- [[product-category]] — brand + category = assortment cell (the unit of buying decisions)
- [[gross-margin]] — margin targets are set per brand tier
- [[sell-through-rate]] — sell-through benchmarks differ by tier
