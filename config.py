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
Shared configuration for the Fashion Cymbal Ontology demo.

All GCP resource names and settings in one place.
Override via environment variables or .env file.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

# --- GCP project -----------------------------------------------------------
GCP_PROJECT = os.getenv("GCP_PROJECT", "YOUR_PROJECT_ID")
GCP_REGION = os.getenv("GCP_REGION", "europe-west1")

# Vertex AI model endpoint — may differ from GCP_REGION.
# Some models (gemini-3.6-flash) resolve only from 'global'.
VERTEX_LOCATION = os.getenv("VERTEX_LOCATION", "global")

# Route the google-genai client (used by ADK) to Vertex AI with ADC credentials.
# Without these it defaults to the Gemini Developer API and demands an API key.
os.environ.setdefault("GOOGLE_GENAI_USE_ENTERPRISE", "true")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", GCP_PROJECT)
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", VERTEX_LOCATION)

# --- Knowledge Catalog resources -------------------------------------------
ENTRY_GROUP_ID = "fashion-cymbal-ontology"
GLOSSARY_ID = "fashion-cymbal-glossary"
OKF_ENTRY_TYPE = "okf-concept"

# Custom aspect type IDs
ASPECT_TRUST_TIER = "trust-tier"
ASPECT_VERIFIED_QUERY = "verified-query"
ASPECT_OKF_SIGNALS = "okf-signals"

# --- BigQuery ---------------------------------------------------------------
BQ_DATASET = "fashion_cymbal_demo"

BQ_TABLES = {
    "order_items": f"{GCP_PROJECT}.{BQ_DATASET}.order_items",
    "orders": f"{GCP_PROJECT}.{BQ_DATASET}.orders",
    "products": f"{GCP_PROJECT}.{BQ_DATASET}.products",
    "inventory_movement": f"{GCP_PROJECT}.{BQ_DATASET}.inventory_movement",
}

# --- Paths ------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent
OKF_BUNDLE_DIR = REPO_ROOT / "okf-bundle"

# --- Model ------------------------------------------------------------------
DEFAULT_MODEL = os.getenv("AGENT_MODEL", "gemini-2.5-flash")
