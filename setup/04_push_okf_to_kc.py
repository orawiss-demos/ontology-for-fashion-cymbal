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
Step 4: Parse OKF markdown files and push to Knowledge Catalog.

For each .md file in okf-bundle/ (excluding index.md files):
  1. Parse YAML frontmatter with python-frontmatter
  2. Create a KC entry in the ontology entry group
  3. Attach the full markdown body as the 'overview' aspect
  4. Attach okf-signals aspect from frontmatter metadata

API gotcha (from the Fashion Cymbal build):
  - On update, aspect_keys must be set on the UpdateEntryRequest object,
    NOT passed as a kwarg. Passing as kwarg silently drops the update mask
    and the update becomes a no-op or throws.

Run: python -I setup/04_push_okf_to_kc.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import frontmatter
from google.cloud import dataplex_v1, resourcemanager_v3
from google.api_core import exceptions as gax_exceptions
from google.protobuf import field_mask_pb2
from config import (
    GCP_PROJECT, GCP_REGION,
    ENTRY_GROUP_ID, OKF_ENTRY_TYPE, ASPECT_OKF_SIGNALS,
    OKF_BUNDLE_DIR,
)

catalog_client = dataplex_v1.CatalogServiceClient()

# Resolve project number (needed for aspect keys)
rm_client = resourcemanager_v3.ProjectsClient()
project_resource = rm_client.get_project(name=f"projects/{GCP_PROJECT}")
PROJECT_NUMBER = project_resource.name.split("/")[1]

ENTRY_GROUP_PARENT = f"projects/{GCP_PROJECT}/locations/{GCP_REGION}"
ENTRY_GROUP_FULL = f"{ENTRY_GROUP_PARENT}/entryGroups/{ENTRY_GROUP_ID}"
ENTRY_TYPE_FULL = f"{ENTRY_GROUP_PARENT}/entryTypes/{OKF_ENTRY_TYPE}"

# 'overview' is a Dataplex system aspect type, not a project-local one.
OVERVIEW_ASPECT_TYPE = "projects/dataplex-types/locations/global/aspectTypes/overview"
OVERVIEW_KEY = "dataplex-types.global.overview"


def ensure_entry_type():
    """Create the OKF entry type (idempotent). Every entry needs an entry type."""
    entry_type = dataplex_v1.EntryType(
        display_name="OKF Concept",
        description="Fashion Cymbal OKF concept — metric, entity, or business rule",
    )
    request = dataplex_v1.CreateEntryTypeRequest(
        parent=ENTRY_GROUP_PARENT,
        entry_type_id=OKF_ENTRY_TYPE,
        entry_type=entry_type,
    )
    try:
        catalog_client.create_entry_type(request=request).result(timeout=120)
        print(f"Created entry type: {OKF_ENTRY_TYPE}")
    except gax_exceptions.AlreadyExists:
        print(f"Entry type already exists: {OKF_ENTRY_TYPE}")


def ensure_entry_group():
    """Create the OKF entry group (idempotent)."""
    eg = dataplex_v1.EntryGroup(
        description="Fashion Cymbal OKF ontology — metrics, entities, business rules"
    )
    request = dataplex_v1.CreateEntryGroupRequest(
        parent=ENTRY_GROUP_PARENT,
        entry_group_id=ENTRY_GROUP_ID,
        entry_group=eg,
    )
    try:
        # Long-running operation: wait, or the first create_entry races it and 404s
        catalog_client.create_entry_group(request=request).result(timeout=120)
        print(f"Created entry group: {ENTRY_GROUP_ID}")
    except gax_exceptions.AlreadyExists:
        print(f"Entry group already exists: {ENTRY_GROUP_ID}")


def collect_okf_files() -> list[Path]:
    """Find all OKF markdown files (skip index.md)."""
    files = []
    for md_file in sorted(OKF_BUNDLE_DIR.rglob("*.md")):
        if md_file.name == "index.md":
            continue
        files.append(md_file)
    return files


def parse_okf(file_path: Path) -> tuple[dict, str]:
    """Parse frontmatter and body from an OKF file."""
    post = frontmatter.load(file_path)
    return dict(post.metadata), post.content


def build_aspects(meta: dict, body: str) -> dict[str, dataplex_v1.Aspect]:
    """Build the aspect map for a KC entry from OKF frontmatter + body."""
    okf_key = f"{PROJECT_NUMBER}.{GCP_REGION}.{ASPECT_OKF_SIGNALS}"

    aspects = {
        # Overview: full markdown body — this is what agents read via lookup_context
        OVERVIEW_KEY: dataplex_v1.Aspect(
            aspect_type=OVERVIEW_ASPECT_TYPE,
            data={"content": body},
        ),
    }

    # OKF signals from frontmatter
    okf_data = {}
    if meta.get("status"):
        okf_data["status"] = meta["status"]
    if meta.get("stale_after"):
        stale_after = meta["stale_after"]  # YAML may parse it into a datetime
        okf_data["stale_after"] = stale_after.isoformat() if hasattr(stale_after, "isoformat") else str(stale_after)
    if meta.get("generated", {}).get("by"):
        okf_data["generated_by"] = meta["generated"]["by"]

    if okf_data:
        aspects[okf_key] = dataplex_v1.Aspect(
            aspect_type=f"projects/{GCP_PROJECT}/locations/{GCP_REGION}/aspectTypes/{ASPECT_OKF_SIGNALS}",
            data=okf_data,
        )

    return aspects


def push_entry(file_path: Path, meta: dict, body: str) -> None:
    """Create or update a KC entry for one OKF file."""
    # Entry ID: directory/filename without extension, e.g. "metrics-return-rate"
    rel = file_path.relative_to(OKF_BUNDLE_DIR)
    entry_id = str(rel.with_suffix("")).replace("/", "-").replace("\\", "-")

    title = meta.get("title", entry_id)
    description = meta.get("description", "")
    entry_type = meta.get("type", "OKF Concept")
    tags = meta.get("tags", [])

    aspects = build_aspects(meta, body)

    entry = dataplex_v1.Entry(
        entry_type=ENTRY_TYPE_FULL,
        # Non-Google systems must use the "custom:" FQN prefix
        fully_qualified_name=f"custom:okf.{entry_id}",
        entry_source=dataplex_v1.EntrySource(
            system="OKF",  # kc_search filters on system=OKF
            display_name=title,
            description=description,
            labels={"type": entry_type.lower().replace(" ", "-")},
        ),
        aspects=aspects,
    )

    # Try create first
    try:
        request = dataplex_v1.CreateEntryRequest(
            parent=ENTRY_GROUP_FULL,
            entry_id=entry_id,
            entry=entry,
        )
        catalog_client.create_entry(request=request)
        print(f"  Created: {entry_id} ({title}) [{len(body)} bytes]")
        return
    except gax_exceptions.AlreadyExists:
        pass

    # Update path — aspect_keys on the request object (not as kwarg!)
    entry.name = f"{ENTRY_GROUP_FULL}/entries/{entry_id}"
    update_request = dataplex_v1.UpdateEntryRequest(
        entry=entry,
        update_mask=field_mask_pb2.FieldMask(paths=["aspects", "entry_source"]),
        aspect_keys=list(aspects.keys()),
    )
    catalog_client.update_entry(request=update_request)
    print(f"  Updated: {entry_id} ({title}) [{len(body)} bytes]")


if __name__ == "__main__":
    print("=== Pushing OKF Bundle to Knowledge Catalog ===\n")

    ensure_entry_type()
    ensure_entry_group()

    files = collect_okf_files()
    print(f"\nFound {len(files)} OKF files to push:\n")

    for f in files:
        meta, body = parse_okf(f)
        push_entry(f, meta, body)

    print(f"\nPushed {len(files)} entries to {ENTRY_GROUP_ID}.")
