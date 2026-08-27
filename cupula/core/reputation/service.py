import json
import time
from dataclasses import dataclass, field
from typing import Any

import redis.asyncio as aioredis

from cupula.core.logger import get_logger

logger = get_logger("reputation")


@dataclass
class AgentScore:
    agent_id: str
    accuracy: float = 0.5
    response_time_avg_ms: float = 0.0
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    nack_count: int = 0
    uptime_ratio: float = 1.0
    consistency_score: float = 0.5
    overall_score: float = 0.5
    last_updated: float = field(default_factory=time.time)
    history: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "accuracy": round(self.accuracy, 4),
            "response_time_avg_ms": round(self.response_time_avg_ms, 2),
            "total_tasks": self.total_tasks,
            "successful_tasks": self.successful_tasks,
            "failed_tasks": self.failed_tasks,
            "nack_count": self.nack_count,
            "uptime_ratio": round(self.uptime_ratio, 4),
            "consistency_score": round(self.consistency_score, 4),
            "overall_score": round(self.overall_score, 4),
            "last_updated": self.last_updated,
        }


class ReputationService:
    """Sistema de reputação para milhares de agentes.

    Cada agente recebe um score baseado em:
    - Acurácia (acerto nas decisões)
    - Tempo de resposta
    - Taxa de sucesso/falha
    - Uptime
    - Consistência ao longo do tempo

    O score influencia o peso do voto do agente nas decisões.
    """

    SCORES_PREFIX = "cupula:rep:"
    HISTORY_PREFIX = "cupula:rep:history:"
    LEADERBOARD_KEY = "cupula:rep:leaderboard"

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._redis: aioredis.Redis | None = None

    async def connect(self):
        self._redis = aioredis.from_url(
            self.redis_url,
            decode_responses=True,
            max_connections=30,
        )
        await self._redis.ping()
        logger.info("ReputationService conectado")

    async def disconnect(self):
        if self._redis:
            await self._redis.close()

    async def get_score(self, agent_id: str) -> AgentScore:
        data = await self._redis.get(f"{self.SCORES_PREFIX}{agent_id}")
        if data:
            d = json.loads(data)
            return AgentScore(**d)
        return AgentScore(agent_id=agent_id)

    async def update_score(
        self,
        agent_id: str,
        success: bool,
        response_time_ms: float = 0.0,
        confidence: float = 0.5,
    ):
        score = await self.get_score(agent_id)
        score.total_tasks += 1
        score.last_updated = time.time()

        if success:
            score.successful_tasks += 1
            score.accuracy = self._ewma(score.accuracy, 1.0, alpha=0.3)
        else:
            score.failed_tasks += 1
            score.nack_count += 1
            score.accuracy = self._ewma(score.accuracy, 0.0, alpha=0.3)

        if response_time_ms > 0:
            if score.response_time_avg_ms == 0:
                score.response_time_avg_ms = response_time_ms
            else:
                score.response_time_avg_ms = self._ewma(
                    score.response_time_avg_ms, response_time_ms, alpha=0.2
                )

        score.overall_score = self._calculate_overall(score)

        score.history.append({
            "timestamp": time.time(),
            "success": success,
            "response_time_ms": response_time_ms,
            "accuracy": score.accuracy,
            "overall": score.overall_score,
        })
        if len(score.history) > 100:
            score.history = score.history[-100:]

        await self._save_score(score)
        await self._update_leaderboard(agent_id, score.overall_score)

        logger.debug(
            f"Score atualizado [{agent_id}]: {score.overall_score:.3f} "
            f"(accuracy={score.accuracy:.3f}, tasks={score.total_tasks})"
        )

    def _ewma(self, current: float, new: float, alpha: float = 0.3) -> float:
        return alpha * new + (1 - alpha) * current

    def _calculate_overall(self, score: AgentScore) -> float:
        weights = {
            "accuracy": 0.35,
            "response_time": 0.15,
            "success_rate": 0.25,
            "uptime": 0.15,
            "consistency": 0.10,
        }

        accuracy_score = score.accuracy

        rt_score = max(0, 1.0 - (score.response_time_avg_ms / 10000))

        if score.total_tasks > 0:
            success_rate = score.successful_tasks / score.total_tasks
        else:
            success_rate = 0.5

        uptime_score = score.uptime_ratio

        if len(score.history) >= 5:
            recent_scores = [h["overall"] for h in score.history[-10:]]
            mean = sum(recent_scores) / len(recent_scores)
            variance = sum((s - mean) ** 2 for s in recent_scores) / len(recent_scores)
            consistency = max(0, 1.0 - variance)
        else:
            consistency = 0.5

        overall = (
            weights["accuracy"] * accuracy_score
            + weights["response_time"] * rt_score
            + weights["success_rate"] * success_rate
            + weights["uptime"] * uptime_score
            + weights["consistency"] * consistency
        )

        return max(0.0, min(1.0, overall))

    async def _save_score(self, score: AgentScore):
        data = json.dumps({
            "agent_id": score.agent_id,
            "accuracy": score.accuracy,
            "response_time_avg_ms": score.response_time_avg_ms,
            "total_tasks": score.total_tasks,
            "successful_tasks": score.successful_tasks,
            "failed_tasks": score.failed_tasks,
            "nack_count": score.nack_count,
            "uptime_ratio": score.uptime_ratio,
            "consistency_score": score.consistency_score,
            "overall_score": score.overall_score,
            "last_updated": score.last_updated,
            "history": score.history[-20:],
        }, ensure_ascii=False)
        await self._redis.set(f"{self.SCORES_PREFIX}{score.agent_id}", data)

    async def _update_leaderboard(self, agent_id: str, score: float):
        await self._redis.zadd(
            self.LEADERBOARD_KEY,
            {agent_id: score},
        )

    async def get_leaderboard(self, top: int = 20) -> list[dict]:
        entries = await self._redis.zrevrange(
            self.LEADERBOARD_KEY, 0, top - 1, withscores=True
        )
        result = []
        for agent_id, score in entries:
            agent_score = await self.get_score(agent_id)
            result.append({
                "rank": len(result) + 1,
                "agent_id": agent_id,
                "overall_score": round(score, 4),
                "accuracy": round(agent_score.accuracy, 4),
                "total_tasks": agent_score.total_tasks,
            })
        return result

    async def get_weight(self, agent_id: str) -> float:
        score = await self.get_score(agent_id)
        return 0.3 + (score.overall_score * 0.7)

    async def get_all_scores(self) -> list[dict]:
        keys = []
        async for key in self._redis.scan_iter(f"{self.SCORES_PREFIX}*"):
            if "history" not in key:
                keys.append(key)

        scores = []
        for key in keys:
            data = await self._redis.get(key)
            if data:
                scores.append(json.loads(data))

        scores.sort(key=lambda x: x.get("overall_score", 0), reverse=True)
        return scores
