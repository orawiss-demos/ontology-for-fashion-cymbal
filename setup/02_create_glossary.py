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
Step 2: Create Knowledge Catalog glossary with terms and entry links.

Creates:
  - Business glossary: fashion-cymbal-glossary
  - 9 glossary terms (4 metrics, 4 entities, 1 alias)
  - 5 term-to-term entry links (SYNONYM, RELATED)

API gotchas (from the Fashion Cymbal build, verified against live API):
  1. Glossary term entry names embed project NUMBER, not project ID.
  2. Entry links must be created in the source entry's entry group and region
     (@dataplex for term→term, @bigquery for DEFINITION→table).
  3. SYNONYM and RELATED are undirected — only one link needed per pair.
  4. Only DEFINITION uses SOURCE/TARGET semantics.

Run: python -I setup/02_create_glossary.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import time
from google.cloud import dataplex_v1
from google.api_core import exceptions as gax_exceptions
from config import GCP_PROJECT, GCP_REGION, GLOSSARY_ID

# --- Client setup ---
catalog_client = dataplex_v1.CatalogServiceClient()
glossary_client = dataplex_v1.BusinessGlossaryServiceClient()

# Resolve project number (entry names require it, not project ID)
from google.cloud import resourcemanager_v3
rm_client = resourcemanager_v3.ProjectsClient()
project_resource = rm_client.get_project(name=f"projects/{GCP_PROJECT}")
PROJECT_NUMBER = project_resource.name.split("/")[1]  # "projects/123456" → "123456"
print(f"Project: {GCP_PROJECT} (number: {PROJECT_NUMBER})")

GLOSSARY_PARENT = f"projects/{GCP_PROJECT}/locations/{GCP_REGION}"
GLOSSARY_FULL = f"{GLOSSARY_PARENT}/glossaries/{GLOSSARY_ID}"

# Each glossary term is mirrored as a catalog entry in the @dataplex entry group:
# projects/{NUMBER}/locations/{REGION}/entryGroups/@dataplex/entries/projects/{NUMBER}/locations/{REGION}/glossaries/{GLOSSARY_ID}/terms/{TERM_ID}
TERM_ENTRY_PREFIX = f"projects/{PROJECT_NUMBER}/locations/{GCP_REGION}/entryGroups/@dataplex/entries"
ENTRY_LINK_TYPES = "projects/dataplex-types/locations/global/entryLinkTypes"


def term_entry_name(term_id: str) -> str:
    """Return the full entry name for a glossary term (uses project NUMBER)."""
    return f"{TERM_ENTRY_PREFIX}/projects/{PROJECT_NUMBER}/locations/{GCP_REGION}/glossaries/{GLOSSARY_ID}/terms/{term_id}"


# ── Glossary terms ──────────────────────────────────────────────────────────
# Each tuple: (term_id, display_name, description)
TERMS = [
    # Metrics
    ("return-rate", "Return Rate",
     "Ratio of returned items to total items sold, measured by unit count not revenue"),
    ("sell-through-rate", "Sell-Through Rate",
     "Ratio of units sold to units received into inventory"),
    ("average-basket-value", "Average Basket Value",
     "Mean net order value after discounts, before returns"),
    ("gross-margin", "Gross Margin",
     "Revenue minus cost of goods sold as percentage of revenue"),
    # Entities
    ("product-category", "Product Category",
     "Three-level product hierarchy: Department > Category > Subcategory"),
    ("brand", "Brand",
     "Brand identity with tier classification (Premium, Core, Entry, Private Label)"),
    ("sales-channel", "Sales Channel",
     "Transaction channel: Online, Store, Outlet, Marketplace, Click-and-Collect"),
    ("collection-season", "Collection Season",
     "Seasonal collection with lifecycle stages from Pre-Season through Outlet"),
    # Alias (synonym pointer for common shorthand)
    ("rr", "RR",
     "Synonym for Return Rate"),
]

# ── Entry links ─────────────────────────────────────────────────────────────
# SYNONYM and RELATED are undirected — one entry per pair.
# Created in @dataplex entry group (term-to-term).
TERM_LINKS = [
    # (link_id, source_term_id, target_term_id, relationship)
    ("rr-synonym", "return-rate", "rr", "SYNONYM"),
    ("return-rate-to-sell-through", "return-rate", "sell-through-rate", "RELATED"),
    ("return-rate-to-gross-margin", "return-rate", "gross-margin", "RELATED"),
    ("gross-margin-to-brand", "gross-margin", "brand", "RELATED"),
    ("return-rate-to-basket", "return-rate", "average-basket-value", "RELATED"),
]


def with_retry(call, attempts: int = 5):
    """Run call(), backing off when the glossary API rate-limits us.

    Throttling may surface as ResourceExhausted or as a ValueError from the
    gRPC status parser ("... doesn't match status code (RESOURCE_EXHAUSTED)").
    """
    for attempt in range(attempts):
        try:
            return call()
        except (gax_exceptions.ResourceExhausted, ValueError) as e:
            if "RESOURCE_EXHAUSTED" not in str(e) and not isinstance(e, gax_exceptions.ResourceExhausted):
                raise
            if attempt == attempts - 1:
                raise
            time.sleep(2 ** attempt * 2)


def create_glossary() -> bool:
    """Create the business glossary (idempotent)."""
    glossary = dataplex_v1.Glossary(
        display_name="Fashion Cymbal Glossary",
        description="Fashion Cymbal business glossary — metrics, entities, and classification terms",
    )
    request = dataplex_v1.CreateGlossaryRequest(
        parent=GLOSSARY_PARENT,
        glossary_id=GLOSSARY_ID,
        glossary=glossary,
    )
    try:
        glossary_client.create_glossary(request=request).result(timeout=120)
        print(f"Created glossary: {GLOSSARY_ID}")
    except gax_exceptions.AlreadyExists:
        print(f"Glossary already exists: {GLOSSARY_ID}")
    except Exception as e:
        print(f"Error creating glossary {GLOSSARY_ID}: {e.message if hasattr(e, 'message') else e}")
        return False
    return True


def create_terms() -> bool:
    """Create glossary terms directly under the glossary."""
    ok = True
    for term_id, display_name, description in TERMS:
        term = dataplex_v1.GlossaryTerm(
            display_name=display_name,
            description=description,
            parent=GLOSSARY_FULL,
        )
        request = dataplex_v1.CreateGlossaryTermRequest(
            parent=GLOSSARY_FULL,
            term_id=term_id,
            term=term,
        )
        # The term API reports duplicates as a generic error, not AlreadyExists,
        # so check existence first.
        try:
            with_retry(lambda: glossary_client.get_glossary_term(name=f"{GLOSSARY_FULL}/terms/{term_id}"))
            print(f"  Term already exists: {term_id}")
            continue
        except gax_exceptions.NotFound:
            pass
        except Exception as e:
            print(f"  Error checking term {term_id}: {e.message if hasattr(e, 'message') else e}")
            ok = False
            continue
        try:
            with_retry(lambda: glossary_client.create_glossary_term(request=request))
            print(f"  Created term: {term_id} ({display_name})")
        except Exception as e:
            print(f"  Error creating term {term_id}: {e.message if hasattr(e, 'message') else e}")
            ok = False
    return ok


def create_term_links() -> bool:
    """Create SYNONYM and RELATED links between glossary terms.

    Links are created in the @dataplex entry group (same region as the glossary).
    SYNONYM and RELATED are undirected, so both references are UNSPECIFIED.
    """
    dataplex_parent = f"projects/{GCP_PROJECT}/locations/{GCP_REGION}/entryGroups/@dataplex"
    unspecified = dataplex_v1.EntryLink.EntryReference.Type.UNSPECIFIED

    ok = True
    for link_id, source_id, target_id, relationship in TERM_LINKS:
        link = dataplex_v1.EntryLink(
            entry_link_type=f"{ENTRY_LINK_TYPES}/{relationship.lower()}",
            entry_references=[
                dataplex_v1.EntryLink.EntryReference(name=term_entry_name(source_id), type_=unspecified),
                dataplex_v1.EntryLink.EntryReference(name=term_entry_name(target_id), type_=unspecified),
            ],
        )
        request = dataplex_v1.CreateEntryLinkRequest(
            parent=dataplex_parent,
            # Link IDs are unique across all of @dataplex, so namespace them per glossary
            entry_link_id=f"{GLOSSARY_ID}-{link_id}",
            entry_link=link,
        )
        try:
            catalog_client.create_entry_link(request=request)
            print(f"  Created link: {source_id} --{relationship}--> {target_id}")
        except gax_exceptions.AlreadyExists:
            print(f"  Link already exists: {GLOSSARY_ID}-{link_id}")
        except Exception as e:
            print(f"  Error creating link {GLOSSARY_ID}-{link_id}: {e.message if hasattr(e, 'message') else e}")
            ok = False
    return ok


if __name__ == "__main__":
    print("\n=== Creating Glossary ===")
    if not create_glossary():
        sys.exit(1)
    time.sleep(2)  # eventual consistency

    print("\n=== Creating Terms ===")
    ok = create_terms()
    time.sleep(5)  # terms sync to @dataplex catalog entries asynchronously

    print("\n=== Creating Entry Links ===")
    ok = create_term_links() and ok

    if not ok:
        print("\nGlossary setup finished with errors.")
        sys.exit(1)

    print("\nGlossary setup complete.")
    print(f"Console: https://console.cloud.google.com/dataplex/glossaries/{GLOSSARY_ID}?project={GCP_PROJECT}")
