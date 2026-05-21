import os
import sys

from dotenv import load_dotenv

load_dotenv()

os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGSMITH_PROJECT", "pr-review-agent")
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGSMITH_API_KEY")

from langgraph.types import Command

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

    config = {"configurable": {"thread_id": pr_url}}
    output = graph.invoke(initial_state, config=config)

    # Handle human-in-the-loop interrupt for CRITICAL findings
    while hasattr(output, "__interrupt__") or (
        isinstance(output, dict) and "__interrupt__" in output
    ):
        interrupt_data = (
            output["__interrupt__"][0].value
            if isinstance(output, dict)
            else output.__interrupt__[0].value
        )
        print("\n*** CRITICAL FINDINGS REQUIRE APPROVAL ***")
        for finding in interrupt_data.get("findings", []):
            print(f"  {finding}")
        answer = input("\nPost this review to GitHub? [y/N]: ").strip().lower()
        if answer != "y":
            print("Review aborted by user.")
            sys.exit(0)
        output = graph.invoke(Command(resume=True), config=config)

    if output.get("error"):
        print(f"Error: {output['error']}")
        sys.exit(1)

    print(output.get("final_report", "No report generated."))


if __name__ == "__main__":
    main()
