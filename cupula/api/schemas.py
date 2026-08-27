import time
from typing import Any
from dataclasses import dataclass, field


@dataclass
class DecisionRequestDTO:
    title: str
    description: str
    context: dict[str, Any] = field(default_factory=dict)
    constraints: list[str] = field(default_factory=list)
    priority: int = 5
    auto_legal: bool = True


@dataclass
class LegalAnalysisRequestDTO:
    titulo: str
    descricao: str
    dominios: list[str] = field(default_factory=list)
    acao_proposta: str = ""
    dados_envolvidos: list[str] = field(default_factory=list)


@dataclass
class DecisionResponseDTO:
    request_id: str
    title: str
    verdict: str
    confidence: float
    responses_count: int
    agent_responses: list[dict] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    legal_analysis: dict | None = None
    elapsed_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)


@dataclass
class HealthResponseDTO:
    status: str
    version: str
    uptime_seconds: float
    redis: str
    agents_registered: int
    legal_db_laws: int
    legal_analyses: int


# ── AI Capability DTOs ────────────────────────────────────────────────────────


@dataclass
class CodeGenerateDTO:
    description: str
    language: str = "python"
    framework: str = ""
    style: str = ""
    constraints: list[str] = field(default_factory=list)


@dataclass
class CodeReviewDTO:
    code: str
    language: str = "python"


@dataclass
class CodeDebugDTO:
    code: str
    error: str
    language: str = "python"


@dataclass
class ImageGenerateDTO:
    prompt: str
    style: str = "natural"
    size: str = "1024x1024"
    quality: str = "hd"
    variations: int = 1


@dataclass
class CopyDTO:
    brief: str
    product: str
    audience: str


@dataclass
class BrainstormDTO:
    topic: str
    context: str = ""
    count: int = 5


@dataclass
class VisionScreenshotDTO:
    image_url: str
    context: str = ""


@dataclass
class VisionOCRequestDTO:
    image_url: str


@dataclass
class VisionCompareDTO:
    image_url_a: str
    image_url_b: str


# ── Webhook DTOs ──────────────────────────────────────────────────────────────


@dataclass
class WebhookRequestDTO:
    trigger: str = "generic"
    title: str = ""
    description: str = ""
    context: dict[str, Any] = field(default_factory=dict)
    constraints: list[str] = field(default_factory=list)
    priority: int = 5
    auto_legal: bool = True
    titulo: str = ""
    dominios: list[str] = field(default_factory=list)
    acao_proposta: str = ""
    action: str = ""
