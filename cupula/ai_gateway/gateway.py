import json
import time
import asyncio
from enum import Enum
from typing import Any
from dataclasses import dataclass, field
from functools import lru_cache

import httpx

from cupula.config.settings import get_settings
from cupula.core.logger import get_logger

logger = get_logger("ai_gateway")


class CapabilityType(Enum):
    TEXT_GENERATION = "text_generation"
    IMAGE_ANALYSIS = "image_analysis"
    IMAGE_GENERATION = "image_generation"
    SPEECH_TO_TEXT = "speech_to_text"
    TEXT_TO_SPEECH = "text_to_speech"
    CODE_GENERATION = "code_generation"
    TRANSLATION = "translation"
    SUMMARIZATION = "summarization"
    EMBEDDINGS = "embeddings"
    SEARCH = "search"
    VIDEO_ANALYSIS = "video_analysis"
    DOCUMENT_ANALYSIS = "document_analysis"
    SCREEN_CAPTURE = "screen_capture"
    REAL_TIME_AUDIO = "real_time_audio"


class ProviderStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"


@dataclass
class AICapability:
    id: str
    name: str
    type: CapabilityType
    provider: str
    model: str
    description: str
    input_types: list[str] = field(default_factory=list)
    output_types: list[str] = field(default_factory=list)
    max_tokens: int = 4096
    cost_per_1k_tokens: float = 0.0
    latency_avg_ms: float = 0.0
    status: ProviderStatus = ProviderStatus.ACTIVE
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AIRequest:
    capability_id: str
    input_data: dict[str, Any]
    parameters: dict[str, Any] = field(default_factory=dict)
    timeout: float = 30.0
    priority: int = 5
    callback_url: str = ""


@dataclass
class AIResponse:
    request_id: str
    capability_id: str
    provider: str
    model: str
    output: Any = None
    error: str = ""
    latency_ms: float = 0.0
    tokens_used: int = 0
    cost: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class AIGateway:
    """Gateway central para acesso a múltiplos provedores de IA.

    Permite que agentes usem capabilities de IAs externas:
    - Análise de imagens (GPT-4V, Claude Vision, Google Vision)
    - Geração de imagens (DALL-E, Stable Diffusion, Midjourney)
    - Speech-to-text (Whisper, Deepgram)
    - Text-to-speech (ElevenLabs, Azure)
    - Code generation (GPT-4, Claude, Gemini)
    - E muito mais

    Funcionalidades:
    - Descoberta automática de capabilities
    - Roteamento inteligente por custo/qualidade/latência
    - Fallback entre provedores
    - Rate limiting por provedor
    - Cache de resultados
    """

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._redis = None
        self._capabilities: dict[str, AICapability] = {}
        self._providers: dict[str, Any] = {}
        self._http_client: httpx.AsyncClient | None = None
        self._cache: dict[str, Any] = {}
        self._rate_limits: dict[str, dict] = {}

    async def connect(self):
        import redis.asyncio as aioredis
        self._redis = aioredis.from_url(
            self.redis_url, decode_responses=True, max_connections=20
        )
        await self._redis.ping()

        self._http_client = httpx.AsyncClient(timeout=60.0)

        self._register_builtin_providers()

        logger.info("AIGateway conectado")

    async def disconnect(self):
        if self._http_client:
            await self._http_client.aclose()
        if self._redis:
            await self._redis.close()

    def _register_builtin_providers(self):
        self._providers = {
            "openai": OpenAIProvider(self),
            "anthropic": AnthropicProvider(self),
            "google": GoogleProvider(self),
            "elevenlabs": ElevenLabsProvider(self),
            "deepgram": DeepgramProvider(self),
            "stability": StabilityProvider(self),
        }

        self._register_default_capabilities()

    def _register_default_capabilities(self):
        defaults = [
            AICapability(
                id="gpt4-text",
                name="GPT-4o Text Generation",
                type=CapabilityType.TEXT_GENERATION,
                provider="openai",
                model="gpt-4o",
                description="Geração de texto de alta qualidade",
                input_types=["text"],
                output_types=["text"],
                max_tokens=128000,
                tags=["text", "reasoning", "analysis"],
            ),
            AICapability(
                id="claude-text",
                name="Claude 3.5 Sonnet",
                type=CapabilityType.TEXT_GENERATION,
                provider="anthropic",
                model="claude-3-5-sonnet-20241022",
                description="Texto excelente com longo contexto",
                input_types=["text"],
                output_types=["text"],
                max_tokens=200000,
                tags=["text", "reasoning", "code"],
            ),
            AICapability(
                id="gpt4v-vision",
                name="GPT-4o Vision",
                type=CapabilityType.IMAGE_ANALYSIS,
                provider="openai",
                model="gpt-4o",
                description="Análise de imagens e screenshots",
                input_types=["image", "text"],
                output_types=["text"],
                tags=["vision", "screenshot", "ui-analysis"],
            ),
            AICapability(
                id="claude-vision",
                name="Claude Vision",
                type=CapabilityType.IMAGE_ANALYSIS,
                provider="anthropic",
                model="claude-3-5-sonnet-20241022",
                description="Análise visual com Claude",
                input_types=["image", "text"],
                output_types=["text"],
                tags=["vision", "analysis"],
            ),
            AICapability(
                id="whisper-stt",
                name="Whisper Large v3",
                type=CapabilityType.SPEECH_TO_TEXT,
                provider="openai",
                model="whisper-1",
                description="Transcrição de áudio de alta qualidade",
                input_types=["audio"],
                output_types=["text"],
                tags=["speech", "transcription"],
            ),
            AICapability(
                id="elevenlabs-tts",
                name="ElevenLabs TTS",
                type=CapabilityType.TEXT_TO_SPEECH,
                provider="elevenlabs",
                model="eleven_multilingual_v2",
                description="Síntese de voz ultra-realista",
                input_types=["text"],
                output_types=["audio"],
                tags=["speech", "voice", "multilingual"],
            ),
            AICapability(
                id="dall-e-3",
                name="DALL-E 3",
                type=CapabilityType.IMAGE_GENERATION,
                provider="openai",
                model="dall-e-3",
                description="Geração de imagens a partir de texto",
                input_types=["text"],
                output_types=["image"],
                tags=["image", "generation", "creative"],
            ),
            AICapability(
                id="gpt4-code",
                name="GPT-4o Code Generation",
                type=CapabilityType.CODE_GENERATION,
                provider="openai",
                model="gpt-4o",
                description="Geração e análise de código",
                input_types=["text"],
                output_types=["text", "code"],
                tags=["code", "programming", "debugging"],
            ),
            AICapability(
                id="gemini-pro",
                name="Gemini 1.5 Pro",
                type=CapabilityType.TEXT_GENERATION,
                provider="google",
                model="gemini-1.5-pro",
                description="Modelo multimodal do Google",
                input_types=["text", "image", "audio", "video"],
                output_types=["text"],
                max_tokens=2000000,
                tags=["multimodal", "text", "analysis"],
            ),
        ]

        for cap in defaults:
            self._capabilities[cap.id] = cap

    async def register_capability(self, capability: AICapability):
        self._capabilities[capability.id] = capability
        logger.info(f"Capability registrada: {capability.id} ({capability.name})")

    async def unregister_capability(self, capability_id: str):
        self._capabilities.pop(capability_id, None)

    async def discover(
        self,
        capability_type: CapabilityType | None = None,
        tags: list[str] | None = None,
        provider: str | None = None,
    ) -> list[AICapability]:
        results = list(self._capabilities.values())

        if capability_type:
            results = [c for c in results if c.type == capability_type]

        if tags:
            results = [
                c for c in results
                if any(tag in c.tags for tag in tags)
            ]

        if provider:
            results = [c for c in results if c.provider == provider]

        return results

    async def execute(self, request: AIRequest) -> AIResponse:
        start_time = time.time()

        capability = self._capabilities.get(request.capability_id)
        if not capability:
            return AIResponse(
                request_id=f"req_{int(time.time())}",
                capability_id=request.capability_id,
                provider="",
                model="",
                error=f"Capability não encontrada: {request.capability_id}",
            )

        provider = self._providers.get(capability.provider)
        if not provider:
            return AIResponse(
                request_id=f"req_{int(time.time())}",
                capability_id=request.capability_id,
                provider=capability.provider,
                model=capability.model,
                error=f"Provider não encontrado: {capability.provider}",
            )

        cache_key = self._get_cache_key(request)
        cached = await self._get_cached(cache_key)
        if cached:
            logger.debug(f"Cache hit para {request.capability_id}")
            return cached

        try:
            response = await provider.execute(capability, request)
            response.latency_ms = (time.time() - start_time) * 1000

            await self._set_cached(cache_key, response, ttl=300)

            await self._log_usage(capability, response)

            return response

        except Exception as e:
            logger.error(f"Erro ao executar {request.capability_id}: {e}")

            fallback = await self._find_fallback(capability)
            if fallback:
                logger.info(f"Tentando fallback: {fallback.id}")
                fallback_request = AIRequest(
                    capability_id=fallback.id,
                    input_data=request.input_data,
                    parameters=request.parameters,
                    timeout=request.timeout,
                )
                return await self.execute(fallback_request)

            return AIResponse(
                request_id=f"req_{int(time.time())}",
                capability_id=request.capability_id,
                provider=capability.provider,
                model=capability.model,
                error=str(e),
                latency_ms=(time.time() - start_time) * 1000,
            )

    async def _find_fallback(self, capability: AICapability) -> AICapability | None:
        alternatives = await self.discover(
            capability_type=capability.type,
            provider=None,
        )
        for alt in alternatives:
            if alt.id != capability.id and alt.status == ProviderStatus.ACTIVE:
                return alt
        return None

    def _get_cache_key(self, request: AIRequest) -> str:
        input_hash = str(hash(json.dumps(request.input_data, sort_keys=True, default=str)))
        return f"ai_cache:{request.capability_id}:{input_hash}"

    async def _get_cached(self, key: str) -> AIResponse | None:
        if self._redis:
            data = await self._redis.get(key)
            if data:
                d = json.loads(data)
                return AIResponse(**d)
        return None

    async def _set_cached(self, key: str, response: AIResponse, ttl: int = 300):
        if self._redis:
            data = json.dumps({
                "request_id": response.request_id,
                "capability_id": response.capability_id,
                "provider": response.provider,
                "model": response.model,
                "output": response.output,
                "error": response.error,
                "latency_ms": response.latency_ms,
                "tokens_used": response.tokens_used,
                "cost": response.cost,
                "metadata": response.metadata,
            }, default=str)
            await self._redis.setex(key, ttl, data)

    async def _log_usage(self, capability: AICapability, response: AIResponse):
        if self._redis:
            entry = {
                "capability_id": capability.id,
                "provider": capability.provider,
                "model": capability.model,
                "latency_ms": response.latency_ms,
                "tokens_used": response.tokens_used,
                "cost": response.cost,
                "success": not bool(response.error),
                "timestamp": time.time(),
            }
            await self._redis.lpush("ai_gateway:usage_log", json.dumps(entry))
            await self._redis.ltrim("ai_gateway:usage_log", 0, 9999)

            await self._redis.hincrby("ai_gateway:stats", "total_requests", 1)
            if response.error:
                await self._redis.hincrby("ai_gateway:stats", "total_errors", 1)
            await self._redis.hincrby(
                "ai_gateway:stats",
                f"requests:{capability.provider}",
                1,
            )

    async def get_stats(self) -> dict:
        stats = {}
        if self._redis:
            raw = await self._redis.hgetall("ai_gateway:stats")
            stats = {k: int(v) for k, v in raw.items()} if raw else {}

        stats["capabilities_count"] = len(self._capabilities)
        stats["providers_count"] = len(self._providers)
        stats["capabilities"] = {
            cap.id: {
                "name": cap.name,
                "type": cap.type.value,
                "provider": cap.provider,
                "status": cap.status.value,
            }
            for cap in self._capabilities.values()
        }

        return stats

    async def get_usage_log(self, limit: int = 50) -> list[dict]:
        if self._redis:
            entries = await self._redis.lrange("ai_gateway:usage_log", 0, limit - 1)
            return [json.loads(e) for e in entries]
        return []


class BaseProvider:
    def __init__(self, gateway: AIGateway):
        self.gateway = gateway
        self._api_key: str = ""

    async def execute(self, capability: AICapability, request: AIRequest) -> AIResponse:
        raise NotImplementedError

    async def _make_request(
        self, method: str, url: str, headers: dict, data: dict | None = None
    ) -> dict:
        if method == "POST":
            resp = await self.gateway._http_client.post(url, json=data, headers=headers)
        else:
            resp = await self.gateway._http_client.get(url, headers=headers)
        resp.raise_for_status()
        return resp.json()


class OpenAIProvider(BaseProvider):
    BASE_URL = "https://api.openai.com/v1"

    async def execute(self, capability: AICapability, request: AIRequest) -> AIResponse:
        import os
        api_key = os.getenv("OPENAI_API_KEY", "")

        if not api_key:
            return AIResponse(
                request_id=f"req_{int(time.time())}",
                capability_id=capability.id,
                provider="openai",
                model=capability.model,
                error="OPENAI_API_KEY não configurada",
            )

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        if capability.type in [CapabilityType.TEXT_GENERATION, CapabilityType.CODE_GENERATION]:
            data = {
                "model": capability.model,
                "messages": [
                    {"role": "user", "content": request.input_data.get("text", "")}
                ],
                "max_tokens": request.parameters.get("max_tokens", 4096),
            }
            result = await self._make_request("POST", f"{self.BASE_URL}/chat/completions", headers, data)

            return AIResponse(
                request_id=f"req_{int(time.time())}",
                capability_id=capability.id,
                provider="openai",
                model=capability.model,
                output=result["choices"][0]["message"]["content"],
                tokens_used=result.get("usage", {}).get("total_tokens", 0),
            )

        elif capability.type == CapabilityType.IMAGE_ANALYSIS:
            data = {
                "model": capability.model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": request.input_data.get("text", "Descreva esta imagem")},
                            {
                                "type": "image_url",
                                "image_url": {"url": request.input_data.get("image_url", "")},
                            },
                        ],
                    }
                ],
            }
            result = await self._make_request("POST", f"{self.BASE_URL}/chat/completions", headers, data)

            return AIResponse(
                request_id=f"req_{int(time.time())}",
                capability_id=capability.id,
                provider="openai",
                model=capability.model,
                output=result["choices"][0]["message"]["content"],
            )

        elif capability.type == CapabilityType.IMAGE_GENERATION:
            data = {
                "model": "dall-e-3",
                "prompt": request.input_data.get("text", ""),
                "n": 1,
                "size": request.parameters.get("size", "1024x1024"),
            }
            result = await self._make_request("POST", f"{self.BASE_URL}/images/generations", headers, data)

            return AIResponse(
                request_id=f"req_{int(time.time())}",
                capability_id=capability.id,
                provider="openai",
                model=capability.model,
                output=result["data"][0]["url"],
            )

        return AIResponse(
            request_id=f"req_{int(time.time())}",
            capability_id=capability.id,
            provider="openai",
            model=capability.model,
            error=f"Tipo não suportado: {capability.type.value}",
        )


class AnthropicProvider(BaseProvider):
    BASE_URL = "https://api.anthropic.com/v1"

    async def execute(self, capability: AICapability, request: AIRequest) -> AIResponse:
        import os
        api_key = os.getenv("ANTHROPIC_API_KEY", "")

        if not api_key:
            return AIResponse(
                request_id=f"req_{int(time.time())}",
                capability_id=capability.id,
                provider="anthropic",
                model=capability.model,
                error="ANTHROPIC_API_KEY não configurada",
            )

        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        data = {
            "model": capability.model,
            "max_tokens": request.parameters.get("max_tokens", 4096),
            "messages": [
                {"role": "user", "content": request.input_data.get("text", "")}
            ],
        }

        result = await self._make_request("POST", f"{self.BASE_URL}/messages", headers, data)

        output = ""
        for block in result.get("content", []):
            if block.get("type") == "text":
                output += block.get("text", "")

        return AIResponse(
            request_id=f"req_{int(time.time())}",
            capability_id=capability.id,
            provider="anthropic",
            model=capability.model,
            output=output,
            tokens_used=result.get("usage", {}).get("input_tokens", 0)
                     + result.get("usage", {}).get("output_tokens", 0),
        )


class GoogleProvider(BaseProvider):
    async def execute(self, capability: AICapability, request: AIRequest) -> AIResponse:
        import os
        api_key = os.getenv("GOOGLE_API_KEY", "")

        if not api_key:
            return AIResponse(
                request_id=f"req_{int(time.time())}",
                capability_id=capability.id,
                provider="google",
                model=capability.model,
                error="GOOGLE_API_KEY não configurada",
            )

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{capability.model}:generateContent?key={api_key}"

        data = {
            "contents": [
                {"parts": [{"text": request.input_data.get("text", "")}]}
            ],
        }

        result = await self._make_request("POST", url, {}, data)

        output = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")

        return AIResponse(
            request_id=f"req_{int(time.time())}",
            capability_id=capability.id,
            provider="google",
            model=capability.model,
            output=output,
        )


class ElevenLabsProvider(BaseProvider):
    async def execute(self, capability: AICapability, request: AIRequest) -> AIResponse:
        import os
        api_key = os.getenv("ELEVENLABS_API_KEY", "")

        if not api_key:
            return AIResponse(
                request_id=f"req_{int(time.time())}",
                capability_id=capability.id,
                provider="elevenlabs",
                model=capability.model,
                error="ELEVENLABS_API_KEY não configurada",
            )

        return AIResponse(
            request_id=f"req_{int(time.time())}",
            capability_id=capability.id,
            provider="elevenlabs",
            model=capability.model,
            output="TTS não implementado aún",
            error="Provider em desenvolvimento",
        )


class DeepgramProvider(BaseProvider):
    async def execute(self, capability: AICapability, request: AIRequest) -> AIResponse:
        return AIResponse(
            request_id=f"req_{int(time.time())}",
            capability_id=capability.id,
            provider="deepgram",
            model=capability.model,
            error="Provider em desenvolvimento",
        )


class StabilityProvider(BaseProvider):
    async def execute(self, capability: AICapability, request: AIRequest) -> AIResponse:
        return AIResponse(
            request_id=f"req_{int(time.time())}",
            capability_id=capability.id,
            provider="stability",
            model=capability.model,
            error="Provider em desenvolvimento",
        )


@lru_cache
def get_ai_gateway() -> AIGateway:
    settings = get_settings()
    return AIGateway(redis_url=settings.REDIS_URL)
