from graph.state import PRReviewState
from tools.github_tool import fetch_pr_chunks


def orchestrator(state: PRReviewState) -> dict:
    pr_url = state.get("pr_url", "")
    try:
        chunks = fetch_pr_chunks(pr_url)
        return {"diff_chunks": chunks}
    except Exception as e:
        return {"error": str(e), "diff_chunks": []}
