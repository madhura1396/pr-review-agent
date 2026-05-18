import os
import re

from dotenv import load_dotenv
from github import Github
from langchain_groq import ChatGroq

from graph.state import PRReviewState
from prompts.agent_prompts import REPORTER_PROMPT

load_dotenv()

_llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
)


def reporter(state: PRReviewState) -> dict:
    critic_output = state.get("critic_output", [])

    if not critic_output:
        return {"final_report": "No issues found."}

    prompt = REPORTER_PROMPT.format(critic_output="\n".join(critic_output))
    response = _llm.invoke(prompt).content.strip()

    return {"final_report": response}


def post_to_github(state: PRReviewState) -> dict:
    pr_url = state.get("pr_url", "")
    final_report = state.get("final_report", "")
    critic_output = state.get("critic_output", [])

    if os.getenv("DRY_RUN", "").lower() == "true":
        print("\n=== DRY RUN: Final Report ===")
        print(final_report)
        return {"error": None}

    try:
        match = re.search(r"github\.com/([^/]+)/([^/]+)/pull/(\d+)", pr_url)
        if not match:
            return {"error": f"Could not parse PR URL: {pr_url}"}

        owner, repo_name, pr_number = match.group(1), match.group(2), int(match.group(3))
        repo = Github(os.getenv("GITHUB_TOKEN")).get_repo(f"{owner}/{repo_name}")
        pr = repo.get_pull(pr_number)

        pr.create_issue_comment(final_report)

        return {"error": None}

    except Exception as e:
        return {"error": str(e)}
