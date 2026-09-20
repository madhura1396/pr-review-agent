from dotenv import load_dotenv

from config import get_llm
from graph.state import PRReviewState
from prompts.agent_prompts import STYLE_PROMPT

load_dotenv()


def style_agent(state: PRReviewState) -> dict:
    chunks = state.get("diff_chunks", [])
    if not chunks:
        return {"style_findings": []}

    findings = []
    for chunk in chunks:
        prompt = STYLE_PROMPT.format(diff=f"File: {chunk.filename}\n{chunk.diff}")
        response = get_llm().invoke(prompt).content.strip()
        if response != "NO ISSUES FOUND":
            findings.append(response)

    return {"style_findings": findings}
