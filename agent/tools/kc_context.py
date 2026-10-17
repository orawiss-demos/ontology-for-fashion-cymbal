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
kc_context — fetch full context for a specific KC entry.

Calls lookup_entry to get the entry's aspects:
  - overview  → full markdown body (OKF content or enriched glossary)
  - trust-tier → CERTIFIED_GOLD / SILVER / SANDBOX
  - verified-query → canonical SQL
  - okf-signals → status, stale_after

Returns a structured dict that the agent uses for grounding transcription:
  - The SQL and exclusion rules are inlined VERBATIM into generated queries
  - Never reference entry names in SQL — always paste the actual filter
"""

from google.cloud import dataplex_v1, resourcemanager_v3
from config import (
    GCP_PROJECT, GCP_REGION,
    ASPECT_TRUST_TIER, ASPECT_VERIFIED_QUERY, ASPECT_OKF_SIGNALS,
)

catalog_client = dataplex_v1.CatalogServiceClient()

# Resolve project number once at import
_rm_client = resourcemanager_v3.ProjectsClient()
_proj = _rm_client.get_project(name=f"projects/{GCP_PROJECT}")
PROJECT_NUMBER = _proj.name.split("/")[1]

# 'overview' is a Dataplex system aspect type, not a project-local one.
OVERVIEW_ASPECT_TYPE = "projects/dataplex-types/locations/global/aspectTypes/overview"


def kc_context(entry_name: str) -> dict:
    """Fetch full context for a KC entry by its entry name.

    Args:
        entry_name: Full entry resource name from kc_search results.

    Returns:
        Dict with keys: display_name, overview (markdown body),
        trust_tier, verified_query, okf_signals, raw_aspects.
    """
    try:
        request = dataplex_v1.LookupEntryRequest(
            name=f"projects/{GCP_PROJECT}/locations/{GCP_REGION}",
            entry=entry_name,
            view=dataplex_v1.EntryView.CUSTOM,  # default view omits aspect data
            aspect_types=[
                OVERVIEW_ASPECT_TYPE,
                f"projects/{GCP_PROJECT}/locations/{GCP_REGION}/aspectTypes/{ASPECT_TRUST_TIER}",
                f"projects/{GCP_PROJECT}/locations/{GCP_REGION}/aspectTypes/{ASPECT_VERIFIED_QUERY}",
                f"projects/{GCP_PROJECT}/locations/{GCP_REGION}/aspectTypes/{ASPECT_OKF_SIGNALS}",
            ],
        )
        entry = catalog_client.lookup_entry(request=request)
    except Exception as e:
        return {"error": str(e), "entry_name": entry_name}

    result = {
        "display_name": "",
        "overview": None,
        "trust_tier": None,
        "verified_query": None,
        "okf_signals": None,
    }

    if entry.entry_source:
        result["display_name"] = entry.entry_source.display_name or ""

    # Parse aspects — keys come back normalized, e.g. dataplex-types.global.overview
    # becomes 655216118709.global.overview and custom ones {PROJECT_NUMBER}.{REGION}.<id>
    for aspect_key, aspect in entry.aspects.items():
        data = dict(aspect.data) if aspect.data else {}

        if aspect_key.endswith(".overview"):
            result["overview"] = data.get("content", "")

        elif aspect_key.endswith(f".{ASPECT_TRUST_TIER}"):
            result["trust_tier"] = data.get("tier", "")

        elif aspect_key.endswith(f".{ASPECT_VERIFIED_QUERY}"):
            result["verified_query"] = data.get("sql", "")

        elif aspect_key.endswith(f".{ASPECT_OKF_SIGNALS}"):
            result["okf_signals"] = data

    return result
