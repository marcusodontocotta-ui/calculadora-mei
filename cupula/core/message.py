from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import uuid


class AgentRole(Enum):
    SENTINEL = "sentinel"
    NEXUS = "nexus"
    VORTEX = "vortex"
    APOLO = "apolo"
    CUSTOM = "custom"


class Verdict(Enum):
    APPROVED = "APROVADO"
    REJECTED = "REJEITADO"
    CONDITIONAL = "CONDICIONAL"
    REVISION = "REVISAO"


class EventType(Enum):
    AGENT_REGISTERED = "agent.registered"
    AGENT_UNREGISTERED = "agent.unregistered"
    AGENT_HEARTBEAT = "agent.heartbeat"
    AGENT_BUSY = "agent.busy"
    AGENT_IDLE = "agent.idle"

    DECISION_REQUESTED = "decision.requested"
    DECISION_ANALYZING = "decision.analyzing"
    DECISION_RESPONSE = "decision.response"
    DECISION_COMPLETED = "decision.completed"
    DECISION_FAILED = "decision.failed"

    TEAM_FORMED = "team.formed"
    TEAM_DISBANDED = "team.disbanded"

    SANDBOX_EXECUTE = "sandbox.execute"
    SANDBOX_RESULT = "sandbox.result"


class AgentStatus(Enum):
    OFFLINE = "offline"
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"


@dataclass
class Message:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    event: EventType = EventType.AGENT_HEARTBEAT
    sender: str = ""
    content: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class DecisionRequest:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    title: str = ""
    description: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    constraints: list[str] = field(default_factory=list)
    required_roles: list[str] = field(default_factory=list)
    priority: int = 5
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class DecisionResponse:
    request_id: str = ""
    agent_id: str = ""
    agent_role: str = ""
    verdict: str = ""
    reasoning: str = ""
    risks: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    confidence: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class AgentMetadata:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    name: str = ""
    role: str = ""
    tags: list[str] = field(default_factory=list)
    status: AgentStatus = AgentStatus.OFFLINE
    capabilities: list[str] = field(default_factory=list)
    max_concurrent: int = 1
    current_load: int = 0
    registered_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_heartbeat: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
