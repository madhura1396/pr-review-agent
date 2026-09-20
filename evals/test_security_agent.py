import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from agents.security import security_agent
from evals.checks import assert_finding_format, assert_severities_valid
from evals.goldens import SECURITY_CLEAN_GOLDEN, SECURITY_GOLDENS, as_state
from evals.metrics import absence_metric, detection_metric, scope_metric

pytestmark = pytest.mark.llm


@pytest.mark.parametrize("golden", SECURITY_GOLDENS, ids=lambda g: g.name)
def test_security_agent_detects_planted_vulnerability(golden, judge):
    findings = security_agent(as_state(golden))["security_findings"]
    assert findings, f"security agent reported nothing for {golden.name}"

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


def test_security_agent_stays_quiet_on_clean_diff(judge):
    findings = security_agent(as_state(SECURITY_CLEAN_GOLDEN))["security_findings"]

    assert_test(
        LLMTestCase(
            input=SECURITY_CLEAN_GOLDEN.diff,
            actual_output="\n".join(findings) or "NO ISSUES FOUND",
            expected_output=SECURITY_CLEAN_GOLDEN.expected_output,
        ),
        [absence_metric(judge)],
        run_async=False,
    )


def test_security_agent_does_not_report_style_or_performance(judge):
    golden = SECURITY_GOLDENS[1]  # SQL injection, which also reads as a style smell
    findings = security_agent(as_state(golden))["security_findings"]
    assert findings, "security agent reported nothing, cannot judge scope"

    assert_test(
        LLMTestCase(input=golden.diff, actual_output="\n".join(findings)),
        [
            scope_metric(
                judge,
                domain="security",
                forbidden="code style, naming, docstrings, or runtime performance",
            )
        ],
        run_async=False,
    )
