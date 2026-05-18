import os
import sys

from dotenv import load_dotenv

load_dotenv()

os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGSMITH_PROJECT", "pr-review-agent")
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGSMITH_API_KEY")

from graph.workflow import build_graph


def main():

    if len(sys.argv) < 2:
        print("Usage: python main.py <github-pr-url>")
        print("Example: python main.py https://github.com/owner/repo/pull/123")
        sys.exit(1)

    pr_url = sys.argv[1]

    graph = build_graph()

    initial_state = {
        "pr_url": pr_url,
        "diff_chunks": [],
        "security_findings": [],
        "performance_findings": [],
        "style_findings": [],
        "critic_output": [],
        "final_report": "",
        "error": None,
    }

    output = graph.invoke(initial_state)

    if output.get("error"):
        print(f"Error: {output['error']}")
        sys.exit(1)

    print(output.get("final_report", "No report generated."))


if __name__ == "__main__":
    main()
