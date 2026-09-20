from dotenv import load_dotenv

from config import get_llm
from graph.state import PRReviewState
from prompts.agent_prompts import SECURITY_PROMPT

load_dotenv()


def security_agent(state: PRReviewState) -> dict:
    chunks = state.get("diff_chunks", [])
    if not chunks:
        return {"security_findings": []}

    findings = []
    for chunk in chunks:
        prompt = SECURITY_PROMPT.format(diff=f"File: {chunk.filename}\n{chunk.diff}")
        response = get_llm().invoke(prompt).content.strip()
        if response != "NO ISSUES FOUND":
            findings.append(response)

    return {"security_findings": findings}
