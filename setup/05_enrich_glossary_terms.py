#!/usr/bin/env python3
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

"""
Step 5: Enrich glossary terms with OKF content, trust tiers, and verified queries.

This combines the Fashion Cymbal build's Fix 1 (overview body) and Fix 2 (trust-tier + verified-query)
into a single update_entry call per term — avoids double round-trip and race condition.

For each glossary term that has a matching OKF file:
  1. Read the OKF markdown body
  2. Write it into the glossary term's 'overview' aspect (so agents see it)
  3. Attach trust-tier aspect (CERTIFIED_GOLD for metrics, SILVER for entities)
  4. Attach verified-query aspect (canonical SQL extracted from the OKF body)

API gotcha (from the Fashion Cymbal build):
  aspect_keys must be on the UpdateEntryRequest object, not a kwarg.

Run: python -I setup/05_enrich_glossary_terms.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import re
import frontmatter
from google.cloud import dataplex_v1, resourcemanager_v3
from google.api_core import exceptions as gax_exceptions
from google.protobuf import field_mask_pb2
from config import (
    GCP_PROJECT, GCP_REGION, GLOSSARY_ID,
    ASPECT_TRUST_TIER, ASPECT_VERIFIED_QUERY,
    OKF_BUNDLE_DIR,
)

catalog_client = dataplex_v1.CatalogServiceClient()

# Resolve project number
rm_client = resourcemanager_v3.ProjectsClient()
project_resource = rm_client.get_project(name=f"projects/{GCP_PROJECT}")
PROJECT_NUMBER = project_resource.name.split("/")[1]

GLOSSARY_FULL = f"projects/{PROJECT_NUMBER}/locations/{GCP_REGION}/glossaries/{GLOSSARY_ID}"

# 'overview' is a Dataplex system aspect type, not a project-local one.
OVERVIEW_ASPECT_TYPE = "projects/dataplex-types/locations/global/aspectTypes/overview"
OVERVIEW_KEY = "dataplex-types.global.overview"


# ── Term → OKF file mapping ────────────────────────────────────────────────
# Maps glossary term IDs to their OKF file paths and enrichment config.
# Trust tier: CERTIFIED_GOLD for metrics (verified SQL), SILVER for entities.
TERM_CONFIG = {
    # Metrics — CERTIFIED_GOLD (have verified canonical SQL)
    "return-rate": {
        "okf_path": "metrics/return-rate.md",
        "trust_tier": "CERTIFIED_GOLD",
        "extract_sql": True,
    },
    "sell-through-rate": {
        "okf_path": "metrics/sell-through-rate.md",
        "trust_tier": "CERTIFIED_GOLD",
        "extract_sql": True,
    },
    "average-basket-value": {
        "okf_path": "metrics/average-basket-value.md",
        "trust_tier": "CERTIFIED_GOLD",
        "extract_sql": True,
    },
    "gross-margin": {
        "okf_path": "metrics/gross-margin.md",
        "trust_tier": "CERTIFIED_GOLD",
        "extract_sql": True,
    },
    # Entities — SILVER (reviewed but no canonical SQL)
    "product-category": {
        "okf_path": "entities/product-category.md",
        "trust_tier": "SILVER",
        "extract_sql": False,
    },
    "brand": {
        "okf_path": "entities/brand.md",
        "trust_tier": "SILVER",
        "extract_sql": False,
    },
    "sales-channel": {
        "okf_path": "entities/sales-channel.md",
        "trust_tier": "SILVER",
        "extract_sql": False,
    },
    "collection-season": {
        "okf_path": "entities/collection-season.md",
        "trust_tier": "SILVER",
        "extract_sql": False,
    },
}


def extract_first_sql_block(body: str) -> str | None:
    """Extract the first ```sql ... ``` block from markdown body."""
    match = re.search(r"```sql\s*\n(.*?)```", body, re.DOTALL)
    return match.group(1).strip() if match else None


def extract_verified_by(meta: dict) -> tuple[str | None, str | None]:
    """Extract the first verified-by name and timestamp from OKF frontmatter."""
    verified = meta.get("verified", [])
    if verified and isinstance(verified, list) and len(verified) > 0:
        first = verified[0]
        at = first.get("at", "")  # YAML may parse it into a datetime
        return first.get("by"), at.isoformat() if hasattr(at, "isoformat") else str(at)
    return None, None


def enrich_term(term_id: str, config: dict) -> bool:
    """Update a single glossary term with OKF content + aspects."""
    okf_file = OKF_BUNDLE_DIR / config["okf_path"]
    if not okf_file.exists():
        print(f"  SKIP {term_id}: OKF file not found ({config['okf_path']})")
        return False

    post = frontmatter.load(okf_file)
    meta = dict(post.metadata)
    body = post.content

    # Build the entry name (glossary terms are mirrored into the @dataplex entry group)
    entry_name = (
        f"projects/{PROJECT_NUMBER}/locations/{GCP_REGION}"
        f"/entryGroups/@dataplex/entries/{GLOSSARY_FULL}/terms/{term_id}"
    )

    # Build aspect map — all three aspects in one update
    trust_key = f"{PROJECT_NUMBER}.{GCP_REGION}.{ASPECT_TRUST_TIER}"
    query_key = f"{PROJECT_NUMBER}.{GCP_REGION}.{ASPECT_VERIFIED_QUERY}"

    aspects = {
        # Overview: full OKF markdown body
        OVERVIEW_KEY: dataplex_v1.Aspect(
            aspect_type=OVERVIEW_ASPECT_TYPE,
            data={"content": body},
        ),
        # Trust tier
        trust_key: dataplex_v1.Aspect(
            aspect_type=f"projects/{GCP_PROJECT}/locations/{GCP_REGION}/aspectTypes/{ASPECT_TRUST_TIER}",
            data={"tier": config["trust_tier"]},
        ),
    }
    aspect_keys = [OVERVIEW_KEY, trust_key]

    # Verified query (metrics only)
    if config["extract_sql"]:
        sql = extract_first_sql_block(body)
        if sql:
            verified_by, verified_at = extract_verified_by(meta)
            query_data = {"sql": sql}
            if verified_by:
                query_data["verified_by"] = verified_by
            if verified_at:
                query_data["verified_at"] = verified_at

            aspects[query_key] = dataplex_v1.Aspect(
                aspect_type=f"projects/{GCP_PROJECT}/locations/{GCP_REGION}/aspectTypes/{ASPECT_VERIFIED_QUERY}",
                data=query_data,
            )
            aspect_keys.append(query_key)

    # Single update — aspect_keys on the request object (NOT as kwarg)
    entry = dataplex_v1.Entry(name=entry_name, aspects=aspects)
    update_request = dataplex_v1.UpdateEntryRequest(
        entry=entry,
        update_mask=field_mask_pb2.FieldMask(paths=["aspects"]),
        aspect_keys=aspect_keys,
    )

    try:
        catalog_client.update_entry(request=update_request)
        tier = config["trust_tier"]
        sql_flag = " + verified-query" if config["extract_sql"] else ""
        body_len = len(body)
        print(f"  Enriched: {term_id} [{body_len}b overview, {tier}{sql_flag}]")
        return True
    except gax_exceptions.NotFound:
        print(f"  NOT FOUND: {term_id} — run 02_create_glossary.py first")
    except Exception as e:
        print(f"  ERROR on {term_id}: {e.message if hasattr(e, 'message') else e}")
    return False


if __name__ == "__main__":
    print("=== Enriching Glossary Terms with OKF Content ===\n")

    ok = True
    for term_id, config in TERM_CONFIG.items():
        ok = enrich_term(term_id, config) and ok

    if not ok:
        print("\nEnrichment finished with errors.")
        sys.exit(1)

    print("\nEnrichment complete.")
    print(f"Console: https://console.cloud.google.com/dataplex/glossaries/{GLOSSARY_ID}?project={GCP_PROJECT}")
