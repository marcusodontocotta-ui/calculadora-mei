import secrets

from fastapi import Header, HTTPException, Request, status

from cupula.config.settings import get_settings

_HEADER_NAME = "X-API-Key"


def _expected_key() -> str:
    return get_settings().CUPULA_API_KEY


def compare_digest(a: str, b: str) -> bool:
    return secrets.compare_digest(a or "", b or "")


def require_api_key(
    request: Request,
    x_api_key: str = Header(default="", alias=_HEADER_NAME),
) -> None:
    """Dependência global que protege as rotas /api/v1/*.

    Requer o cabeçalho ``X-API-Key`` com valor igual a ``CUPULA_API_KEY``.
    Fail-closed: se a env var não estiver configurada ou o header estiver
    ausente/incorreto, a requisição é rejeitada.
    """
    expected = _expected_key()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="CUPULA_API_KEY não configurada no servidor",
        )
    if not compare_digest(x_api_key, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key inválida ou ausente",
        )
