import os
from pathlib import Path
from functools import lru_cache
from dataclasses import dataclass, field


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def _env_int(key: str, default: int = 0) -> int:
    val = os.environ.get(key)
    return int(val) if val else default


@dataclass(frozen=True)
class Settings:
    PROJECT_NAME: str = "Cupula de Gestao Autonoma"
    VERSION: str = "1.0.0"
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent

    LOGS_DIR: Path = BASE_DIR / "logs"
    SANDBOX_DIR: Path = BASE_DIR / "sandbox"

    DOCKER_IMAGE: str = "python:3.12-slim"
    SANDBOX_TIMEOUT: int = 30
    SANDBOX_MEMORY: str = "256m"
    SANDBOX_CPUS: str = "0.5"

    N8N_PORT: int = 5678
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8080

    # API key de autenticação. OBRIGATÓRIA em produção. Se vazia, o servidor
    # recusa iniciar (fail-closed) para nunca rodar sem autenticação.
    CUPULA_API_KEY: str = ""

    # Grupo/consumidor do Worker (Redis Streams). O consumidor deve ser único
    # por instância para permitir múltiplas réplicas sem colisão.
    REDIS_CONSUMER_GROUP: str = "cupula-worker-group"
    REDIS_CONSUMER_NAME: str = "cupula-worker-1"

    REDIS_URL: str = "redis://localhost:6379"
    REDIS_STREAM_MAX_LEN: int = 10000

    # Banco de dados (não utilizado de forma obrigatória neste release). Sem
    # credencial embutida por padrão: a senha REAL deve vir de env DATABASE_URL.
    # Em produção, defina a env var completa (ex.: postgresql://user:senha@host:5432/db).
    DATABASE_URL: str = "postgresql://cupula@localhost:5432/cupula_db"

    # Rate limiting (M3) — limites default por janela deslizante em memória.
    RATE_LIMIT_MAX_REQUESTS: int = 60
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    # Persistência durável de decisões/pareceres (M4) — diretório versionável.
    DECISIONS_DIR: Path = BASE_DIR / "decisions"

    # Seleção de agentes (L3): roles priorizadas e limite de agentes por
    # decisão quando não há `required_roles` no request. A priorização torna
    # a escolha determinística (roles críticas primeiro, depois reputação).
    CUPULA_CRITICAL_ROLES: str = "sentinel,apolo"
    CUPULA_MAX_AGENTS_PER_DECISION: int = 10

    MAX_AGENTS: int = 10000
    AGENT_HEARTBEAT_INTERVAL: int = 30
    AGENT_TIMEOUT: int = 90

    LOG_FORMAT: str = "%(asctime)s | %(name)-25s | %(levelname)-8s | %(message)s"

    def __post_init__(self):
        self.LOGS_DIR.mkdir(exist_ok=True)
        self.SANDBOX_DIR.mkdir(exist_ok=True)
        self.DECISIONS_DIR.mkdir(exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    _BASE_DIR = Path(__file__).resolve().parent.parent.parent
    return Settings(
        REDIS_URL=_env("REDIS_URL", "redis://localhost:6379"),
        DATABASE_URL=_env("DATABASE_URL", "postgresql://cupula@localhost:5432/cupula_db"),
        API_HOST=_env("API_HOST", "0.0.0.0"),
        API_PORT=_env_int("API_PORT", 8080),
        REDIS_STREAM_MAX_LEN=_env_int("REDIS_STREAM_MAX_LEN", 10000),
        MAX_AGENTS=_env_int("MAX_AGENTS", 10000),
        AGENT_TIMEOUT=_env_int("AGENT_TIMEOUT", 90),
        CUPULA_API_KEY=_env("CUPULA_API_KEY", ""),
        REDIS_CONSUMER_GROUP=_env("REDIS_CONSUMER_GROUP", "cupula-worker-group"),
        REDIS_CONSUMER_NAME=_env("REDIS_CONSUMER_NAME", "cupula-worker-1"),
        RATE_LIMIT_MAX_REQUESTS=_env_int("RATE_LIMIT_MAX_REQUESTS", 60),
        RATE_LIMIT_WINDOW_SECONDS=_env_int("RATE_LIMIT_WINDOW_SECONDS", 60),
        DECISIONS_DIR=Path(_env("CUPULA_DECISIONS_DIR", str(_BASE_DIR / "decisions"))),
        CUPULA_CRITICAL_ROLES=_env("CUPULA_CRITICAL_ROLES", "sentinel,apolo"),
        CUPULA_MAX_AGENTS_PER_DECISION=_env_int("CUPULA_MAX_AGENTS_PER_DECISION", 10),
    )
