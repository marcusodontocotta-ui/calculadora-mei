import base64
from typing import Any

from cupula.core.logger import get_logger
from cupula.ai_gateway.capabilities.base import CapabilityAgent
from cupula.ai_gateway.gateway import AIGateway

logger = get_logger("capability.vision")


class VisionAgent(CapabilityAgent):
    """Agente especializado em análise visual.

    Capabilities:
    - Análise de screenshots de programas
    - Verificação de UI/UX
    - OCR em imagens
    - Descrição de desenhos e diagramas
    - Comparação visual entre versões
    - Detecção de erros visuais
    """

    VISION_MODELS = {
        "gpt4v": "gpt4v-vision",
        "claude": "claude-vision",
        "gemini": "gemini-pro",
    }

    def __init__(self, gateway: AIGateway, default_model: str = "gpt4v"):
        super().__init__(
            agent_id="capability-vision",
            gateway=gateway,
            capabilities=["gpt4v-vision", "claude-vision", "gemini-pro"],
        )
        self.default_model = default_model

    async def analyze_screenshot(
        self,
        image_url: str,
        context: str = "",
        specific_checks: list[str] | None = None,
    ) -> dict[str, Any]:
        """Analisa screenshot de programa."""
        prompt = self._build_screenshot_prompt(context, specific_checks)
        return await self.analyze_image(image_url, prompt)

    def _build_screenshot_prompt(
        self, context: str, checks: list[str] | None
    ) -> str:
        parts = [
            "Analise este screenshot de programa/aplicação.",
            "Forneça:",
            "- Descrição do que está sendo exibido",
            "- Estado atual da interface",
            "- Possíveis erros ou problemas visuais",
            "- Sugestões de melhoria de UX",
        ]

        if context:
            parts.append(f"\nContexto: {context}")

        if checks:
            parts.append("\nChecks específicos solicitados:")
            for check in checks:
                parts.append(f"  - {check}")

        return "\n".join(parts)

    async def analyze_ui_design(
        self,
        image_url: str,
        design_system: str = "",
        brand_guidelines: str = "",
    ) -> dict[str, Any]:
        """Analisa design de UI."""
        prompt = (
            "Analise este design de interface (UI/UX). "
            "Avalie: hierarquia visual, acessibilidade, consistência, "
            "uso de espaço, tipografia, cores e padroções de interação."
        )

        if design_system:
            prompt += f"\nDesign System: {design_system}"

        if brand_guidelines:
            prompt += f"\nDiretrizes de marca: {brand_guidelines}"

        return await self.analyze_image(image_url, prompt)

    async def compare_versions(
        self,
        old_image_url: str,
        new_image_url: str,
        description: str = "",
    ) -> dict[str, Any]:
        """Compara duas versões de uma interface."""
        prompt = (
            "Compare estas duas versões de uma interface. "
            "Identifique: mudanças visuais, melhorias, possíveis regressões, "
            "e qual versão parece mais adequada."
        )

        if description:
            prompt += f"\nDescrição das mudanças: {description}"

        result_old = await self.analyze_image(old_image_url, "Descreva esta versão antiga em detalhes")
        result_new = await self.analyze_image(new_image_url, "Descreva esta versão nova em detalhes")

        return {
            "old_analysis": result_old,
            "new_analysis": result_new,
            "comparison": "Análise comparativa concluída",
        }

    async def ocr_image(
        self,
        image_url: str,
        language: str = "pt-br",
    ) -> dict[str, Any]:
        """Extrai texto de imagem (OCR via IA)."""
        prompt = (
            f"Extraia todo o texto visível nesta imagem. "
            f"Idioma: {language}. "
            f"Retorne o texto formatado preservando a estrutura original."
        )
        return await self.analyze_image(image_url, prompt)

    async def detect_errors(
        self,
        image_url: str,
        error_types: list[str] | None = None,
    ) -> dict[str, Any]:
        """Detecta erros visuais em interface."""
        prompt = (
            "Analise esta imagem procurando erros visuais como: "
            "elementos sobrepostos, texto ilegível, cores inadequadas, "
            "alinhamento incorreto, botões quebrados, layouts desordenados."
        )

        if error_types:
            prompt += f"\nTipos específicos de erros para detectar: {', '.join(error_types)}"

        return await self.analyze_image(image_url, prompt)

    async def describe_diagram(
        self,
        image_url: str,
        diagram_type: str = "auto",
    ) -> dict[str, Any]:
        """Descreve diagrama ou fluxograma."""
        prompt = (
            "Analise este diagrama/fluxograma. "
            "Identifique: elementos, conexões, fluxo lógico, "
            "possíveis erros de lógica e sugestões de melhoria."
        )

        if diagram_type != "auto":
            prompt += f"\nTipo de diagrama: {diagram_type}"

        return await self.analyze_image(image_url, prompt)

    async def handle_message(self, message) -> dict | None:
        payload = message.payload
        if payload.get("type") == "vision_request":
            request_type = payload.get("request_type", "analyze")
            image_url = payload.get("image_url", "")

            if request_type == "screenshot":
                return await self.analyze_screenshot(
                    image_url,
                    context=payload.get("context", ""),
                )
            elif request_type == "ui_design":
                return await self.analyze_ui_design(image_url)
            elif request_type == "ocr":
                return await self.ocr_image(image_url)
            elif request_type == "detect_errors":
                return await self.detect_errors(image_url)
            elif request_type == "describe_diagram":
                return await self.describe_diagram(image_url)
            else:
                return await self.analyze_image(
                    image_url,
                    payload.get("prompt", "Descreva esta imagem"),
                )

        return None
