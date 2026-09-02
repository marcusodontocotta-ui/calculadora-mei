"""Persistência durável mínima de decisões e pareceres jurídicos (M4).

As decisões/pareceres eram mantidos apenas em memória (_decision_history) e em
Redis (volátil). Este módulo adiciona uma trilha em arquivo JSONL (append-only)
em um diretório configurável via env ``CUPULA_DECISIONS_DIR``, com rotação por
tamanho. Não substitui o histórico em memória (que segue como cache) — apenas
garante uma trilha de auditoria durável e versionável.
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock

from cupula.config.settings import get_settings
from cupula.core.logger import get_logger

logger = get_logger("persist")

_APPEND_WRITE_LOCK = Lock()

# Tamanho máximo (bytes) por arquivo antes de rotacionar para um novo índice.
DEFAULT_MAX_FILE_BYTES = 5 * 1024 * 1024  # 5 MiB


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _decisions_dir() -> Path:
    return get_settings().DECISIONS_DIR


def _current_file(decisions_dir: Path) -> Path:
    """Retorna o arquivo JSONL ativo (índice = contagem de arquivos existentes)."""
    pattern = "decisions_*.jsonl"
    existing = sorted(decisions_dir.glob(pattern))
    if not existing:
        return decisions_dir / "decisions_000000.jsonl"
    last = existing[-1]
    if last.stat().st_size >= DEFAULT_MAX_FILE_BYTES:
        idx = int(last.stem.split("_")[1]) + 1
        return decisions_dir / f"decisions_{idx:06d}.jsonl"
    return last


def persist_decision(record: dict) -> Path | None:
    """Adiciona um registro de decisão/parecer à trilha JSONL.

    O registro é enriquecido com um id e timestamp de auditoria antes de gravar.
    Falhas de escrita são logadas mas não propagam (persistência é best-effort;
    a decisão em memória segue funcionando mesmo se o disco falhar).
    """
    decisions_dir = _decisions_dir()
    try:
        decisions_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.error(f"Não foi possível criar CUPULA_DECISIONS_DIR {decisions_dir}: {e}")
        return None

    entry = {
        "id": f"dec_{int(time.time() * 1000)}_{abs(hash(record.get('title', ''))) % 100000}",
        "persisted_at": _now_iso(),
        "audit": {
            "origin": "cupula",
            "type": "decision",
            "version": get_settings().VERSION,
        },
        **record,
    }

    try:
        with _APPEND_WRITE_LOCK:
            path = _current_file(decisions_dir)
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False, default=str))
                f.write("\n")
        logger.info(f"Decisão persistida: {path}")
        return path
    except OSError as e:
        logger.error(f"Falha ao persistir decisão em {decisions_dir}: {e}")
        return None
