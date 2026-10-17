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
kc_search — discover KC entries relevant to a user question.

Merges two sources (Fashion Cymbal build, Fix 3):
  1. system=dataplex  → glossary terms
  2. system=OKF       → OKF entries (rules, complex logic)

Deduplication: when the same concept appears in both, the glossary term wins
(it has trust-tier and verified-query aspects). OKF-only entries (rules like
return-window-policy that have no glossary term equivalent) are always included.

Search is executed against the GLOBAL location — regional search returns zero
(Fashion Cymbal API finding). Global search spans every glossary and entry group the
caller can see, so results are filtered to this demo's glossary and OKF group.
"""

import time
from google.cloud import dataplex_v1
from google.api_core import exceptions as gax_exceptions
from config import GCP_PROJECT, GLOSSARY_ID, ENTRY_GROUP_ID


catalog_client = dataplex_v1.CatalogServiceClient()

# OKF entry IDs are "<bundle dir>-<concept>", e.g. metrics-return-rate
OKF_DIR_PREFIXES = ("metrics-", "entities-", "rules-")


def _concept_key(entry_name: str, system_label: str) -> str | None:
    """Normalize an entry name to its concept slug, or None if it isn't ours.

    Glossary: .../glossaries/fashion-cymbal-glossary/terms/return-rate → return-rate
    OKF:      .../entryGroups/fashion-cymbal-ontology/entries/metrics-return-rate → return-rate
    """
    if system_label == "dataplex":
        marker = f"/glossaries/{GLOSSARY_ID}/terms/"
    else:
        marker = f"/entryGroups/{ENTRY_GROUP_ID}/entries/"
    if marker not in entry_name:
        return None
    slug = entry_name.split(marker, 1)[1]
    if system_label != "dataplex":
        for prefix in OKF_DIR_PREFIXES:
            if slug.startswith(prefix):
                return slug[len(prefix):]
    return slug


TRANSIENT_ERRORS = (
    gax_exceptions.ResourceExhausted,
    gax_exceptions.ServiceUnavailable,
    gax_exceptions.DeadlineExceeded,
)


def _search(request: dataplex_v1.SearchEntriesRequest, attempts: int = 4):
    """search_entries with backoff on throttling / transient failures.

    Throttling can also surface as a ValueError from the gRPC status parser
    ("... doesn't match status code (RESOURCE_EXHAUSTED)").
    """
    for attempt in range(attempts):
        try:
            return list(catalog_client.search_entries(request=request).results)
        except (*TRANSIENT_ERRORS, ValueError) as e:
            if isinstance(e, ValueError) and "RESOURCE_EXHAUSTED" not in str(e):
                raise
            if attempt == attempts - 1:
                raise
            time.sleep(2 ** attempt)


def kc_search(query: str) -> list[dict]:
    """Search KC for entries matching the query.

    Returns a list of dicts with: name, display_name, entry_type, source, description.
    Merges glossary (system=dataplex) and OKF (system=OKF) results,
    deduplicating by concept name with glossary preferred.

    Args:
        query: Natural language search query.

    Returns:
        List of matching KC entries with metadata.
    """
    results = {}

    # Glossary first, so it wins the dedup
    for system_label in ["dataplex", "OKF"]:
        try:
            # Search must hit global — regional returns nothing
            request = dataplex_v1.SearchEntriesRequest(
                name=f"projects/{GCP_PROJECT}/locations/global",
                query=f"{query} system={system_label}",
                page_size=25,  # headroom: other glossaries/groups are filtered out below
            )
            for result in _search(request):
                entry = result.dataplex_entry
                if not entry:
                    continue

                # Skip entries from other glossaries / entry groups / projects
                entry_name = entry.name
                concept_key = _concept_key(entry_name, system_label)
                if concept_key is None:
                    continue

                # Extract display name from entry source
                display_name = ""
                description = ""
                if entry.entry_source:
                    display_name = entry.entry_source.display_name or ""
                    description = entry.entry_source.description or ""

                # Determine source label
                source = "Glossary Term" if system_label == "dataplex" else "OKF Entry"

                # Dedup: glossary wins over OKF for same concept
                if concept_key in results and results[concept_key]["source"] == "Glossary Term":
                    continue

                results[concept_key] = {
                    "name": entry_name,
                    "display_name": display_name or concept_key,
                    "entry_type": source,
                    "source": source,
                    "description": description,
                }

        except Exception as e:
            # Search can timeout or return partial — non-fatal
            print(f"Warning: kc_search({system_label}): {e}")

    return list(results.values())
