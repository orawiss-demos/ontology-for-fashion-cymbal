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
Tests for the Fashion Cymbal Ontology Agent.

Three test categories:
  1. Unit tests — tool functions in isolation (mock GCP clients)
  2. OKF bundle tests — validate frontmatter parsing and completeness
  3. Integration tests — in test_integration.py (requires GCP credentials, skipped by default)

Run:
  pytest tests/                          # unit + OKF tests only
  pytest tests/ --run-integration        # include integration tests (needs GCP)
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import frontmatter

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import OKF_BUNDLE_DIR


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def golden_questions():
    path = Path(__file__).parent / "golden_questions.json"
    with open(path) as f:
        return json.load(f)


@pytest.fixture
def okf_files():
    """All non-index OKF markdown files."""
    return [f for f in sorted(OKF_BUNDLE_DIR.rglob("*.md")) if f.name != "index.md"]


# ── OKF Bundle Tests ───────────────────────────────────────────────────────

class TestOKFBundle:
    """Validate the OKF markdown files are well-formed."""

    def test_okf_bundle_has_files(self, okf_files):
        """Bundle should have at least 10 non-index files."""
        assert len(okf_files) >= 10, f"Only {len(okf_files)} OKF files found"

    def test_all_files_have_required_frontmatter(self, okf_files):
        """Every OKF file must have 'type' in frontmatter (OKF spec requirement)."""
        for f in okf_files:
            post = frontmatter.load(f)
            assert "type" in post.metadata, f"{f.name} missing required 'type' field"

    def test_all_files_have_title(self, okf_files):
        """Every OKF file should have a title."""
        for f in okf_files:
            post = frontmatter.load(f)
            assert post.metadata.get("title"), f"{f.name} missing 'title'"

    def test_all_files_have_body(self, okf_files):
        """Every OKF file should have non-empty body content."""
        for f in okf_files:
            post = frontmatter.load(f)
            assert len(post.content.strip()) > 100, f"{f.name} body too short"

    def test_metrics_have_sql_blocks(self, okf_files):
        """All metric files should contain at least one SQL block."""
        metrics = [f for f in okf_files if "metrics/" in str(f)]
        assert len(metrics) == 4, "Expected 4 metric files"
        for f in metrics:
            content = f.read_text()
            assert "```sql" in content, f"{f.name} missing SQL block"

    def test_metrics_have_exclusions_section(self, okf_files):
        """All metrics should document their exclusion rules."""
        metrics = [f for f in okf_files if "metrics/" in str(f)]
        for f in metrics:
            content = f.read_text()
            assert "exclusion" in content.lower(), f"{f.name} missing exclusions section"

    def test_rules_have_sql_blocks(self, okf_files):
        """All rule files should contain SQL blocks."""
        rules = [f for f in okf_files if "rules/" in str(f)]
        assert len(rules) >= 3, "Expected at least 3 rule files"
        for f in rules:
            content = f.read_text()
            assert "```sql" in content, f"{f.name} missing SQL block"

    def test_wikilinks_resolve(self, okf_files):
        """All [[wikilink]] targets should have corresponding files."""
        import re
        file_stems = {f.stem for f in okf_files}
        for f in okf_files:
            content = f.read_text()
            links = re.findall(r"\[\[([^\]]+)\]\]", content)
            for link in links:
                assert link in file_stems, (
                    f"{f.name} links to [[{link}]] but no {link}.md exists"
                )

    def test_frontmatter_status_values(self, okf_files):
        """Status should be one of: draft, active, deprecated."""
        valid = {"draft", "active", "deprecated"}
        for f in okf_files:
            post = frontmatter.load(f)
            status = post.metadata.get("status")
            if status:
                assert status in valid, f"{f.name}: invalid status '{status}'"


# ── Tool Unit Tests ─────────────────────────────────────────────────────────

class TestBQExecute:
    """Test bq_execute safety checks (without GCP connection)."""

    def test_rejects_ddl(self):
        from agent.tools.bq_execute import bq_execute
        result = bq_execute("DROP TABLE foo")
        assert "error" in result
        assert "Only SELECT" in result["error"]

    def test_rejects_dml(self):
        from agent.tools.bq_execute import bq_execute
        result = bq_execute("INSERT INTO foo VALUES (1)")
        assert "error" in result

    def test_allows_select(self):
        """SELECT should pass safety check (will fail on connection, not safety)."""
        from agent.tools.bq_execute import bq_execute
        # This will fail because no BQ connection, but should NOT fail on safety
        result = bq_execute("SELECT 1 AS test")
        # Either succeeds or fails on connection, not on safety
        if "error" in result:
            assert "Only SELECT" not in result["error"]

    def test_allows_with_cte(self):
        """WITH ... SELECT should pass safety check."""
        from agent.tools.bq_execute import bq_execute
        result = bq_execute("WITH cte AS (SELECT 1) SELECT * FROM cte")
        if "error" in result:
            assert "Only SELECT" not in result["error"]


# ── Golden Question Validation ──────────────────────────────────────────────

class TestGoldenQuestions:
    """Validate the golden questions file structure."""

    def test_golden_questions_exist(self, golden_questions):
        assert len(golden_questions) >= 5

    def test_all_have_required_fields(self, golden_questions):
        required = {"id", "question", "expected_behavior", "grounding_sources", "category"}
        for q in golden_questions:
            missing = required - set(q.keys())
            assert not missing, f"Question {q.get('id', '?')} missing: {missing}"

    def test_categories_are_valid(self, golden_questions):
        valid = {"metric_with_filter", "metric_with_dimension", "explanation",
                 "metric_with_channel", "cross_entry_grounding"}
        for q in golden_questions:
            assert q["category"] in valid, f"Invalid category: {q['category']}"

    def test_grounding_sources_have_okf_files(self, golden_questions, okf_files):
        """Every grounding source should map to an actual OKF file."""
        file_stems = {f.stem for f in okf_files}
        for q in golden_questions:
            for source in q["grounding_sources"]:
                assert source in file_stems, (
                    f"Question {q['id']}: grounding source '{source}' has no OKF file"
                )
