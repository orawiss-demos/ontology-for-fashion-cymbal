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
title: Product Category
description: Three-level hierarchical product classification used across all analytics
resource: analytics.products.product_category
tags: [product, hierarchy, classification]
generated:
  by: data-team@fashion-cymbal.example
  at: 2026-10-01T10:00:00Z
status: active
stale_after: 2027-04-01T00:00:00Z
---

## Definition
A three-level hierarchy classifying every SKU in the assortment:
**Department > Category > Subcategory**.

The `product_category` field in analytics tables refers to the middle
level (Category). Use `department` for the top level and `subcategory`
for the leaf level.

## Hierarchy
| Department     | Category        | Example Subcategories              |
|----------------|-----------------|-------------------------------------|
| Women          | Dresses         | Casual, Evening, Knit              |
| Women          | Outerwear       | Coats, Jackets, Blazers            |
| Women          | Tops            | Blouses, T-Shirts, Knitwear        |
| Men            | Suits           | Business, Casual, Occasion         |
| Men            | Outerwear       | Coats, Jackets, Blazers            |
| Men            | Shirts          | Dress, Casual, Polo                |
| Accessories    | Bags            | Handbags, Backpacks, Travel        |
| Accessories    | Shoes           | Sneakers, Boots, Formal            |

## Grain
- One row per SKU in `products` dimension table
- `product_category` is the join key from `order_items` to `products`
- Category codes are stable — renamed annually at most, never mid-season

## Data Quality Notes
- Category assignment is manual (buying team) — not auto-classified
- ~2% of SKUs have "Uncategorized" — exclude from category-level reporting
- Outlet-only products share the same hierarchy as full-price

## Related
- [[brand]] — brand within category drives margin and return behavior
- [[collection-season]] — categories are bought per season
