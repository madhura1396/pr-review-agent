import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from agents.performance import performance_agent
from evals.checks import assert_finding_format, assert_severities_valid
from evals.goldens import PERFORMANCE_GOLDENS, as_state
from evals.metrics import detection_metric, scope_metric

pytestmark = pytest.mark.llm


@pytest.mark.parametrize("golden", PERFORMANCE_GOLDENS, ids=lambda g: g.name)
def test_performance_agent_detects_planted_bottleneck(golden, judge):
    findings = performance_agent(as_state(golden))["performance_findings"]
    assert findings, f"performance agent reported nothing for {golden.name}"

    output = "\n".join(findings)
    assert_finding_format(output)
    assert_severities_valid(output)

    assert_test(
        LLMTestCase(
            input=golden.diff,
            actual_output=output,
            expected_output=golden.expected_output,
        ),
        [detection_metric(judge)],
        run_async=False,
    )


def test_performance_agent_does_not_report_security_or_style(judge):
    golden = PERFORMANCE_GOLDENS[0]  # N+1 queries, adjacent to SQL/security territory
    findings = performance_agent(as_state(golden))["performance_findings"]
    assert findings, "performance agent reported nothing, cannot judge scope"

    assert_test(
        LLMTestCase(input=golden.diff, actual_output="\n".join(findings)),
        [
            scope_metric(
                judge,
                domain="performance",
                forbidden="security vulnerabilities, code style, naming, or docstrings",
            )
        ],
        run_async=False,
    )
