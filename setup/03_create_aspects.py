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
Step 3: Create custom aspect types for Knowledge Catalog.

Creates three custom aspect types:
  - trust-tier     — enum: CERTIFIED_GOLD / SILVER / SANDBOX
  - verified-query — canonical SQL + verified-by + verified-at
  - okf-signals    — OKF metadata: status, stale_after, generated_by

These aspect types are attached to glossary terms (by 05_enrich)
and OKF entries (by 04_push_okf) to carry structured metadata
alongside the prose content.

Run: python -I setup/03_create_aspects.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.cloud import dataplex_v1
from google.api_core import exceptions as gax_exceptions
from config import GCP_PROJECT, GCP_REGION, ASPECT_TRUST_TIER, ASPECT_VERIFIED_QUERY, ASPECT_OKF_SIGNALS

catalog_client = dataplex_v1.CatalogServiceClient()
PARENT = f"projects/{GCP_PROJECT}/locations/{GCP_REGION}"


ASPECT_TYPES = [
    # ── trust-tier ──────────────────────────────────────────────────────────
    {
        "id": ASPECT_TRUST_TIER,
        "description": "Data trust tier classification: CERTIFIED_GOLD (verified, canonical), SILVER (reviewed), SANDBOX (draft/experimental)",
        "template": {
            "name": "trust_tier_template",
            "type": "record",
            "record_fields": [
                {
                    "name": "tier",
                    "type": "enum",
                    "index": 1,
                    "constraints": {"required": True},
                    "annotations": {
                        "display_name": "Trust Tier",
                        "description": "Classification level for this business concept",
                    },
                    "enum_values": [
                        {"name": "CERTIFIED_GOLD", "index": 1},
                        {"name": "SILVER", "index": 2},
                        {"name": "SANDBOX", "index": 3},
                    ],
                }
            ],
        },
    },
    # ── verified-query ──────────────────────────────────────────────────────
    {
        "id": ASPECT_VERIFIED_QUERY,
        "description": "Canonical SQL query verified by a domain expert, with provenance",
        "template": {
            "name": "verified_query_template",
            "type": "record",
            "record_fields": [
                {
                    "name": "sql",
                    "type": "string",
                    "index": 1,
                    "constraints": {"required": True},
                    "annotations": {
                        "display_name": "Canonical SQL",
                        "description": "The verified SQL calculation for this metric",
                        "string_type": "richText",
                    },
                },
                {
                    "name": "verified_by",
                    "type": "string",
                    "index": 2,
                    "annotations": {
                        "display_name": "Verified By",
                        "description": "Email or name of the person who verified this query",
                    },
                },
                {
                    "name": "verified_at",
                    "type": "string",
                    "index": 3,
                    "annotations": {
                        "display_name": "Verified At",
                        "description": "ISO-8601 timestamp of verification",
                    },
                },
            ],
        },
    },
    # ── okf-signals ─────────────────────────────────────────────────────────
    {
        "id": ASPECT_OKF_SIGNALS,
        "description": "OKF metadata signals: status, staleness deadline, generation provenance",
        "template": {
            "name": "okf_signals_template",
            "type": "record",
            "record_fields": [
                {
                    "name": "status",
                    "type": "enum",
                    "index": 1,
                    "annotations": {
                        "display_name": "Status",
                        "description": "Lifecycle status of this OKF entry",
                    },
                    "enum_values": [
                        {"name": "draft", "index": 1},
                        {"name": "active", "index": 2},
                        {"name": "deprecated", "index": 3},
                    ],
                },
                {
                    "name": "stale_after",
                    "type": "string",
                    "index": 2,
                    "annotations": {
                        "display_name": "Stale After",
                        "description": "ISO-8601 date after which this entry needs re-verification",
                    },
                },
                {
                    "name": "generated_by",
                    "type": "string",
                    "index": 3,
                    "annotations": {
                        "display_name": "Generated By",
                        "description": "Author or system that created this OKF entry",
                    },
                },
            ],
        },
    },
]


def build_metadata_template(spec: dict) -> dataplex_v1.AspectType.MetadataTemplate:
    """Recursively build MetadataTemplate from a nested dict spec."""
    tmpl = dataplex_v1.AspectType.MetadataTemplate()
    tmpl.name = spec["name"]
    tmpl.type_ = spec["type"]
    if "index" in spec:
        tmpl.index = spec["index"]
    if "constraints" in spec:
        tmpl.constraints = dataplex_v1.AspectType.MetadataTemplate.Constraints(
            required=spec["constraints"].get("required", False)
        )
    if "annotations" in spec:
        ann = spec["annotations"]
        tmpl.annotations = dataplex_v1.AspectType.MetadataTemplate.Annotations(
            display_name=ann.get("display_name", ""),
            description=ann.get("description", ""),
            string_type=ann.get("string_type", ""),
        )
    if "enum_values" in spec:
        tmpl.enum_values = [
            dataplex_v1.AspectType.MetadataTemplate.EnumValue(
                name=ev["name"], index=ev["index"]
            )
            for ev in spec["enum_values"]
        ]
    if "record_fields" in spec:
        tmpl.record_fields = [
            build_metadata_template(field) for field in spec["record_fields"]
        ]
    return tmpl


def create_aspect_types() -> bool:
    ok = True
    for spec in ASPECT_TYPES:
        aspect_type = dataplex_v1.AspectType(
            description=spec["description"],
            metadata_template=build_metadata_template(spec["template"]),
        )
        request = dataplex_v1.CreateAspectTypeRequest(
            parent=PARENT,
            aspect_type_id=spec["id"],
            aspect_type=aspect_type,
        )
        try:
            op = catalog_client.create_aspect_type(request=request)
            result = op.result(timeout=120)
            print(f"Created aspect type: {spec['id']}")
        except gax_exceptions.AlreadyExists:
            print(f"Aspect type already exists: {spec['id']}")
        except Exception as e:
            print(f"Error creating {spec['id']}: {e}")
            ok = False
    return ok


if __name__ == "__main__":
    print("=== Creating Custom Aspect Types ===\n")
    if not create_aspect_types():
        print("\nFinished with errors.")
        sys.exit(1)
    print("\nDone.")
