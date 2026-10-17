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
Integration tests against the deployed demo resources.

Requires GCP credentials (ADC) and setup steps 01–05 to have run.
Skipped unless --run-integration is passed (see conftest.py).

  1. Knowledge Catalog — glossary terms, OKF entries, search scoping + dedup
  2. BigQuery — demo tables exist and have rows
  3. Agent loop — each golden question runs end to end; the SQL the agent
     executed must contain every must_include_in_sql snippet

Run:
  pytest tests/ --run-integration
"""

import asyncio
import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import GCP_REGION, GLOSSARY_ID, ENTRY_GROUP_ID, BQ_TABLES

pytestmark = pytest.mark.integration

GOLDEN = json.loads((Path(__file__).parent / "golden_questions.json").read_text())


def _term_entry(term_id: str) -> str:
    from agent.tools.kc_context import PROJECT_NUMBER
    return (
        f"projects/{PROJECT_NUMBER}/locations/{GCP_REGION}/entryGroups/@dataplex/entries"
        f"/projects/{PROJECT_NUMBER}/locations/{GCP_REGION}/glossaries/{GLOSSARY_ID}/terms/{term_id}"
    )


def _okf_entry(entry_id: str) -> str:
    # Search returns entry names with the project NUMBER, so build them the same way
    from agent.tools.kc_context import PROJECT_NUMBER
    return f"projects/{PROJECT_NUMBER}/locations/{GCP_REGION}/entryGroups/{ENTRY_GROUP_ID}/entries/{entry_id}"


def _normalize(text: str) -> str:
    """Lowercase, drop markdown emphasis and table aliases (oi.col → col), collapse whitespace."""
    text = text.lower().replace("*", "").replace("<>", "!=")
    text = re.sub(r"\b[a-z_][a-z0-9_]*\.(?=[a-z_])", "", text)
    return re.sub(r"\s+", " ", text)


# ── Knowledge Catalog ───────────────────────────────────────────────────────

class TestKnowledgeCatalog:

    def test_search_prefers_glossary_and_stays_in_scope(self):
        from agent.tools.kc_search import kc_search
        results = kc_search("return rate")
        names = [r["name"] for r in results]
        assert _term_entry("return-rate") in names
        # Guard against a vacuous "not in" below: OKF results must be present at all
        assert any(f"/entryGroups/{ENTRY_GROUP_ID}/entries/" in n for n in names), names
        # Glossary wins the dedup: the OKF copy of the same metric is dropped
        assert _okf_entry("metrics-return-rate") not in names
        # Nothing from other glossaries, entry groups or projects
        for name in names:
            assert f"/glossaries/{GLOSSARY_ID}/terms/" in name or f"/entryGroups/{ENTRY_GROUP_ID}/entries/" in name, name

    def test_search_keeps_okf_only_rules(self):
        from agent.tools.kc_search import kc_search
        names = [r["name"] for r in kc_search("outlet classification")]
        assert _okf_entry("rules-outlet-vs-fullprice") in names

    @pytest.mark.parametrize("term_id", ["return-rate", "sell-through-rate", "average-basket-value", "gross-margin"])
    def test_metric_terms_are_enriched(self, term_id):
        from agent.tools.kc_context import kc_context
        ctx = kc_context(_term_entry(term_id))
        assert "error" not in ctx, ctx
        assert ctx["trust_tier"] == "CERTIFIED_GOLD"
        assert ctx["verified_query"] and "select" in ctx["verified_query"].lower()
        assert ctx["overview"] and len(ctx["overview"]) > 100

    @pytest.mark.parametrize("term_id", ["product-category", "brand", "sales-channel", "collection-season"])
    def test_entity_terms_are_enriched(self, term_id):
        from agent.tools.kc_context import kc_context
        ctx = kc_context(_term_entry(term_id))
        assert "error" not in ctx, ctx
        assert ctx["trust_tier"] == "SILVER"
        assert ctx["overview"] and len(ctx["overview"]) > 100

    def test_okf_entry_has_signals(self):
        from agent.tools.kc_context import kc_context
        ctx = kc_context(_okf_entry("rules-return-window-policy"))
        assert "error" not in ctx, ctx
        assert ctx["okf_signals"]["status"] == "active"
        assert ctx["overview"] and "DISCLAIMER" not in ctx["overview"]


# ── BigQuery ────────────────────────────────────────────────────────────────

class TestBigQuery:

    @pytest.mark.parametrize("table", sorted(BQ_TABLES))
    def test_table_has_rows(self, table):
        from agent.tools.bq_execute import bq_execute
        result = bq_execute(f"SELECT COUNT(*) AS n FROM `{BQ_TABLES[table]}`")
        assert "error" not in result, result
        assert result["rows"][0]["n"] > 0


# ── Agent loop ──────────────────────────────────────────────────────────────

async def _ask(question: str) -> tuple[str, list[str], list[str]]:
    """Run one question through the agent. Returns (answer, tools called, SQL executed)."""
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types as genai_types
    from agent.ontology_agent import create_agent

    session_service = InMemorySessionService()
    runner = Runner(agent=create_agent(), app_name="fashion-cymbal-ontology-test", session_service=session_service)
    session = await session_service.create_session(app_name="fashion-cymbal-ontology-test", user_id="test")

    answer, tools, sql = [], [], []
    async for event in runner.run_async(
        user_id="test",
        session_id=session.id,
        new_message=genai_types.Content(role="user", parts=[genai_types.Part(text=question)]),
    ):
        for call in event.get_function_calls():
            tools.append(call.name)
            if call.name == "bq_execute":
                sql.append((call.args or {}).get("sql", ""))
        if event.is_final_response() and event.content and event.content.parts:
            answer.extend(part.text for part in event.content.parts if part.text)
    return "\n".join(answer), tools, sql


@pytest.mark.parametrize("q", GOLDEN, ids=[f"q{q['id']}-{q['category']}" for q in GOLDEN])
def test_golden_question(q):
    answer, tools, sql = asyncio.run(_ask(q["question"]))

    assert answer.strip(), "agent returned no answer"
    assert "kc_search" in tools and "kc_context" in tools, f"agent skipped KC grounding: {tools}"

    if q.get("must_include_in_sql"):
        executed = _normalize("\n".join(sql))
        assert executed, f"agent never ran bq_execute: {tools}"
        missing = [s for s in q["must_include_in_sql"] if _normalize(s) not in executed]
        assert not missing, f"SQL missing {missing}\n--- executed SQL ---\n" + "\n".join(sql)

    if q.get("must_include_in_response"):
        response = _normalize(answer)
        missing = [s for s in q["must_include_in_response"] if _normalize(s) not in response]
        assert not missing, f"answer missing {missing}\n--- answer ---\n{answer}"
