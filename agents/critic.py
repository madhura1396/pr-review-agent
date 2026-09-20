from dotenv import load_dotenv

from config import get_llm
from graph.state import PRReviewState
from prompts.agent_prompts import CRITIC_PROMPT

load_dotenv()


def critic(state: PRReviewState) -> dict:
    security = state.get("security_findings", [])
    performance = state.get("performance_findings", [])
    style = state.get("style_findings", [])

    if not security and not performance and not style:
        return {"critic_output": []}

    prompt = CRITIC_PROMPT.format(
        security_findings="\n".join(security),
        performance_findings="\n".join(performance),
        style_findings="\n".join(style),
    )

    response = get_llm().invoke(prompt).content.strip()
    findings_list = [line for line in response.split("\n") if line.strip()]

    return {"critic_output": findings_list}
