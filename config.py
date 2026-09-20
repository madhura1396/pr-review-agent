import os

from dotenv import load_dotenv

load_dotenv()

# Groq retired llama-3.3-70b-versatile, the model this project was built on;
# requests for it now come back 404 model_not_found. Keeping the name in one
# place means the next retirement is a one-line change instead of a five-file
# hunt. Override with GROQ_MODEL to try a different model without editing code.
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

# The eval judge is deliberately a different model than the one under test.
# Scoring gpt-oss output with gpt-oss is self-grading, and a model tends to be
# lenient about its own work.
EVAL_JUDGE_MODEL = os.getenv("EVAL_JUDGE_MODEL", "qwen/qwen3.8-27b")

_llm = None


def get_llm():
    """
    Return the shared ChatGroq client, building it on first use.

    Deliberately lazy: constructing ChatGroq requires GROQ_API_KEY, and doing
    that at import time means simply importing an agent module fails without a
    key. Pytest imports every agent module during collection, so an eager
    client turns a missing key into a collection error instead of a clean skip.
    """
    global _llm
    if _llm is None:
        from langchain_groq import ChatGroq

        _llm = ChatGroq(model=GROQ_MODEL, api_key=os.getenv("GROQ_API_KEY"))
    return _llm
