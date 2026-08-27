import asyncio
import pytest
from cupula.core.message import Message, EventType, DecisionRequest, DecisionResponse, AgentRole


def test_message_creation():
    msg = Message(
        event=EventType.DECISION_REQUESTED,
        sender="test-agent",
        content="test content",
    )
    assert msg.sender == "test-agent"
    assert msg.event == EventType.DECISION_REQUESTED
    assert msg.content == "test content"
    assert msg.id


def test_decision_request():
    req = DecisionRequest(
        title="Test Decision",
        description="A test decision",
        priority=7,
    )
    assert req.title == "Test Decision"
    assert req.priority == 7
    assert req.id


def test_decision_response():
    resp = DecisionResponse(
        request_id="test-123",
        agent_id="sentinel",
        agent_role="sentinel",
        verdict="APROVADO",
        reasoning="Looks good",
        risks=["risk1"],
        recommendations=["rec1"],
        confidence=0.85,
    )
    assert resp.verdict == "APROVADO"
    assert resp.confidence == 0.85
    assert len(resp.risks) == 1


def test_event_types():
    assert EventType.DECISION_REQUESTED.value == "decision.requested"
    assert EventType.AGENT_HEARTBEAT.value == "agent.heartbeat"
    assert EventType.DECISION_COMPLETED.value == "decision.completed"
