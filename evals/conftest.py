import os

import pytest
from dotenv import load_dotenv

from evals.groq_judge import GroqJudge

load_dotenv()


@pytest.fixture(scope="session")
def judge() -> GroqJudge:
    """One judge for the whole session — building it opens a Groq client."""
    return GroqJudge()


def pytest_collection_modifyitems(config, items):
    """
    Skip the LLM evals when there is no Groq key.

    CI runs `pytest evals/` on every push, and every test in here calls a live
    model. Without this the suite would fail on any checkout that has no key,
    rather than reporting honestly that it could not run.
    """
    if os.getenv("GROQ_API_KEY"):
        return

    skip_llm = pytest.mark.skip(reason="GROQ_API_KEY not set — LLM evals skipped")
    for item in items:
        if "llm" in item.keywords:
            item.add_marker(skip_llm)
