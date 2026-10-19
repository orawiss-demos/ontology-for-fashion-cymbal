# Fashion Cymbal Ontology Demo
## Author : Wissem Khlifi 
> **DISCLAIMER — DEMONSTRATION CODE, NOT FOR PRODUCTION USE**
>
> This project is a demonstration example, provided solely to illustrate
> concepts and for learning purposes. It is not an official Google product
> and is not supported by Google.
>
> The code is provided "as is", without warranty of any kind, express or
> implied. It has not been hardened, security-reviewed, or tested for
> production workloads, and it must not be relied upon to run production
> systems or to process business-critical data.
>
> The author accepts no responsibility or liability for any failure, defect,
> data loss, cost, or other damage arising from the use, adaptation, or
> deployment of this example in any environment, including customer
> environments. Anyone reusing any part of it does so at their own risk and
> should review, test, and adapt it thoroughly first.

OKF (Open Knowledge Format) + Knowledge Catalog + ADK agent demo for fashion retail analytics. Built for Fashion Cymbal as a demo of business ontology-driven analytics.

## What This Does

This demo shows how to define business knowledge (metrics, entities, rules) as markdown files using the OKF spec, push them to Google Cloud Knowledge Catalog, and wire up an ADK agent that grounds its SQL generation in that cataloged knowledge.

```
┌─────────────────────┐
│  OKF Markdown Files  │  ← Business knowledge as code (git-managed)
│  (okf-bundle/)       │
└─────────┬───────────┘
          │ 04_push_okf_to_kc.py
          ▼
┌─────────────────────┐     ┌─────────────────────┐
│  Knowledge Catalog   │────▶│  Ontology Agent (ADK)│
│  - Glossary terms    │     │  - kc_search         │
│  - OKF entries       │     │  - kc_context         │
│  - Trust tiers       │     │  - bq_execute         │
│  - Verified queries  │     └──────────┬────────────┘
└─────────────────────┘                │
                                       ▼
                              ┌─────────────────────┐
                              │  BigQuery            │
                              │  (fashion_cymbal_demo)│
                              └─────────────────────┘
```

### The Agent's Three-Stage Workflow

1. **Search** — `kc_search` discovers glossary terms and OKF entries relevant to the question
2. **Context** — `kc_context` fetches full definitions, canonical SQL, and business rules
3. **Execute** — Grounding transcription inlines rules VERBATIM into SQL, then `bq_execute` runs it

## Prerequisites

- Python 3.11+
- A GCP project with these APIs enabled:
  - BigQuery API
  - Dataplex API (Knowledge Catalog)
  - Vertex AI API
- Authenticated: `gcloud auth application-default login`

## Setup

```bash
# 1. Clone and install
git clone https://github.com/orawiss/ontology-for-fashion-cymbal.git
cd ontology-for-fashion-cymbal
pip install -e .

# 2. Configure
cp .env.example .env
# Edit .env — set GCP_PROJECT to your project ID

# 3. Create resources (run in order)
python -I setup/01_create_sample_bq.py      # BigQuery tables with demo data
python -I setup/02_create_glossary.py        # KC business glossary + 9 terms + 5 entry links
python -I setup/03_create_aspects.py         # Custom aspect types
python -I setup/04_push_okf_to_kc.py         # okf-concept entry type + 11 OKF entries
python -I setup/05_enrich_glossary_terms.py  # Write OKF body into glossary terms
```

## Run the Agent

```bash
python -m agent.app
```

### Example Questions

| Question | What the agent does |
|----------|---------------------|
| "What is our return rate for Women's Outerwear?" | Fetches return-rate definition, applies exclusions, filters by department+category |
| "Show me sell-through by brand for FW26" | Uses inventory_movement, excludes outlet warehouse and samples |
| "What does outlet classification mean?" | Explains the four-condition rule from OKF (no SQL) |
| "Average basket value for online orders?" | Queries orders table with channel filter and all exclusions |
| "Return rate for outlet transactions only?" | Cross-references return-rate AND outlet-vs-fullprice OKF entries |

## Run Tests

```bash
# Unit + OKF bundle validation
pytest tests/

# Include integration tests (requires deployed GCP resources)
pytest tests/ --run-integration
```

## Tear Down

```bash
python -I setup/teardown.py
```

Deletes the OKF entries, entry group and entry type, the glossary's entry links, terms and glossary, the aspect types, and the BQ dataset — in dependency order. Asks for confirmation.

## OKF Bundle Structure

```
okf-bundle/
├── index.md                     # Navigation
├── metrics/
│   ├── return-rate.md           # Hero metric — unit-based return ratio
│   ├── sell-through-rate.md     # Inventory efficiency
│   ├── average-basket-value.md  # Order value across channels
│   └── gross-margin.md          # Revenue minus COGS
├── entities/
│   ├── product-category.md      # Three-level hierarchy
│   ├── brand.md                 # Brand tiers
│   ├── sales-channel.md         # Online/Store/Outlet/Marketplace/CNC
│   └── collection-season.md     # Season lifecycle stages
└── rules/
    ├── return-window-policy.md  # Channel-specific return windows + holiday exception
    ├── markdown-cadence.md      # Seasonal price reduction schedule
    └── outlet-vs-fullprice.md   # Four-condition outlet classification
```

Each file follows the OKF spec: YAML frontmatter (`type` required, plus optional `title`, `tags`, `status`, `verified`, `stale_after`) and a markdown body with definitions, SQL, exclusions, and `[[wikilink]]` cross-references.

## Key Design Decisions

1. **Grounding transcription** — The agent never references KC entry names in SQL. It reads the rule from KC and pastes the actual SQL filter verbatim.
2. **Dual-source merge** — `kc_search` queries both glossary terms (`system=dataplex`) and OKF entries (`system=OKF`), deduplicating by concept slug with glossary preferred (`metrics-return-rate` and term `return-rate` are the same concept). OKF-only entries (rules without a glossary equivalent) are always included.
3. **Trust tiers** — Metrics are `CERTIFIED_GOLD` (have verified canonical SQL), entities are `SILVER` (reviewed, no canonical SQL). Agents can use this to calibrate confidence.
4. **Search on global** — KC search is indexed globally; regional search returns zero results. This is a known API behavior.
5. **Project number, not ID** — Glossary term entry names embed the project number. The setup scripts resolve this automatically via Resource Manager.
6. **Scoped search** — Global search returns every glossary and entry group the caller can see, including other projects'. `kc_search` keeps only results from `fashion-cymbal-glossary` and `fashion-cymbal-ontology`.

## API Gotchas (found while building this demo)

These are real issues encountered during development and verified against the live KC API:

- **Glossaries are not entry groups** — create them with `BusinessGlossaryServiceClient` (`create_glossary`, `create_glossary_term`). Each term is mirrored as a catalog entry in `@dataplex`; there is no `glossary-term` entry type to create entries with.
- **Glossary term entry names embed project NUMBER, not project ID** — `projects/{NUMBER}/locations/{REGION}/entryGroups/@dataplex/entries/projects/{NUMBER}/locations/{REGION}/glossaries/{GLOSSARY}/terms/{TERM}`. `GlossaryTerm.name` uses the project ID, so build the entry name from the term ID.
- **Entry links are their own resource** — `CatalogServiceClient.create_entry_link` in the source entry's group (`@dataplex` for term↔term), with link type `projects/dataplex-types/locations/global/entryLinkTypes/{synonym|related}`
- **SYNONYM/RELATED are undirected** — create one link, not two; both references are `UNSPECIFIED`. Only DEFINITION uses SOURCE/TARGET.
- **Delete links before terms, terms before the glossary**
- **Every entry needs an entry type** — the OKF entries use the custom `okf-concept` type, created by `04_push_okf_to_kc.py`
- **Custom FQNs need the `custom:` prefix** — e.g. `custom:okf.metrics-return-rate`; `okf:...` is rejected
- **`overview` is a system aspect type** — `projects/dataplex-types/locations/global/aspectTypes/overview`, written under key `dataplex-types.global.overview`
- **Aspect data is a plain struct** — write `{"tier": "SILVER"}`, not JSON-encoded strings (readers would get `"\"SILVER\""` back)
- **Update path: `aspect_keys` on the request object** — NOT as a kwarg to `update_entry()`. Passing as kwarg silently no-ops.
- **`lookup_entry` omits aspect data by default** — pass `view=EntryView.CUSTOM` with `aspect_types`
- **Search only works from global location** — Regional search returns empty results, and global results span other projects, so filter them
- **API normalizes aspect keys** — `dataplex-types.global.overview` becomes `{SYSTEM_PROJECT_NUMBER}.global.overview` on read
- **Errors can be masked** — throttling sometimes surfaces as `ValueError: Code in Status proto (INVALID_ARGUMENT) doesn't match status code (RESOURCE_EXHAUSTED)`; use `transport="rest"` to see the real message. A missing entry often comes back as 403, not 404.
