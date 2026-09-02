import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from cupula.config.settings import get_settings
from cupula.core.logger import get_logger
from cupula.app import CupulaApp
from cupula.api.routes.main import router as api_router
from cupula.api.security import require_api_key
from cupula.api.validation import PayloadTooLargeError

logger = get_logger("api.main")

_startup_time = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    cupula = CupulaApp()

    from cupula.agents.builtin.sentinel.agent import SentinelAgent
    from cupula.agents.builtin.nexus.agent import NexusAgent
    from cupula.agents.builtin.vortex.agent import VortexAgent
    from cupula.agents.builtin.apolo.agent import ApoloAgent

    cupula.orchestrator.register_agent("sentinel", SentinelAgent(), role="sentinel")
    cupula.orchestrator.register_agent("nexus", NexusAgent(), role="nexus")
    cupula.orchestrator.register_agent("vortex", VortexAgent(), role="vortex")
    cupula.orchestrator.register_agent("apolo", ApoloAgent(), role="apolo")

    await cupula.start()
    app.state.cupula = cupula
    app.state.start_time = time.time()

    logger.info("Cúpula API iniciada (worker dedicado roda como serviço separado)")
    yield

    await cupula.stop()
    logger.info("Cúpula API encerrada")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="API da Cúpula de Gestão Autônoma - Sistema multi-agente com Setor Jurídico",
        lifespan=lifespan,
    )

    settings_displayed = settings.CUPULA_API_KEY

    @app.get("/api/v1/health")
    async def public_health(req: Request):
        """Health check público (isento de autenticação, sem dados sensíveis)."""
        cupula = req.app.state.cupula
        return await cupula.get_health()

    # Payloads excessivos (L2) são rejeitados com 4xx antes de chegarem aos
    # agentes. Mapeamos a exceção de validação de DTOs para 413 Payload Too Large.
    @app.exception_handler(PayloadTooLargeError)
    async def payload_too_large_handler(req: Request, exc: PayloadTooLargeError):
        logger.warning(f"Payload rejeitado ({exc.detail})")
        return JSONResponse(
            status_code=413,
            content={"detail": str(exc.detail or "Payload demasiado grande")},
        )

    # Todas as rotas /api/v1/* (exceto /health) exigem X-API-Key.
    app.include_router(
        api_router,
        prefix="/api/v1",
        dependencies=[Depends(require_api_key)],
    )

    if not settings_displayed:
        logger.warning(
            "CUPULA_API_KEY não configurada — rotas protegidas responderão 503 até a env var ser definida"
        )

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "cupula.api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=False,
        log_level="info",
    )
