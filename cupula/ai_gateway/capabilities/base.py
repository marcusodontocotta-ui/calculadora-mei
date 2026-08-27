import time
from typing import Any

from cupula.core.logger import get_logger
from cupula.core.message import Message, EventType
from cupula.ai_gateway.gateway import AIGateway, AIRequest, AICapability


class CapabilityAgent:
    """Agente que expõe uma capability de IA para outros agentes.

    Funciona como um "wrapper" que:
    - Registra capabilities disponíveis
    - Processa pedidos de outros agentes
    - Fallback entre modelos/provider
    - Cacheia resultados frequentes
    - Reporta métricas de uso
    """

    def __init__(
        self,
        agent_id: str,
        gateway: AIGateway,
        capabilities: list[str] | None = None,
    ):
        self.agent_id = agent_id
        self.gateway = gateway
        self.capability_ids = capabilities or []
        self._request_count = 0
        self._total_latency = 0.0

    async def process_request(
        self,
        capability_id: str,
        input_data: dict[str, Any],
        parameters: dict[str, Any] | None = None,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        """Processa um pedido de capability de outro agente."""
        start = time.time()

        self._request_count += 1

        request = AIRequest(
            capability_id=capability_id,
            input_data=input_data,
            parameters=parameters or {},
            timeout=timeout,
        )

        response = await self.gateway.execute(request)

        elapsed = (time.time() - start) * 1000
        self._total_latency += elapsed

        if response.error:
            return {
                "success": False,
                "error": response.error,
                "capability_id": capability_id,
                "latency_ms": elapsed,
            }

        return {
            "success": True,
            "output": response.output,
            "provider": response.provider,
            "model": response.model,
            "tokens_used": response.tokens_used,
            "cost": response.cost,
            "latency_ms": elapsed,
        }

    async def analyze_image(
        self,
        image_url: str,
        prompt: str = "Descreva esta imagem em detalhes",
        capability_id: str = "gpt4v-vision",
    ) -> dict[str, Any]:
        """Analisa uma imagem usando IA."""
        return await self.process_request(
            capability_id=capability_id,
            input_data={
                "image_url": image_url,
                "text": prompt,
            },
        )

    async def generate_text(
        self,
        prompt: str,
        capability_id: str = "gpt4-text",
        **params,
    ) -> dict[str, Any]:
        """Gera texto usando IA."""
        return await self.process_request(
            capability_id=capability_id,
            input_data={"text": prompt},
            parameters=params,
        )

    async def generate_code(
        self,
        prompt: str,
        language: str = "python",
        capability_id: str = "gpt4-code",
    ) -> dict[str, Any]:
        """Gera código usando IA."""
        full_prompt = f"Gere código {language} para: {prompt}"
        return await self.process_request(
            capability_id=capability_id,
            input_data={"text": full_prompt},
        )

    async def transcribe_audio(
        self,
        audio_url: str,
        capability_id: str = "whisper-stt",
    ) -> dict[str, Any]:
        """Transcreve áudio usando IA."""
        return await self.process_request(
            capability_id=capability_id,
            input_data={"audio_url": audio_url},
        )

    async def synthesize_speech(
        self,
        text: str,
        voice: str = "default",
        capability_id: str = "elevenlabs-tts",
    ) -> dict[str, Any]:
        """Sintetiza voz a partir de texto."""
        return await self.process_request(
            capability_id=capability_id,
            input_data={"text": text},
            parameters={"voice": voice},
        )

    async def generate_image(
        self,
        prompt: str,
        size: str = "1024x1024",
        capability_id: str = "dall-e-3",
    ) -> dict[str, Any]:
        """Gera imagem a partir de texto."""
        return await self.process_request(
            capability_id=capability_id,
            input_data={"text": prompt},
            parameters={"size": size},
        )

    async def handle_message(self, message: Message) -> dict | None:
        """Processa mensagens de outros agentes que pedem capabilities."""
        if message.event != EventType.AGENT_HEARTBEAT:
            return None

        payload = message.payload
        if payload.get("type") != "capability_request":
            return None

        capability_id = payload.get("capability_id")
        input_data = payload.get("input_data", {})
        parameters = payload.get("parameters", {})

        if capability_id not in self.capability_ids and not self.capability_ids:
            return None

        result = await self.process_request(
            capability_id=capability_id,
            input_data=input_data,
            parameters=parameters,
        )

        return {
            "type": "capability_response",
            "request_id": payload.get("request_id"),
            "agent_id": self.agent_id,
            **result,
        }

    def get_stats(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "request_count": self._request_count,
            "avg_latency_ms": (
                self._total_latency / self._request_count
                if self._request_count > 0
                else 0
            ),
            "capabilities": self.capability_ids,
        }
