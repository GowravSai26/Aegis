from unittest.mock import MagicMock, patch

from agents.orchestrator import MAX_REVISIONS, aegis_graph
from agents.state import AegisState, DisputeVerdict


def _llm_returning(content: str) -> MagicMock:
    llm = MagicMock()
    llm.invoke.return_value.content = content
    return llm


def make_state() -> AegisState:
    return AegisState(
        chargeback_id="CB-LOOP",
        merchant_id="MERCH-001",
        transaction_id="TXN-001",
        amount=450.0,
        reason_code="13.1",
        reason_description="Item not received",
        dispute_deadline="2024-04-01",
        dispute_category=None,
        urgency=None,
        required_evidence=None,
        evidence_collected=None,
        evidence_strength=None,
        missing_evidence=None,
        verdict=None,
        winability_score=None,
        strategy_reasoning=None,
        recommended_arguments=None,
        dispute_response_draft=None,
        document_path=None,
        revision_count=0,
        review_passed=None,
        review_feedback=None,
        escalation_reason=None,
        agent_trace=[],
        error=None,
    )


@patch("agents.reviewer_agent.ChatGroq")
@patch("agents.writer_agent.ChatGroq")
@patch("agents.strategy_agent.ChatGroq")
@patch("agents.evidence_collector_agent.ChatGroq")
@patch("agents.intake_agent.ChatGroq")
def test_failed_reviews_escalate_instead_of_looping(intake, evidence, strategy, writer, reviewer):
    intake.return_value = _llm_returning('{"dispute_category": "not_received", "urgency": "HIGH"}')
    evidence.return_value = _llm_returning('{"evidence_strength": 0.9, "missing_evidence": []}')
    strategy.return_value = _llm_returning(
        '{"verdict": "FIGHT", "winability_score": 0.8, "strategy_reasoning": "x", "recommended_arguments": ["a"]}'
    )
    writer.return_value = _llm_returning("EXECUTIVE SUMMARY\nDraft.")
    reviewer.return_value = _llm_returning('{"review_passed": false, "feedback": "Needs work"}')

    result = aegis_graph.invoke(make_state())

    drafts = [t for t in result["agent_trace"] if t.startswith("WriterAgent")]
    assert len(drafts) == MAX_REVISIONS + 1
    assert result["verdict"] == DisputeVerdict.ESCALATE
    assert result["agent_trace"][-1] == "Orchestrator: ESCALATED TO HUMAN"
