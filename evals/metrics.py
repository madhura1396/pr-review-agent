"""
GEval metrics used by the agent evals.

Every metric is constructed with an explicit `evaluation_steps` list rather than
a free-text `criteria`. That is deliberate: when only `criteria` is given,
DeepEval spends an extra LLM call asking the judge to invent the steps, and in
this version it asks for them under a schema that types `steps` as a bare string
instead of a list. Supplying the steps skips both problems.

Scores come back from the judge on a 0-10 scale and DeepEval divides by 10, so
the thresholds below are fractions of 1.
"""

from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCaseParams

from evals.groq_judge import GroqJudge

INPUT = LLMTestCaseParams.INPUT
ACTUAL = LLMTestCaseParams.ACTUAL_OUTPUT
EXPECTED = LLMTestCaseParams.EXPECTED_OUTPUT


def detection_metric(judge: GroqJudge, threshold: float = 0.7) -> GEval:
    """Did the agent actually find the defect that was planted in the diff?"""
    return GEval(
        name="Planted Defect Detection",
        evaluation_params=[INPUT, ACTUAL, EXPECTED],
        evaluation_steps=[
            "Read Expected Output. It describes one specific defect that was "
            "deliberately planted in the code diff shown in Input.",
            "Decide whether Actual Output contains a finding that describes that "
            "same underlying defect. Judge the substance of the finding, not its "
            "wording, severity label, or line number.",
            "Award a high score only if the planted defect is clearly identified.",
            "Award the lowest score if Actual Output is 'NO ISSUES FOUND', is "
            "empty, or describes only unrelated problems.",
            "Do not penalize Actual Output for reporting additional findings "
            "beyond the planted defect.",
        ],
        model=judge,
        threshold=threshold,
        async_mode=False,
    )


def absence_metric(judge: GroqJudge, threshold: float = 0.7) -> GEval:
    """Did the agent stay quiet on a diff that has nothing wrong with it?"""
    return GEval(
        name="No False Alarm",
        evaluation_params=[INPUT, ACTUAL, EXPECTED],
        evaluation_steps=[
            "Read Expected Output. It explains why the diff in Input is clean and "
            "contains no defect of the kind this reviewer looks for.",
            "Award the highest score if Actual Output reports no issues at all, "
            "for example the exact text 'NO ISSUES FOUND'.",
            "Award a low score if Actual Output invents a defect that the diff "
            "does not actually contain.",
            "Penalize more heavily the higher the claimed severity: a fabricated "
            "CRITICAL finding is worse than a fabricated SUGGESTION.",
        ],
        model=judge,
        threshold=threshold,
        async_mode=False,
    )


def scope_metric(judge: GroqJudge, domain: str, forbidden: str, threshold: float = 0.7) -> GEval:
    """
    Did the agent stay in its lane?

    Each agent prompt tells the model to review one domain only. This catches the
    common failure where a specialist drifts into the other agents' territory and
    floods the critic with duplicates.
    """
    return GEval(
        name=f"{domain.title()} Reviewer Scope",
        evaluation_params=[INPUT, ACTUAL],
        evaluation_steps=[
            f"Actual Output is the report of a reviewer whose only job is to find "
            f"{domain} problems in the diff shown in Input.",
            f"Check every finding in Actual Output. A finding is in scope if it is "
            f"genuinely a {domain} concern.",
            f"A finding is out of scope if it is really about {forbidden}.",
            "Award the highest score if every finding is in scope. Lower the score "
            "in proportion to how many findings stray out of scope.",
        ],
        model=judge,
        threshold=threshold,
        async_mode=False,
    )


def reconciliation_metric(judge: GroqJudge, threshold: float = 0.7) -> GEval:
    """Did the critic dedupe, keep the highest severity, and rank correctly?"""
    return GEval(
        name="Critic Reconciliation",
        evaluation_params=[INPUT, ACTUAL, EXPECTED],
        evaluation_steps=[
            "Input holds findings from three independent reviewers. Actual Output "
            "is the critic's single reconciled list. Expected Output describes "
            "what a correct reconciliation looks like.",
            "Check that every distinct issue described in Expected Output appears "
            "in Actual Output, and that no distinct issue was dropped.",
            "Check that issues Expected Output calls duplicates appear exactly "
            "once in Actual Output, carrying the highest severity any reviewer "
            "assigned them.",
            "Check that the findings are ordered CRITICAL first, then WARNING, "
            "then SUGGESTION.",
            "Award a high score only when deduplication, severity, and ordering "
            "are all correct.",
        ],
        model=judge,
        threshold=threshold,
        async_mode=False,
    )
