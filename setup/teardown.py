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
Teardown: delete all demo resources in the correct order.

Deletion order matters:
  1. OKF entries (in fashion-cymbal-ontology entry group)
  2. OKF entry group, then the okf-concept entry type
  3. Entry links between glossary terms (in @dataplex)
     — links MUST be deleted before the terms they reference
  4. Glossary terms — terms MUST be deleted before the glossary
  5. Business glossary
  6. Custom aspect types (trust-tier, verified-query, okf-signals)
  7. BigQuery dataset (with delete_contents=True)

Asks for confirmation before proceeding.

Run: python -I setup/teardown.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.cloud import dataplex_v1, bigquery, resourcemanager_v3
from google.api_core import exceptions as gax_exceptions
from config import (
    GCP_PROJECT, GCP_REGION,
    ENTRY_GROUP_ID, OKF_ENTRY_TYPE, GLOSSARY_ID, BQ_DATASET,
    ASPECT_TRUST_TIER, ASPECT_VERIFIED_QUERY, ASPECT_OKF_SIGNALS,
)

catalog_client = dataplex_v1.CatalogServiceClient()
glossary_client = dataplex_v1.BusinessGlossaryServiceClient()
bq_client = bigquery.Client(project=GCP_PROJECT)

PARENT = f"projects/{GCP_PROJECT}/locations/{GCP_REGION}"
GLOSSARY_FULL = f"{PARENT}/glossaries/{GLOSSARY_ID}"

# Glossary term entry names embed the project NUMBER, not the project ID
_project = resourcemanager_v3.ProjectsClient().get_project(name=f"projects/{GCP_PROJECT}")
PROJECT_NUMBER = _project.name.split("/")[1]
TERM_ENTRY_PREFIX = f"projects/{PROJECT_NUMBER}/locations/{GCP_REGION}/entryGroups/@dataplex/entries"


def delete_entries_in_group(entry_group_id: str) -> int:
    """Delete all entries in an entry group. Returns count."""
    eg_path = f"{PARENT}/entryGroups/{entry_group_id}"
    count = 0
    try:
        entries = catalog_client.list_entries(
            request=dataplex_v1.ListEntriesRequest(parent=eg_path, page_size=100)
        )
        for entry in entries:
            # Dataplex auto-creates an entry describing the group itself; it goes with the group
            if entry.entry_type.endswith("/entryTypes/entrygroup"):
                continue
            try:
                catalog_client.delete_entry(name=entry.name)
                count += 1
            except gax_exceptions.NotFound:
                pass
    except gax_exceptions.NotFound:
        pass
    return count


def delete_entry_group(entry_group_id: str) -> bool:
    """Delete an entry group. Returns True if deleted."""
    eg_path = f"{PARENT}/entryGroups/{entry_group_id}"
    try:
        catalog_client.delete_entry_group(name=eg_path).result(timeout=120)
        return True
    except gax_exceptions.NotFound:
        return False
    except gax_exceptions.FailedPrecondition as e:
        print(f"  Cannot delete {entry_group_id} — still has entries: {e}")
        return False


def delete_entry_type(entry_type_id: str) -> bool:
    """Delete a custom entry type. Returns True if deleted."""
    et_path = f"{PARENT}/entryTypes/{entry_type_id}"
    try:
        catalog_client.delete_entry_type(name=et_path).result(timeout=120)
        return True
    except gax_exceptions.NotFound:
        return False
    except Exception as e:
        print(f"  Cannot delete entry type {entry_type_id}: {e}")
        return False


def list_glossary_terms() -> list:
    """List all terms in the glossary (empty if the glossary is gone)."""
    try:
        return list(glossary_client.list_glossary_terms(parent=GLOSSARY_FULL))
    except gax_exceptions.NotFound:
        return []


def delete_term_links(terms: list) -> int:
    """Delete every entry link that references a glossary term. Returns count."""
    link_names = set()
    for term in terms:
        # term.name uses the project ID; the catalog entry needs the project NUMBER
        term_id = term.name.rsplit("/", 1)[1]
        term_entry = (
            f"{TERM_ENTRY_PREFIX}/projects/{PROJECT_NUMBER}/locations/{GCP_REGION}"
            f"/glossaries/{GLOSSARY_ID}/terms/{term_id}"
        )
        try:
            links = catalog_client.lookup_entry_links(
                request=dataplex_v1.LookupEntryLinksRequest(name=PARENT, entry=term_entry)
            )
            link_names.update(link.name for link in links)
        except (gax_exceptions.NotFound, gax_exceptions.PermissionDenied):
            pass  # a missing entry surfaces as 403
    count = 0
    for name in sorted(link_names):
        try:
            catalog_client.delete_entry_link(name=name)
            count += 1
        except gax_exceptions.NotFound:
            pass
    return count


def delete_terms(terms: list) -> int:
    """Delete glossary terms. Returns count."""
    count = 0
    for term in terms:
        try:
            glossary_client.delete_glossary_term(name=term.name)
            count += 1
        except gax_exceptions.NotFound:
            pass
    return count


def delete_glossary() -> bool:
    """Delete the business glossary. Returns True if deleted."""
    try:
        glossary_client.delete_glossary(name=GLOSSARY_FULL).result(timeout=120)
        return True
    except gax_exceptions.NotFound:
        return False
    except Exception as e:
        print(f"  Cannot delete glossary {GLOSSARY_ID}: {e}")
        return False


def delete_aspect_type(aspect_type_id: str) -> bool:
    """Delete a custom aspect type. Returns True if deleted."""
    at_path = f"{PARENT}/aspectTypes/{aspect_type_id}"
    try:
        op = catalog_client.delete_aspect_type(name=at_path)
        op.result(timeout=60)
        return True
    except gax_exceptions.NotFound:
        return False
    except Exception as e:
        print(f"  Cannot delete aspect type {aspect_type_id}: {e}")
        return False


def delete_bq_dataset() -> bool:
    """Delete the BQ demo dataset with all contents."""
    dataset_ref = f"{GCP_PROJECT}.{BQ_DATASET}"
    try:
        bq_client.delete_dataset(dataset_ref, delete_contents=True)
        return True
    except gax_exceptions.NotFound:
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Fashion Cymbal Ontology Demo — TEARDOWN")
    print("=" * 60)
    print(f"\nProject:    {GCP_PROJECT}")
    print(f"Region:     {GCP_REGION}")
    print(f"Entry grp:  {ENTRY_GROUP_ID}")
    print(f"Glossary:   {GLOSSARY_ID}")
    print(f"BQ dataset: {BQ_DATASET}")
    print(f"Aspects:    {ASPECT_TRUST_TIER}, {ASPECT_VERIFIED_QUERY}, {ASPECT_OKF_SIGNALS}")
    print()

    confirm = input("Delete ALL of the above? (yes/no): ").strip().lower()
    if confirm != "yes":
        print("Aborted.")
        sys.exit(0)

    print()

    # 1. OKF entries
    print("1. Deleting OKF entries...", end=" ", flush=True)
    n = delete_entries_in_group(ENTRY_GROUP_ID)
    print(f"{n} deleted")

    # 2. OKF entry group
    print("2. Deleting OKF entry group...", end=" ", flush=True)
    ok = delete_entry_group(ENTRY_GROUP_ID)
    print("done" if ok else "not found")

    print("   Deleting OKF entry type...", end=" ", flush=True)
    ok = delete_entry_type(OKF_ENTRY_TYPE)
    print("done" if ok else "not found")

    # 3. Term-to-term entry links (must go before the terms)
    terms = list_glossary_terms()
    print("3. Deleting glossary entry links...", end=" ", flush=True)
    n = delete_term_links(terms)
    print(f"{n} deleted")

    # 4. Glossary terms (must go before the glossary)
    print("4. Deleting glossary terms...", end=" ", flush=True)
    n = delete_terms(terms)
    print(f"{n} deleted")

    # 5. Business glossary
    print("5. Deleting glossary...", end=" ", flush=True)
    ok = delete_glossary()
    print("done" if ok else "not found")

    # Legacy: older 02_create_glossary.py runs created an entry group with the glossary's ID
    if delete_entry_group(GLOSSARY_ID):
        print("   Deleted legacy glossary entry group")

    # 6. Custom aspect types
    for at_id in [ASPECT_TRUST_TIER, ASPECT_VERIFIED_QUERY, ASPECT_OKF_SIGNALS]:
        print(f"6. Deleting aspect type: {at_id}...", end=" ", flush=True)
        ok = delete_aspect_type(at_id)
        print("done" if ok else "not found")

    # 7. BigQuery dataset
    print(f"7. Deleting BQ dataset: {BQ_DATASET}...", end=" ", flush=True)
    ok = delete_bq_dataset()
    print("done" if ok else "not found")

    print("\nTeardown complete.")
