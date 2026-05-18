import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq

from graph.state import PRReviewState
from prompts.agent_prompts import STYLE_PROMPT

load_dotenv()

_llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
)


def style_agent(state: PRReviewState) -> dict:
    chunks = state.get("diff_chunks", [])
    if not chunks:
        return {"style_findings": []}

    findings = []
    for chunk in chunks:
        prompt = STYLE_PROMPT.format(diff=f"File: {chunk.filename}\n{chunk.diff}")
        response = _llm.invoke(prompt).content.strip()
        if response != "NO ISSUES FOUND":
            findings.append(response)

    return {"style_findings": findings}
