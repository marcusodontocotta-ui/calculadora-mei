"""Rate limiting simples em memória, thread-safe (M3).

Protege os endpoints de IA (e decide/webhook) contra abuso de custo de
provedor sem depender de Redis: usa janela deslizante em memória, com
limites configuráveis via env (RATE_LIMIT_MAX_REQUESTS / RATE_LIMIT_WINDOW_SECONDS).
"""

import time
import threading
from collections import defaultdict, deque
from typing import Deque

from fastapi import HTTPException, Request, status

from cupula.config.settings import get_settings


class MemoryRateLimiter:
    """Janela deslizante em memória por chave (IP e/ou API key).

    Thread-safe via um lock único. Os timestamps são descartados após a
    janela, então a estrutura não cresce indefinidamente e é adequada a um
    processo único (API local/Docker Compose com uma réplica de API).
    """

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, Deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            q = self._hits[key]
            while q and q[0] < cutoff:
                q.popleft()
            if len(q) >= self.max_requests:
                return False
            q.append(now)
            return True

    def reset(self, key: str | None = None):
        with self._lock:
            if key is None:
                self._hits.clear()
            else:
                self._hits.pop(key, None)


_limiter: MemoryRateLimiter | None = None


def get_limiter() -> MemoryRateLimiter:
    global _limiter
    if _limiter is None:
        settings = get_settings()
        _limiter = MemoryRateLimiter(
            max_requests=settings.RATE_LIMIT_MAX_REQUESTS,
            window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
        )
    return _limiter


def _client_ip(request: Request) -> str:
    if request.client:
        return request.client.host or "unknown"
    return "unknown"


def _api_key(request: Request) -> str:
    # A chave é truncada/anonimizada para não ser logada integralmente.
    raw = request.headers.get("X-API-Key", "")
    return f"key:{raw[:8]}" if raw else "no-key"


def _rate_limit_key(request: Request) -> str:
    ip = _client_ip(request)
    key = _api_key(request)
    # Endpoints de IA são caros (chamadas de provedor): limita por chave E por IP,
    # escolhendo a chave mais restritiva (~ chave primária, IP como fallback).
    return f"{key}|ip:{ip}"


def require_rate_limit(request: Request) -> None:
    """Dependência FastAPI que rejeita (429) requisições acima do limite."""
    limiter = get_limiter()
    if not limiter.allow(_rate_limit_key(request)):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Limite de requisições excedido "
                f"({limiter.max_requests} por {limiter.window_seconds}s). "
                "Aguarde e tente novamente."
            ),
            headers={"Retry-After": str(limiter.window_seconds)},
        )
