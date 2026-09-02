"""
Limites de validação para DTOs de entrada.

Objetivo: rejeitar payloads excessivos (L2) antes de chegarem aos agentes,
evitando DoS por memória/CPU e preservando a performance do sistema.

Limites documentados:
  - STR_MAX_TITLE   = 500    (títulos curtos)
  - STR_MAX_MEDIUM  = 2 000  (descrições, briefs)
  - STR_MAX_LONG    = 10 000 (textos livres longos)
  - LIST_MAX_ITEMS  = 50     (máximo de itens em listas)
  - DICT_MAX_KEYS   = 100    (máximo de chaves em dicts)
  - DICT_MAX_DEPTH  = 5      (profundidade máxima de嵌套 de dicts)
  - MAX_SERIALIZED  = 512 KB (tamanho total serializado do payload)

Esses valores são conservadores para uma API de backend. Para ajustar,
modifique as constantes abaixo ou crie Settings dedicadas.
"""

from __future__ import annotations

import sys
from dataclasses import fields as dc_fields
from typing import Any


# ── Limites ──────────────────────────────────────────────────────────────────

STR_MAX_TITLE: int = 500
STR_MAX_MEDIUM: int = 2_000
STR_MAX_LONG: int = 10_000

LIST_MAX_ITEMS: int = 50
DICT_MAX_KEYS: int = 100
DICT_MAX_DEPTH: int = 5

MAX_SERIALIZED_BYTES: int = 512 * 1024  # 512 KB


# ── Helpers ──────────────────────────────────────────────────────────────────

class PayloadTooLargeError(ValueError):
    """Payload excede limites aceitáveis."""

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


def _check_str(value: str, field_name: str, max_len: int) -> None:
    if not isinstance(value, str):
        return
    if len(value) > max_len:
        raise PayloadTooLargeError(
            f"Campo '{field_name}' excede {max_len} caracteres "
            f"(recebido: {len(value)})"
        )


def _check_list(value: list, field_name: str, max_items: int, max_depth: int, current_depth: int = 0) -> None:
    if not isinstance(value, list):
        return
    if len(value) > max_items:
        raise PayloadTooLargeError(
            f"Campo '{field_name}' excede {max_items} itens "
            f"(recebido: {len(value)})"
        )
    if current_depth >= max_depth:
        raise PayloadTooLargeError(
            f"Campo '{field_name}' excede profundidade máxima de {max_depth}"
        )
    for item in value:
        if isinstance(item, dict):
            _check_dict(item, f"{field_name}[*]", max_items, max_depth, current_depth + 1)
        elif isinstance(item, list):
            _check_list(item, f"{field_name}[*]", max_items, max_depth, current_depth + 1)


def _check_dict(value: dict, field_name: str, max_keys: int, max_depth: int, current_depth: int = 0) -> None:
    if not isinstance(value, dict):
        return
    if len(value) > max_keys:
        raise PayloadTooLargeError(
            f"Campo '{field_name}' excede {max_keys} chaves "
            f"(recebido: {len(value)})"
        )
    if current_depth >= max_depth:
        raise PayloadTooLargeError(
            f"Campo '{field_name}' excede profundidade máxima de {max_depth}"
        )
    for k, v in value.items():
        if isinstance(v, dict):
            _check_dict(v, f"{field_name}.{k}", max_keys, max_depth, current_depth + 1)
        elif isinstance(v, list):
            _check_list(v, f"{field_name}.{k}", max_keys, max_depth, current_depth + 1)


def _estimate_size(obj: Any) -> int:
    """Estima o tamanho serializado em bytes (JSON-like)."""
    if isinstance(obj, str):
        return len(obj.encode("utf-8"))
    if isinstance(obj, (int, float, bool)):
        return 8
    if isinstance(obj, list):
        return sum(_estimate_size(item) for item in obj) + 16
    if isinstance(obj, dict):
        return sum(_estimate_size(k) + _estimate_size(v) for k, v in obj.items()) + 32
    return 16


def validate_dto(instance: Any) -> None:
    """Valida um dataclass DTO verificando limites de tamanho.

    Chame *depois* da construção do dataclass (no __post_init__ ou
    explicitamente). Levanta PayloadTooLargeError se os limites forem
    excedidos.
    """
    total = 0
    for f in dc_fields(instance):
        value = getattr(instance, f.name)
        total += _estimate_size(value)

        if isinstance(value, str):
            if f.name in ("title", "titulo", "trigger", "action", "language",
                          "framework", "style", "size", "quality", "brief",
                          "product", "audience", "topic", "error",
                          "image_url", "image_url_a", "image_url_b"):
                _check_str(value, f.name, STR_MAX_TITLE)
            elif f.name in ("description", "descricao", "context", "acao_proposta"):
                _check_str(value, f.name, STR_MAX_LONG)
            else:
                _check_str(value, f.name, STR_MAX_MEDIUM)

        elif isinstance(value, list):
            _check_list(value, f.name, LIST_MAX_ITEMS, DICT_MAX_DEPTH)

        elif isinstance(value, dict):
            _check_dict(value, f.name, DICT_MAX_KEYS, DICT_MAX_DEPTH)

    if total > MAX_SERIALIZED_BYTES:
        raise PayloadTooLargeError(
            f"Payload total excede {MAX_SERIALIZED_BYTES} bytes "
            f"(estimado: {total})"
        )
