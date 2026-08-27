from typing import Any

from cupula.core.logger import get_logger
from cupula.ai_gateway.capabilities.base import CapabilityAgent
from cupula.ai_gateway.gateway import AIGateway

logger = get_logger("capability.code")


class CodeAgent(CapabilityAgent):
    """Agente especializado em código e programação.

    Capabilities:
    - Geração de código em múltiplas linguagens
    - Revisão e refactorização
    - Debug e análise de erros
    - Geração de testes
    - Documentação de código
    - Conversão entre linguagens
    """

    LANGUAGES = [
        "python", "javascript", "typescript", "java", "csharp",
        "go", "rust", "php", "ruby", "swift", "kotlin",
        "sql", "html", "css", "bash", "powershell",
    ]

    def __init__(self, gateway: AIGateway):
        super().__init__(
            agent_id="capability-code",
            gateway=gateway,
            capabilities=["gpt4-code", "claude-text"],
        )

    async def generate_code(
        self,
        description: str,
        language: str = "python",
        framework: str = "",
        style: str = "",
        constraints: list[str] | None = None,
    ) -> dict[str, Any]:
        """Gera código a partir de descrição."""
        prompt = self._build_generation_prompt(
            description, language, framework, style, constraints
        )
        return await self.generate_code_from_prompt(prompt, "gpt4-code")

    def _build_generation_prompt(
        self,
        description: str,
        language: str,
        framework: str,
        style: str,
        constraints: list[str] | None,
    ) -> str:
        parts = [
            f"Gere código {language} para:",
            description,
        ]

        if framework:
            parts.append(f"Framework: {framework}")
        if style:
            parts.append(f"Estilo: {style}")
        if constraints:
            parts.append("Restrições:")
            for c in constraints:
                parts.append(f"  - {c}")

        parts.extend([
            "",
            "Requisitos:",
            "- Código limpo e bem estruturado",
            "- Tratamento de erros adequado",
            "- Type hints (se aplicável)",
            "- Docstrings/comentários quando necessário",
        ])

        return "\n".join(parts)

    async def review_code(
        self,
        code: str,
        language: str = "python",
        focus_areas: list[str] | None = None,
    ) -> dict[str, Any]:
        """Revisa código e sugere melhorias."""
        prompt = (
            f"Revise este código {language} e forneça:\n"
            "1. Problemas encontrados (bugs, security, performance)\n"
            "2. Sugestões de melhoria\n"
            "3. Pontos fortes\n"
            "4. Nota geral (1-10)\n\n"
            f"Código:\n```\n{code}\n```"
        )

        if focus_areas:
            prompt += f"\n\nFoque em: {', '.join(focus_areas)}"

        return await self.generate_text(prompt, "claude-text")

    async def debug_error(
        self,
        code: str,
        error_message: str,
        language: str = "python",
        stack_trace: str = "",
    ) -> dict[str, Any]:
        """Ajuda a debugar erro no código."""
        prompt = (
            f"Este código {language} está gerando erro:\n\n"
            f"Código:\n```\n{code}\n```\n\n"
            f"Erro: {error_message}\n"
        )

        if stack_trace:
            prompt += f"\nStack Trace:\n{stack_trace}\n"

        prompt += (
            "\nForneça:\n"
            "1. Causa raiz do erro\n"
            "2. Correção específica\n"
            "3. Código corrigido\n"
            "4. Como prevenir no futuro"
        )

        return await self.generate_text(prompt, "claude-text")

    async def generate_tests(
        self,
        code: str,
        language: str = "python",
        test_framework: str = "",
        coverage_level: str = "comprehensive",
    ) -> dict[str, Any]:
        """Gera testes para o código."""
        prompt = (
            f"Gere testes {language} para este código:\n\n"
            f"```\n{code}\n```\n\n"
            f"Nível de cobertura: {coverage_level}\n"
        )

        if test_framework:
            prompt += f"Framework de teste: {test_framework}\n"

        prompt += (
            "\nInclua:\n"
            "- Testes unitários\n"
            "- Testes de borda\n"
            "- Testes de erro\n"
            "- Fixtures/setup quando necessário"
        )

        return await self.generate_text(prompt, "claude-text")

    async def convert_language(
        self,
        code: str,
        source_language: str,
        target_language: str,
        preserve_logic: bool = True,
    ) -> dict[str, Any]:
        """Converte código de uma linguagem para outra."""
        prompt = (
            f"Converta este código de {source_language} para {target_language}:\n\n"
            f"```\n{code}\n```\n\n"
            f"Preservar lógica: {'Sim' if preserve_logic else 'Não'}\n\n"
            "Forneça:\n"
            "- Código convertido\n"
            "- Notas sobre diferenças entre as linguagens\n"
            "- Possíveis adaptações necessárias"
        )

        return await self.generate_text(prompt, "claude-text")

    async def document_code(
        self,
        code: str,
        language: str = "python",
        doc_style: str = "google",
    ) -> dict[str, Any]:
        """Gera documentação para o código."""
        prompt = (
            f"Gere documentação completa para este código {language}:\n\n"
            f"```\n{code}\n```\n\n"
            f"Estilo: {doc_style}\n\n"
            "Inclua:\n"
            "- Descrição geral\n"
            "- Parâmetros e tipos\n"
            "- Valores de retorno\n"
            "- Exemplos de uso\n"
            "- Possíveis exceções"
        )

        return await self.generate_text(prompt, "claude-text")

    async def refactor_code(
        self,
        code: str,
        language: str = "python",
        goals: list[str] | None = None,
    ) -> dict[str, Any]:
        """Refatora código para melhor qualidade."""
        prompt = (
            f"Refatore este código {language}:\n\n"
            f"```\n{code}\n```\n\n"
        )

        if goals:
            prompt += f"Objetivos: {', '.join(goals)}\n\n"

        prompt += (
            "Foque em:\n"
            "- Princípios SOLID\n"
            "- Design patterns\n"
            "- Readabilidade\n"
            "- Performance\n"
            "- Manutenibilidade"
        )

        return await self.generate_text(prompt, "claude-text")

    async def handle_message(self, message) -> dict | None:
        payload = message.payload
        if payload.get("type") != "code_request":
            return None

        request_type = payload.get("request_type", "generate")

        if request_type == "generate":
            return await self.generate_code(
                payload.get("description", ""),
                language=payload.get("language", "python"),
                framework=payload.get("framework", ""),
            )
        elif request_type == "review":
            return await self.review_code(
                payload.get("code", ""),
                language=payload.get("language", "python"),
            )
        elif request_type == "debug":
            return await self.debug_error(
                payload.get("code", ""),
                payload.get("error", ""),
                language=payload.get("language", "python"),
            )
        elif request_type == "test":
            return await self.generate_tests(
                payload.get("code", ""),
                language=payload.get("language", "python"),
            )
        elif request_type == "convert":
            return await self.convert_language(
                payload.get("code", ""),
                payload.get("source_lang", ""),
                payload.get("target_lang", ""),
            )
        elif request_type == "document":
            return await self.document_code(
                payload.get("code", ""),
                language=payload.get("language", "python"),
            )
        elif request_type == "refactor":
            return await self.refactor_code(
                payload.get("code", ""),
                language=payload.get("language", "python"),
            )

        return None
