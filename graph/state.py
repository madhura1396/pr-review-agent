from typing import Optional

from typing_extensions import TypedDict

from tools.github_tool import DiffChunk


class PRReviewState(TypedDict):
    pr_url: str
    diff_chunks: list[DiffChunk]
    security_findings: list[str]
    performance_findings: list[str]
    style_findings: list[str]
    critic_output: list[str]
    final_report: str
    error: Optional[str]
