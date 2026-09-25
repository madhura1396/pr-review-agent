import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase

from agents.critic import critic
from evals.goldens import CRITIC_GOLDENS, critic_state
from evals.metrics import reconciliation_metric


def test_critic_short_circuits_when_no_agent_found_anything():
    """No findings means no LLM call at all — so this one needs no Groq key."""
    state = critic_state(CRITIC_GOLDENS[0])
    state["security_findings"] = []
    state["style_findings"] = []
    state["performance_findings"] = []

    assert critic(state) == {"critic_output": []}


@pytest.mark.llm
@pytest.mark.parametrize("golden", CRITIC_GOLDENS, ids=lambda g: g.name)
def test_critic_reconciles_reviewer_findings(golden, judge):
    findings = critic(critic_state(golden))["critic_output"]
    assert findings, f"critic returned nothing for {golden.name}"

    output = "\n".join(findings)

    reviewer_input = (
        f"Security findings:\n{chr(10).join(golden.security_findings) or '(none)'}\n\n"
        f"Performance findings:\n{chr(10).join(golden.performance_findings) or '(none)'}\n\n"
        f"Style findings:\n{chr(10).join(golden.style_findings) or '(none)'}"
    )

    assert_test(
        LLMTestCase(
            input=reviewer_input,
            actual_output=output,
            expected_output=golden.expected_output,
        ),
        [reconciliation_metric(judge)],
        run_async=False,
    )
