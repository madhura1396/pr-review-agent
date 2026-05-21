from langgraph.graph import StateGraph, START, END

from graph.state import PRReviewState
from agents.orchestrator import orchestrator
from agents.security import security_agent
from agents.performance import performance_agent
from agents.style import style_agent
from agents.critic import critic
from agents.reporter import reporter, post_to_github


def route_after_orchestrator(state: PRReviewState) -> str:
    if state.get("error") is not None:
        return "end"
    return "continue"


def build_graph() -> StateGraph:
    graph = StateGraph(PRReviewState)

    graph.add_node("orchestrator", orchestrator)
    graph.add_node("security_agent", security_agent)
    graph.add_node("performance_agent", performance_agent)
    graph.add_node("style_agent", style_agent)
    graph.add_node("critic", critic)
    graph.add_node("reporter", reporter)
    graph.add_node("post_to_github", post_to_github)

    graph.add_edge(START, "orchestrator")
    graph.add_conditional_edges(
        "orchestrator",
        route_after_orchestrator,
        {
            "end": END,
            "continue": ["security_agent", "performance_agent", "style_agent"],
        },
    )
    graph.add_edge("security_agent", "critic")
    graph.add_edge("performance_agent", "critic")
    graph.add_edge("style_agent", "critic")
    graph.add_edge("critic", "reporter")
    graph.add_edge("reporter", "post_to_github")
    graph.add_edge("post_to_github", END)

    return graph.compile()
