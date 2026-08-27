import time
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from cupula.config.settings import get_settings
from cupula.core.logger import get_logger
from cupula.app import CupulaApp
from cupula.api.routes.main import router as api_router
from cupula.worker.main import AutonomousWorker, set_worker

logger = get_logger("api.main")

_startup_time = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
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

    worker = AutonomousWorker()
    set_worker(worker)
    worker._cupula_app = cupula
    worker._redis = cupula.orchestrator.bus._redis
    worker._running = True

    asyncio.create_task(_run_worker_background(worker))

    logger.info(f"Cúpula API + Worker rodando em {settings.API_HOST}:{settings.API_PORT}")
    yield

    worker._running = False
    await cupula.stop()
    logger.info("Cúpula API encerrada")


async def _run_worker_background(worker: AutonomousWorker):
    try:
        for key in worker.STREAM_KEYS:
            try:
                await worker._redis.xgroup_create(key, "worker-group", "0", mkstream=True)
            except Exception:
                pass

        logger.info("Worker background: streams inicializados")

        while worker._running:
            try:
                await asyncio.sleep(worker.CRON_INTERVAL)
                if not worker._running:
                    break
                worker._cron_runs += 1
                await worker._check_agent_health()
                await worker._update_metrics()
                await worker._update_worker_stats()

                if worker._cron_runs % 2 == 0:
                    try:
                        await worker._periodic_meta_analysis()
                    except Exception:
                        pass

                logger.debug(f"Worker cron cycle #{worker._cron_runs}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erro no worker cron: {e}")
                await asyncio.sleep(5)
    except Exception as e:
        logger.error(f"Worker background falhou: {e}")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="API da Cúpula de Gestão Autônoma - Sistema multi-agente com Setor Jurídico",
        lifespan=lifespan,
    )

    app.include_router(api_router, prefix="/api/v1")

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
