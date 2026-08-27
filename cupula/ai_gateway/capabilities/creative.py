from typing import Any

from cupula.core.logger import get_logger
from cupula.ai_gateway.capabilities.base import CapabilityAgent
from cupula.ai_gateway.gateway import AIGateway

logger = get_logger("capability.creative")


class CreativeAgent(CapabilityAgent):
    """Agente especializado em tarefas criativas.

    Capabilities:
    - Geração de imagens (DALL-E, Stable Diffusion)
    - Criação de conteúdo (textos, scripts, copies)
    - Design de interfaces
    - Storytelling e narrativas
    - Branding e identidade visual
    """

    def __init__(self, gateway: AIGateway):
        super().__init__(
            agent_id="capability-creative",
            gateway=gateway,
            capabilities=["dall-e-3", "gpt4-text", "claude-text"],
        )

    async def generate_image(
        self,
        prompt: str,
        style: str = "natural",
        size: str = "1024x1024",
        quality: str = "hd",
        variations: int = 1,
    ) -> dict[str, Any]:
        """Gera imagem a partir de descrição textual."""
        enhanced_prompt = self._enhance_image_prompt(prompt, style)

        results = []
        for i in range(min(variations, 4)):
            result = await self.process_request(
                capability_id="dall-e-3",
                input_data={"text": enhanced_prompt},
                parameters={"size": size, "quality": quality},
            )
            results.append(result)

        return {
            "success": all(r.get("success", False) for r in results),
            "images": results,
            "prompt_used": enhanced_prompt,
        }

    def _enhance_image_prompt(self, prompt: str, style: str) -> str:
        style_suffixes = {
            "natural": ", photorealistic, high quality, detailed",
            "digital": ", digital art, vibrant colors, modern",
            "minimal": ", minimalist, clean lines, simple",
            "artistic": ", artistic, painterly, creative",
            "professional": ", professional, corporate, polished",
            "cartoon": ", cartoon style, colorful, fun",
        }

        return prompt + style_suffixes.get(style, "")

    async def create_copy(
        self,
        product: str,
        audience: str,
        tone: str = "professional",
        format_type: str = "social_media",
        platform: str = "instagram",
    ) -> dict[str, Any]:
        """Cria texto de marketing/copywriting."""
        prompt = (
            f"Crie conteúdo para: {product}\n"
            f"Público-alvo: {audience}\n"
            f"Tom: {tone}\n"
            f"Formato: {format_type}\n"
            f"Plataforma: {platform}\n\n"
            "Gere:\n"
            "- Título chamativo\n"
            "- Corpo do texto\n"
            "- Call to action\n"
            "- Hashtags relevantes"
        )

        return await self.generate_text(prompt, "gpt4-text")

    async def brainstorm(
        self,
        topic: str,
        count: int = 10,
        constraints: list[str] | None = None,
    ) -> dict[str, Any]:
        """Gera ideias criativas sobre um tema."""
        prompt = (
            f"Gere {count} ideias criativas sobre: {topic}\n\n"
            "Para cada ideia, forneça:\n"
            "- Título\n"
            "- Descrição breve\n"
            "- Potencial de impacto (1-10)\n"
            "- Facilidade de implementação (1-10)"
        )

        if constraints:
            prompt += f"\nRestrições: {', '.join(constraints)}"

        return await self.generate_text(prompt, "claude-text")

    async def design_ui_concept(
        self,
        app_description: str,
        target_audience: str,
        style_preferences: str = "",
    ) -> dict[str, Any]:
        """Cria conceito de design de UI."""
        prompt = (
            f"Crie um conceito de design para: {app_description}\n"
            f"Público: {target_audience}\n\n"
            "Especifique:\n"
            "- Paleta de cores (hex)\n"
            "- Tipografia recomendada\n"
            "- Layout principal\n"
            "- Componentes-chave\n"
            "- Fluxo do usuário"
        )

        if style_preferences:
            prompt += f"\nPreferências de estilo: {style_preferences}"

        concept_text = await self.generate_text(prompt, "claude-text")

        image_prompt = (
            f"UI design concept for: {app_description}. "
            f"Modern, clean interface. "
            f"{style_preferences}"
        )

        image_result = await self.process_request(
            capability_id="dall-e-3",
            input_data={"text": image_prompt},
            parameters={"size": "1024x1024"},
        )

        return {
            "concept": concept_text,
            "visual": image_result,
        }

    async def create_narrative(
        self,
        theme: str,
        characters: list[str] | None = None,
        style: str = "engaging",
        length: str = "medium",
    ) -> dict[str, Any]:
        """Cria narrativa/história."""
        length_map = {
            "short": "300-500 palavras",
            "medium": "800-1200 palavras",
            "long": "2000-3000 palavras",
        }

        prompt = (
            f"Crie uma narrativa sobre: {theme}\n"
            f"Tom: {style}\n"
            f"Tamanho: {length_map.get(length, 'medium')}\n"
        )

        if characters:
            prompt += f"Personagens: {', '.join(characters)}\n"

        prompt += (
            "\nElementos:\n"
            "- Gancho inicial forte\n"
            "- Desenvolvimento envolvente\n"
            "- Clímax impactante\n"
            "- Conclusão memorável"
        )

        return await self.generate_text(prompt, "claude-text")

    async def generate_brand_identity(
        self,
        company_name: str,
        industry: str,
        values: list[str] | None = None,
        target_audience: str = "",
    ) -> dict[str, Any]:
        """Gera conceito de identidade de marca."""
        prompt = (
            f"Crie identidade visual para: {company_name}\n"
            f"Indústria: {industry}\n"
        )

        if values:
            prompt += f"Valores: {', '.join(values)}\n"
        if target_audience:
            prompt += f"Público: {target_audience}\n"

        prompt += (
            "\nInclua:\n"
            "- Nome da marca (se aplicável)\n"
            "- Conceito visual\n"
            "- Paleta de cores (3-5 cores com hex)\n"
            "- Tipografia\n"
            "- Personalidade da marca\n"
            "- Diretrizes de uso"
        )

        return await self.generate_text(prompt, "claude-text")

    async def handle_message(self, message) -> dict | None:
        payload = message.payload
        if payload.get("type") != "creative_request":
            return None

        request_type = payload.get("request_type", "generate")

        if request_type == "image":
            return await self.generate_image(
                payload.get("prompt", ""),
                style=payload.get("style", "natural"),
            )
        elif request_type == "copy":
            return await self.create_copy(
                payload.get("product", ""),
                payload.get("audience", ""),
                tone=payload.get("tone", "professional"),
            )
        elif request_type == "brainstorm":
            return await self.brainstorm(
                payload.get("topic", ""),
                count=payload.get("count", 10),
            )
        elif request_type == "ui_concept":
            return await self.design_ui_concept(
                payload.get("app_description", ""),
                payload.get("target_audience", ""),
            )
        elif request_type == "narrative":
            return await self.create_narrative(
                payload.get("theme", ""),
                characters=payload.get("characters"),
            )
        elif request_type == "brand":
            return await self.generate_brand_identity(
                payload.get("company_name", ""),
                payload.get("industry", ""),
                values=payload.get("values"),
            )

        return None
