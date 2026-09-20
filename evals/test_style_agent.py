import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from agents.style import style_agent
from evals.checks import assert_finding_format, assert_severities_valid
from evals.goldens import STYLE_GOLDENS, as_state
from evals.metrics import detection_metric

pytestmark = pytest.mark.llm


@pytest.mark.parametrize("golden", STYLE_GOLDENS, ids=lambda g: g.name)
def test_style_agent_detects_planted_quality_issue(golden, judge):
    findings = style_agent(as_state(golden))["style_findings"]
    assert findings, f"style agent reported nothing for {golden.name}"

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
