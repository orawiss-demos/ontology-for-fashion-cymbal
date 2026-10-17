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
Fashion Cymbal Ontology Agent — ADK LlmAgent with KC + BQ tools.

Architecture (follows Architectural Principle #5: one job, one tool, per agent):
  - Single LlmAgent with three tools:
    1. kc_search  — discover KC entries
    2. kc_context — fetch full context for an entry
    3. bq_execute — run read-only SQL against BigQuery

  - The LlmAgent reasons through the 3-stage workflow itself:
    search → context → grounding transcription → execute

  - Tools are structurally restricted at construction time
    (Principle #1: structural enforcement over instructional).

For multi-agent orchestration (Demo 2), this agent becomes a specialist
sub-agent behind an ADK router. The tools stay the same — only the
wiring changes.
"""

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from agent.tools.kc_search import kc_search
from agent.tools.kc_context import kc_context
from agent.tools.bq_execute import bq_execute
from agent.prompts.system_prompt import get_system_prompt
from config import GCP_PROJECT, BQ_DATASET, DEFAULT_MODEL


def create_agent() -> LlmAgent:
    """Create and return the ontology agent."""
    return LlmAgent(
        name="fashion_cymbal_ontology_agent",
        model=DEFAULT_MODEL,
        instruction=get_system_prompt(GCP_PROJECT, BQ_DATASET),
        tools=[
            FunctionTool(kc_search),
            FunctionTool(kc_context),
            FunctionTool(bq_execute),
        ],
        description=(
            "Answers business analytics questions about Fashion Cymbal "
            "by grounding SQL in Knowledge Catalog context (glossary terms + OKF entries)."
        ),
    )
