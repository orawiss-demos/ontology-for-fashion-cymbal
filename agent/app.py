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
Runnable entrypoint for the Fashion Cymbal Ontology Agent.

Usage:
    python -m agent.app

Accepts questions from stdin, runs the 3-stage workflow
(search → context → grounding transcription → execute),
and prints results.
"""

import asyncio
import sys

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from agent.ontology_agent import create_agent


async def main():
    agent = create_agent()
    session_service = InMemorySessionService()
    runner = Runner(
        agent=agent,
        app_name="fashion-cymbal-ontology",
        session_service=session_service,
    )

    # Create a session
    session = await session_service.create_session(
        app_name="fashion-cymbal-ontology",
        user_id="demo-user",
    )

    print("Fashion Cymbal Ontology Agent")
    print("=" * 40)
    print("Ask questions about Fashion Cymbal metrics, entities, and rules.")
    print("Type 'quit' or Ctrl+C to exit.\n")

    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not question:
            continue
        if question.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        # Build the user message
        user_content = genai_types.Content(
            role="user",
            parts=[genai_types.Part(text=question)],
        )

        print("\nAgent: ", end="", flush=True)

        # Run the agent and collect the final response
        async for event in runner.run_async(
            user_id="demo-user",
            session_id=session.id,
            new_message=user_content,
        ):
            # Print final agent text responses
            if event.is_final_response() and event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        print(part.text)

        print()


if __name__ == "__main__":
    asyncio.run(main())
