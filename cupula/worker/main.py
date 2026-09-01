import asyncio
import json
import signal
import time
from typing import Any

import redis.asyncio as aioredis

from cupula.config.settings import get_settings
from cupula.core.logger import get_logger
from cupula.core.message import EventType, Message

logger = get_logger("worker")


class AutonomousWorker:
    """Worker autônomo que processa eventos e mantém o sistema vivo.

    Três gatilhos:
    1. EVENT DRIVEN — consome Redis Streams e processa decisões pendentes
    2. CRON (30s) — análises periódicas de saúde, métricas, meta-agentes
    3. WEBHOOK — alimentado por endpoints da API (externos/n8n)
    """

    STREAM_KEYS = [
        f"cupula:stream:{e.value}"
        for e in [
            EventType.DECISION_REQUESTED,
            EventType.DECISION_COMPLETED,
            EventType.DECISION_FAILED,
            EventType.AGENT_HEARTBEAT,
            EventType.AGENT_BUSY,
            EventType.AGENT_IDLE,
        ]
    ]

    CRON_INTERVAL = 30
    CLEANUP_INTERVAL = 300

    def __init__(self):
        self.settings = get_settings()
        self._redis: aioredis.Redis | None = None
        self._running = False
        self._start_time = time.time()
        self._events_processed = 0
        self._decisions_triggered = 0
        self._cron_runs = 0
        self._webhooks_received = 0
        self._cupula_app = None
        self.consumer_group = self.settings.REDIS_CONSUMER_GROUP
        self.consumer_name = self.settings.REDIS_CONSUMER_NAME

    async def start(self):
        self._redis = aioredis.from_url(
            self.settings.REDIS_URL, decode_responses=True, max_connections=30,
        )
        await self._redis.ping()
        self._running = True

        self._cupula_app = await self._init_cupula()
        if self._cupula_app:
            logger.info("Cúpula App integrada ao Worker")
        else:
            logger.warning("Cúpula App indisponível — worker opera em modo observação")

        await asyncio.gather(
            self._event_driven_loop(),
            self._cron_loop(),
            self._cleanup_loop(),
        )

    async def stop(self):
        self._running = False
        if self._cupula_app:
            await self._cupula_app.stop()
        if self._redis:
            await self._redis.close()
        logger.info("Worker parado")

    async def _init_cupula(self):
        try:
            from cupula.app import CupulaApp
            from cupula.agents.builtin.sentinel.agent import SentinelAgent
            from cupula.agents.builtin.nexus.agent import NexusAgent
            from cupula.agents.builtin.vortex.agent import VortexAgent
            from cupula.agents.builtin.apolo.agent import ApoloAgent

            app = CupulaApp()
            app.orchestrator.register_agent("sentinel", SentinelAgent(), role="sentinel")
            app.orchestrator.register_agent("nexus", NexusAgent(), role="nexus")
            app.orchestrator.register_agent("vortex", VortexAgent(), role="vortex")
            app.orchestrator.register_agent("apolo", ApoloAgent(), role="apolo")
            await app.start()
            return app
        except Exception as e:
            logger.error(f"Falha ao iniciar CupulaApp no worker: {e}")
            return None

    # ── GATILHO 1: EVENT DRIVEN ───────────────────────────────────────────

    async def _event_driven_loop(self):
        for key in self.STREAM_KEYS:
            try:
                await self._redis.xgroup_create(key, self.consumer_group, "0", mkstream=True)
            except aioredis.ResponseError:
                pass

        logger.info(
            f"Event Driven: monitorando {len(self.STREAM_KEYS)} streams "
            f"(grupo={self.consumer_group}, consumidor={self.consumer_name})"
        )

        while self._running:
            try:
                results = await self._redis.xreadgroup(
                    self.consumer_group, self.consumer_name,
                    {k: ">" for k in self.STREAM_KEYS},
                    count=10, block=1000,
                )
                for stream_name, messages in results:
                    for msg_id, fields in messages:
                        await self._handle_event(stream_name, msg_id, fields)
                        await self._redis.xack(stream_name, self.consumer_group, msg_id)
                        self._events_processed += 1
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erro no event loop: {e}")
                await asyncio.sleep(1)

    async def _handle_event(self, stream: str, msg_id: str, fields: dict):
        event_type = fields.get("event", "")
        sender = fields.get("sender", "unknown")

        if event_type == EventType.DECISION_REQUESTED.value:
            await self._auto_process_decision(fields)

        elif event_type == EventType.AGENT_HEARTBEAT.value:
            agent_id = sender
            if agent_id:
                await self._redis.setex(
                    f"cupula:worker:heartbeat:{agent_id}", 90,
                    json.dumps({"last_seen": time.time()}),
                )

        elif event_type == EventType.DECISION_COMPLETED.value:
            payload = json.loads(fields.get("payload", "{}"))
            await self._redis.incrby("cupula:worker:decisions_completed", 1)
            await self._redis.lpush("cupula:worker:recent_decisions", json.dumps({
                "request_id": payload.get("request_id", ""),
                "verdict": payload.get("verdict", ""),
                "elapsed_ms": payload.get("elapsed_ms", 0),
                "timestamp": time.time(),
            }))
            await self._redis.ltrim("cupula:worker:recent_decisions", 0, 99)

        elif event_type == EventType.DECISION_FAILED.value:
            await self._redis.incrby("cupula:worker:decisions_failed", 1)
            logger.warning(f"Decisão falhou: {fields.get('content', '')}")

        elif event_type in [EventType.AGENT_BUSY.value, EventType.AGENT_IDLE.value]:
            await self._redis.incrby(f"cupula:worker:agent_events:{event_type}", 1)

    async def _auto_process_decision(self, fields: dict):
        if not self._cupula_app:
            return

        try:
            payload = json.loads(fields.get("payload", "{}"))
            title = payload.get("title", fields.get("content", "Decisão automática"))
            description = payload.get("description", title)

            result = await self._cupula_app.process_decision(
                title=title, description=description,
                context=payload.get("context", {}),
                priority=payload.get("priority", 5),
                auto_legal=True,
            )

            self._decisions_triggered += 1
            logger.info(
                f"Decisão processada automaticamente: {title} → {result.get('verdict', 'N/A')}"
            )

            await self._redis.set("cupula:worker:last_auto_decision", json.dumps({
                "title": title,
                "verdict": result.get("verdict", ""),
                "confidence": result.get("confidence", 0),
                "timestamp": time.time(),
            }))

        except Exception as e:
            logger.error(f"Erro ao processar decisão automática: {e}")

    # ── GATILHO 2: CRON 30s ──────────────────────────────────────────────

    async def _cron_loop(self):
        logger.info(f"Cron: análises periódicas a cada {self.CRON_INTERVAL}s")
        while self._running:
            try:
                await asyncio.sleep(self.CRON_INTERVAL)
                self._cron_runs += 1
                await self._run_cron_cycle()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erro no cron cycle: {e}")

    async def _run_cron_cycle(self):
        await self._check_agent_health()
        await self._update_metrics()
        await self._periodic_meta_analysis()
        await self._update_worker_stats()
        logger.debug(f"Cron cycle #{self._cron_runs} completo")

    async def _check_agent_health(self):
        keys = await self._redis.keys("cupula:worker:heartbeat:*")
        timeout = self.settings.AGENT_TIMEOUT
        now = time.time()
        offline = []

        for key in keys:
            data = await self._redis.get(key)
            if data:
                hb = json.loads(data)
                if now - hb.get("last_seen", 0) > timeout:
                    agent_id = key.split(":")[-1]
                    offline.append(agent_id)
                    await self._redis.delete(key)
                    logger.warning(f"Agente offline: {agent_id}")

        if offline:
            await self._redis.set("cupula:worker:offline_agents", json.dumps(offline))

    async def _update_metrics(self):
        uptime = time.time() - self._start_time
        health_score = 1.0

        if self._cupula_app:
            try:
                health = await self._cupula_app.get_health()
                health_score = health.get("score", 0.5)
                await self._redis.set("cupula:worker:system_health", json.dumps(health))
            except Exception:
                health_score = 0.3

        await self._redis.set("cupula:worker:health_score", str(round(health_score, 3)))

    async def _periodic_meta_analysis(self):
        if not self._cupula_app or self._cron_runs % 2 != 0:
            return

        try:
            meta = await self._cupula_app.run_meta_analysis()
            await self._redis.set("cupula:worker:last_meta_analysis", json.dumps({
                "timestamp": time.time(),
                "suggestions": meta.get("self_improver", {}).get("total_suggestions", 0),
                "system_health_score": meta.get("self_improver", {}).get("system_health_score", 0),
            }))
            logger.info("Meta-análise periódica executada")
        except Exception as e:
            logger.error(f"Erro na meta-análise: {e}")

    async def _update_worker_stats(self):
        uptime = time.time() - self._start_time
        stats = {
            "uptime_seconds": round(uptime, 1),
            "events_processed": self._events_processed,
            "decisions_triggered": self._decisions_triggered,
            "cron_runs": self._cron_runs,
            "webhooks_received": self._webhooks_received,
            "running": self._running,
            "timestamp": time.time(),
        }
        await self._redis.set("cupula:worker:stats", json.dumps(stats))

    # ── GATILHO 3: WEBHOOK ───────────────────────────────────────────────

    async def process_webhook(self, payload: dict) -> dict:
        """Chamado pelos endpoints /api/v1/webhook/* da API."""
        self._webhooks_received += 1
        trigger = payload.get("trigger", "generic")

        logger.info(f"Webhook recebido: trigger={trigger}")

        if trigger == "decision":
            return await self._webhook_decision(payload)
        elif trigger == "legal":
            return await self._webhook_legal(payload)
        elif trigger == "status":
            return await self._webhook_status(payload)
        elif trigger == "n8n":
            return await self._webhook_n8n(payload)
        else:
            return await self._webhook_generic(payload)

    async def _webhook_decision(self, payload: dict) -> dict:
        if not self._cupula_app:
            return {"error": "Cúpula App indisponível"}

        result = await self._cupula_app.process_decision(
            title=payload.get("title", "Decisão via webhook"),
            description=payload.get("description", ""),
            context=payload.get("context", {}),
            priority=payload.get("priority", 5),
            auto_legal=payload.get("auto_legal", True),
        )
        self._decisions_triggered += 1
        return result

    async def _webhook_legal(self, payload: dict) -> dict:
        if not self._cupula_app:
            return {"error": "Cúpula App indisponível"}

        return await self._cupula_app.legal_analysis(
            titulo=payload.get("titulo", "Análise via webhook"),
            descricao=payload.get("descricao", ""),
            dominios=payload.get("dominios", []),
            acao_proposta=payload.get("acao_proposta", ""),
        )

    async def _webhook_status(self, payload: dict) -> dict:
        stats = {}
        if self._redis:
            raw = await self._redis.get("cupula:worker:stats")
            if raw:
                stats = json.loads(raw)

        health_score = await self._redis.get("cupula:worker:health_score") if self._redis else "0"

        return {
            "worker": stats,
            "health_score": float(health_score or 0),
            "uptime": round(time.time() - self._start_time, 1),
        }

    async def _webhook_n8n(self, payload: dict) -> dict:
        n8n_action = payload.get("action", "unknown")

        if n8n_action == "trigger_decision":
            return await self._webhook_decision(payload)
        elif n8n_action == "trigger_legal":
            return await self._webhook_legal(payload)
        elif n8n_action == "run_meta":
            if self._cupula_app:
                return await self._cupula_app.run_meta_analysis()
            return {"error": "Cúpula App indisponível"}
        elif n8n_action == "get_report":
            if self._cupula_app:
                return await self._cupula_app.generate_report()
            return {"error": "Cúpula App indisponível"}
        else:
            return await self._webhook_generic(payload)

    async def _webhook_generic(self, payload: dict) -> dict:
        await self._redis.set(
            f"cupula:worker:webhook:{int(time.time())}",
            json.dumps(payload, ensure_ascii=False),
            ex=3600,
        )
        return {"status": "stored", "message": "Webhook genérico armazenado"}

    # ── CLEANUP ───────────────────────────────────────────────────────────

    async def _cleanup_loop(self):
        while self._running:
            try:
                await asyncio.sleep(self.CLEANUP_INTERVAL)
                for prefix in ["cupula:feedback:", "cupula:delivery:"]:
                    keys = await self._redis.keys(f"{prefix}*")
                    for key in keys:
                        ttl = await self._redis.ttl(key)
                        if ttl == -1:
                            await self._redis.expire(key, 3600)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erro no cleanup: {e}")


_worker_instance: AutonomousWorker | None = None


def get_worker() -> AutonomousWorker | None:
    return _worker_instance


def set_worker(w: AutonomousWorker):
    global _worker_instance
    _worker_instance = w


async def main():
    worker = AutonomousWorker()
    set_worker(worker)

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, lambda: asyncio.create_task(worker.stop()))
        except NotImplementedError:
            pass

    logger.info("=== CupulaWorker Autônomo iniciando ===")
    await worker.start()


if __name__ == "__main__":
    asyncio.run(main())
