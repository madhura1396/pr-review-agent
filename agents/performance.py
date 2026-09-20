from dotenv import load_dotenv

from config import get_llm
from graph.state import PRReviewState
from prompts.agent_prompts import PERFORMANCE_PROMPT

load_dotenv()


def performance_agent(state: PRReviewState) -> dict:
    chunks = state.get("diff_chunks", [])
    if not chunks:
        return {"performance_findings": []}

    findings = []
    for chunk in chunks:
        prompt = PERFORMANCE_PROMPT.format(diff=f"File: {chunk.filename}\n{chunk.diff}")
        response = get_llm().invoke(prompt).content.strip()
        if response != "NO ISSUES FOUND":
            findings.append(response)

    return {"performance_findings": findings}
