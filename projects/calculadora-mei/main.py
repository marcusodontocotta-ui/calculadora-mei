"""
Calculadora de MEI - Backend API
FastAPI server com endpoints para calculos DAS, simulacoes, alertas e registro de vendas
"""
import asyncio
import hashlib
import os
import re
import secrets
import shutil
import socket
import subprocess
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Optional

import httpx
from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import database
from calculadora import (
    TABELA_DAS_2025,
    TETO_ANUAL_2025,
    TETO_MENSAL_2025,
    CenarioSimulacao,
    calcular_das,
    formatar_moeda,
    obter_alertas_vencimento,
    simular_cenarios,
)

MERCADO_PAGO_TOKEN = os.environ.get("MP_ACCESS_TOKEN", "TEST-xxx")
MERCADO_PAGO_PUBLIC_KEY = os.environ.get("MP_PUBLIC_KEY", "TEST-xxx")
PRECO_PRO_MENSAL = 9.90
RECONCILIACAO_INTERVALO_SEG = int(os.environ.get("RECONCILIACAO_INTERVALO_SEG", "600"))

PLANO_LIMITES = {
    "free": {"produtos": 15, "clientes": 20, "vendas": 100, "despesas": 100},
    "pro": {"produtos": 500, "clientes": 500, "vendas": 2000, "despesas": 2000},
}

LIMITES_UPLOAD = {
    "tamanho_max": 2 * 1024 * 1024,
    "tipos": {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"},
}


def _detectar_imagem(content_type: str, dados: bytes) -> str | None:
    """Valida imagem por magic bytes e retorna extensao; None se nao for jpeg/png/webp real."""
    if dados[:4] == b"\xff\xd8\xff":
        return ".jpg"
    if dados.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if dados[:4] == b"RIFF" and dados[8:12] == b"WEBP":
        return ".webp"
    return None


@asynccontextmanager
async def lifespan(app):
    await database.init_db()
    task = asyncio.create_task(_loop_reconciliacao())
    yield
    task.cancel()


app = FastAPI(
    title="Calculadora MEI",
    description="Calculadora de DAS para Microempreendedores Individuais",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")


# ── Models ────────────────────────────────────────────────────────────────────

class CalculoDASRequest(BaseModel):
    mes: int = Field(..., ge=1, le=12, description="Mes do calculo (1-12)")
    ano: int = Field(..., ge=2020, le=2030, description="Ano do calculo")
    faturamento: float = Field(..., ge=0, description="Faturamento bruto do mes")
    tipo_atividade: str = Field("servico", description="comercio, servico ou misto")


class SimulacaoRequest(BaseModel):
    cenarios: list[dict] = Field(..., description="Lista de cenarios para simular")


class ProdutoRequest(BaseModel):
    nome: str = Field(..., min_length=1, description="Nome do produto/servico")
    preco: float = Field(..., gt=0, description="Preco unitario")
    categoria: Optional[str] = Field("servico", description="servico, produto ou insumo")
    descricao: Optional[str] = Field("", description="Descricao opcional")
    data_fabricacao: Optional[str] = Field(None, description="Data de fabricacao (YYYY-MM-DD)")
    data_validade: Optional[str] = Field(None, description="Data de validade (YYYY-MM-DD)")
    codigo_barras: Optional[str] = Field(None, description="Codigo de barras ou QR Code")
    estoque: Optional[int] = Field(0, ge=0, description="Quantidade em estoque")
    foto_url: Optional[str] = Field(None, description="URL da foto do produto")
    unidade: Optional[str] = Field("un", description="un, kg, lt, mt, cx, par")


class VendaRequest(BaseModel):
    produto_id: Optional[int] = Field(None, description="ID do produto cadastrado")
    descricao: str = Field(..., min_length=1, description="Descricao da venda")
    valor: float = Field(..., gt=0, description="Valor da venda")
    quantidade: int = Field(1, ge=1, description="Quantidade")
    data: Optional[str] = Field(None, description="Data da venda (YYYY-MM-DD)")
    cliente: Optional[str] = Field("", description="Nome do cliente")
    cliente_id: Optional[int] = Field(None, description="ID do cliente")


class DespesaRequest(BaseModel):
    descricao: str = Field(..., min_length=1, description="Descricao da despesa")
    valor: float = Field(..., gt=0, description="Valor da despesa")
    data: Optional[str] = Field(None, description="Data da despesa (YYYY-MM-DD)")
    categoria: Optional[str] = Field("fixa", description="fixa, variavel, material, transporte, servico, imposto ou outro")


class ClienteRequest(BaseModel):
    nome: str = Field(..., min_length=1, description="Nome do cliente")
    telefone: Optional[str] = Field(None, description="Telefone/WhatsApp")
    email: Optional[str] = Field(None, description="E-mail")
    data_aniversario: Optional[str] = Field(None, description="Data de aniversario (YYYY-MM-DD)")
    endereco: Optional[str] = Field(None, description="Endereco")
    observacoes: Optional[str] = Field("", description="Observacoes sobre o cliente")
    produto_preferido: Optional[str] = Field(None, description="Produto/servico preferido")
    periodicidade: Optional[str] = Field(None, description="Frequencia: diario, semanal, quinzenal, mensal, avulso")


class AssinaturaRequest(BaseModel):
    cliente_id: Optional[int] = Field(None, description="Compatibilidade - nao utilizado")
    email: Optional[str] = Field(None, description="Email do pagante (usado email do usuario autenticado)")
    nome: Optional[str] = Field(None, description="Nome do pagante (usado nome do usuario autenticado)")
    cupom: Optional[str] = Field(None, description="Codigo do cupom de desconto")


class CupomValidarRequest(BaseModel):
    codigo: str = Field(..., min_length=1, description="Codigo do cupom")


class CadastroRequest(BaseModel):
    nome: str = Field(..., min_length=1, description="Nome do usuario")
    email: str = Field(..., description="Email do usuario")
    senha: str = Field(..., description="Senha (minimo 6 caracteres)")


class LoginRequest(BaseModel):
    email: str = Field(..., description="Email do usuario")
    senha: str = Field(..., description="Senha")


class ValidarEmailRequest(BaseModel):
    email: str = Field(..., description="Email a validar")


class ScanCodigoRequest(BaseModel):
    imagem_base64: Optional[str] = Field(None, description="Imagem em base64")
    codigo: Optional[str] = Field(None, description="Codigo ja detectado")


# ── Funcoes auxiliares de autenticacao ───────────────────────────────────────

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

DOMINIOS_DESCARTAVEIS = {
    "mailinator.com", "yopmail.com", "tempmail.com", "guerrillamail.com",
    "10minutemail.com", "throwawaymail.com", "shut.name", "maildrop.cc",
    "fakemail.com", "disposablemail.com",
}


def _gerar_salt() -> str:
    return secrets.token_hex(16)


def _hash_senha(senha: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt.encode("utf-8"), 100_000).hex()


def _verificar_senha(senha: str, senha_hash: str) -> bool:
    if "$" not in senha_hash:
        return False
    salt, h = senha_hash.split("$", 1)
    return secrets.compare_digest(_hash_senha(senha, salt), h)


def _novo_token() -> str:
    return secrets.token_urlsafe(32)


def _expira_em() -> str:
    return (datetime.now() + timedelta(days=30)).isoformat()


async def usuario_atual(authorization: str = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token nao fornecido")
    token = authorization[7:].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Token nao fornecido")
    usuario = await database.usuario_por_token(token)
    if not usuario:
        raise HTTPException(status_code=401, detail="Token invalido ou expirado")
    return usuario


def _assinatura_ativa(assinatura) -> bool:
    if not assinatura or assinatura.get("status") != "ativa":
        return False
    fim = assinatura.get("data_fim")
    if not fim:
        return True
    try:
        return datetime.fromisoformat(fim) > datetime.now()
    except Exception:
        return True


async def _plano_usuario(usuario_id: int) -> str:
    assinatura = await database.obter_assinatura_usuario(usuario_id)
    if _assinatura_ativa(assinatura):
        return "pro"
    return "free"


async def _ativa_se_vigente(assinatura: dict | None) -> dict | None:
    """Retorna a assinatura se estiver ativa e dentro da vigencia; senao None."""
    if not _assinatura_ativa(assinatura):
        return None
    return assinatura


# ── Reconciliação de pagamentos / renovação ───────────────────────────────────

async def reconciliar_pagamentos():
    """Garante que nenhum pagamento aprovado fique sem ativar o PRO (webhook perdido).

    1) Expira assinaturas ativas com data_fim vencida.
    2) Para cada assinatura pendente, consulta a MP por external_reference e ativa se houver pagamento aprovado.
    """
    try:
        expiradas = await database.expirar_assinaturas_vencidas()
        if expiradas:
            print(f"[RECON] {expiradas} assinatura(s) expirada(s) por data_fim vencida")
    except Exception as e:
        print(f"[RECON] Erro ao expirar assinaturas: {e}")

    try:
        pendentes = await database.listar_assinaturas_pendentes()
        if not pendentes:
            return
        async with httpx.AsyncClient(timeout=15) as client:
            for assinatura in pendentes:
                usuario_id = assinatura.get("usuario_id")
                if not usuario_id:
                    continue
                await _ativar_por_pagamento_aprovado(client, assinatura)
    except Exception as e:
        print(f"[RECON] Erro na varredura de pendentes: {e}")


async def _ativar_por_pagamento_aprovado(client, assinatura):
    """Consulta a MP por pagamentos aprovados dessa assinatura e ativa se encontrar."""
    usuario_id = assinatura["usuario_id"]
    try:
        resp = await client.get(
            "https://api.mercadopago.com/v1/payments/search",
            params={"external_reference": f"usuario_{usuario_id}", "status": "approved"},
            headers={"Authorization": f"Bearer {MERCADO_PAGO_TOKEN}"}
        )
        if resp.status_code != 200:
            return
        resultados = resp.json().get("results", [])
    except Exception as e:
        print(f"[RECON] Falha ao consultar MP p/ usuario {usuario_id}: {e}")
        return

    for pagamento in resultados:
        pago_id = pagamento.get("id")
        if not pago_id:
            continue
        ja_processado = await database.obter_pagamento(pago_id)
        if ja_processado:
            continue
        if pagamento.get("status") != "approved":
            continue
        valor = (pagamento.get("transaction_amount") or 0.0)
        registrado = await database.registrar_pagamento(
            str(pago_id),
            pagamento.get("preference_id"),
            usuario_id,
            assinatura["id"],
            "approved",
            valor,
            "reconciliacao",
            str(pagamento)[:1000],
        )
        if registrado:
            renovou = await database.ativar_assinatura(assinatura["id"], str(pago_id))
            tipo = "renovação" if renovou else "ativação"
            print(f"[RECON] Assinatura {assinatura['id']} {tipo} via pagamento {pago_id} (R$ {valor:.2f})")
            break


async def _loop_reconciliacao():
    while True:
        await reconciliar_pagamentos()
        await asyncio.sleep(RECONCILIACAO_INTERVALO_SEG)


@asynccontextmanager
async def lifespan(app):
    await database.init_db()
    task = asyncio.create_task(_loop_reconciliacao())
    yield
    task.cancel()


# ── Validacao de email ───────────────────────────────────────────────────────

def _dominio_tem_mx(dominio: str) -> bool:
    """Checa se o dominio tem registro MX via nslookup. Se a ferramenta falhar, aceita (noop True)."""
    try:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        resultado = subprocess.run(
            ["nslookup", "-type=mx", dominio],
            capture_output=True, text=True, timeout=6,
            creationflags=flags
        )
        saida = ((resultado.stdout or "") + (resultado.stderr or "")).lower()
        if "mail exchanger" in saida:
            return True
        if any(marca in saida for marca in [
            "no mx", "no mail servers", "can't find", "cannot find",
            "non-existent domain", "no data", "no records",
        ]):
            return False
        if not saida.strip():
            return True
        try:
            socket.gethostbyname_ex(dominio)
            return True
        except Exception:
            return True
    except Exception:
        return True


async def _validar_email_completo(email: str) -> dict:
    email = (email or "").strip()
    if not EMAIL_REGEX.match(email):
        return {"valido": False, "motivo": "formato_invalido"}
    dominio = email.rsplit("@", 1)[1].lower().strip(".")
    if dominio in DOMINIOS_DESCARTAVEIS:
        return {"valido": False, "motivo": "dominio_descartavel"}
    if not _dominio_tem_mx(dominio):
        return {"valido": False, "motivo": "dominio_sem_mx"}
    return {"valido": True, "motivo": "ok"}


# ── Paginas estaticas ─────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root():
    with open("templates/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/termos", response_class=HTMLResponse)
async def termos():
    with open("templates/termos.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/privacidade", response_class=HTMLResponse)
async def privacidade():
    with open("templates/privacidade.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


# ── API Endpoints ─────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    assinaturas = await database.contar_assinaturas_ativas()
    return {
        "status": "healthy",
        "version": "2.0.0",
        "teto_anual": TETO_ANUAL_2025,
        "teto_mensal": round(TETO_MENSAL_2025, 2),
        "tabela_das": TABELA_DAS_2025,
        "assinaturas_ativas": assinaturas,
        "timestamp": datetime.now().isoformat()
    }


# ── Autenticacao ─────────────────────────────────────────────────────────────

@app.post("/api/auth/cadastro", status_code=201)
async def cadastro(req: CadastroRequest):
    nome = (req.nome or "").strip()
    email = (req.email or "").strip().lower()
    senha = req.senha or ""

    if not EMAIL_REGEX.match(email):
        raise HTTPException(status_code=400, detail="Email invalido")
    if len(senha) < 6:
        raise HTTPException(status_code=400, detail="Senha deve ter pelo menos 6 caracteres")
    if await database.obter_usuario_por_email(email):
        raise HTTPException(status_code=409, detail="Email ja cadastrado")

    salt = _gerar_salt()
    usuario = await database.criar_usuario(nome, email, f"{salt}${_hash_senha(senha, salt)}")
    if not usuario:
        raise HTTPException(status_code=409, detail="Email ja cadastrado")

    token = _novo_token()
    await database.criar_sessao(usuario["id"], token, _expira_em())

    return {
        "token": token,
        "usuario": {
            "id": usuario["id"],
            "nome": usuario["nome"],
            "email": usuario["email"],
            "plano": await _plano_usuario(usuario["id"]),
        }
    }


@app.post("/api/auth/login")
async def login(req: LoginRequest):
    email = (req.email or "").strip().lower()
    usuario = await database.obter_usuario_por_email(email)
    if not usuario or not _verificar_senha(req.senha or "", usuario["senha_hash"]):
        raise HTTPException(status_code=401, detail="Credenciais invalidas")

    token = _novo_token()
    await database.criar_sessao(usuario["id"], token, _expira_em())

    return {
        "token": token,
        "usuario": {
            "id": usuario["id"],
            "nome": usuario["nome"],
            "email": usuario["email"],
            "plano": await _plano_usuario(usuario["id"]),
        }
    }


@app.post("/api/auth/logout")
async def logout(authorization: str = Header(None)):
    if authorization and authorization.startswith("Bearer "):
        await database.revogar_sessao(authorization[7:].strip())
    return {"sucesso": True, "mensagem": "Sessao encerrada"}


@app.get("/api/auth/me")
async def me(usuario: dict = Depends(usuario_atual)):
    plano = await _plano_usuario(usuario["id"])
    produtos = await database.contar_produtos(usuario["id"])
    clientes = await database.contar_clientes(usuario["id"])
    vendas = await database.contar_vendas_total(usuario["id"])
    despesas = await database.contar_despesas_total(usuario["id"])
    return {
        "usuario": {
            "id": usuario["id"],
            "nome": usuario["nome"],
            "email": usuario["email"],
            "plano": plano,
        },
        "autenticado": True,
        "limites": PLANO_LIMITES[plano],
        "uso": {"produtos": produtos, "clientes": clientes, "vendas": vendas, "despesas": despesas},
    }


# ── Assinaturas / Plano ──────────────────────────────────────────────────────

def _aplicar_cupom(percentual: float) -> dict:
    desconto = round(PRECO_PRO_MENSAL * percentual / 100, 2)
    valor_final = round(PRECO_PRO_MENSAL - desconto, 2)
    if valor_final < 0.01:
        valor_final = 0.01
    return {"desconto": desconto, "valor_final": valor_final}


@app.post("/api/assinatura/checkout")
async def criar_checkout(req: AssinaturaRequest, usuario: dict = Depends(usuario_atual)):
    usuario_id = usuario["id"]
    ativa = await database.obter_assinatura_ativa_usuario(usuario_id)
    if ativa:
        return {"sucesso": False, "motivo": "ja_ativa"}

    pendente = await database.obter_assinatura_pendente_usuario(usuario_id)
    if pendente:
        return {
            "sucesso": False,
            "motivo": "ja_pendente",
            "mensagem": "Ja existe um pagamento pendente. Conclua ou aguarde a confirmacao.",
        }

    cupom_aplicado = None
    valor_unitario = PRECO_PRO_MENSAL
    if req.cupom:
        codigo = (req.cupom or "").strip().upper()
        cupom = await database.obter_cupom(codigo)
        if not cupom:
            raise HTTPException(status_code=400, detail="Cupom nao encontrado")
        if not cupom.get("ativo"):
            raise HTTPException(status_code=400, detail="Cupom inativo")
        cupom_aplicado = cupom
        valor_unitario = _aplicar_cupom(cupom["percentual"])["valor_final"]

    metadata = {"usuario_id": usuario_id, "email": usuario["email"]}
    if cupom_aplicado:
        metadata["cupom"] = cupom_aplicado["codigo"]

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.mercadopago.com/checkout/preferences",
            headers={
                "Authorization": f"Bearer {MERCADO_PAGO_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "items": [{
                    "id": "plano_pro",
                    "title": "Calculadora MEI - Plano PRO",
                    "description": "Plano PRO mensal - Calculadora MEI",
                    "quantity": 1,
                    "unit_price": round(valor_unitario, 2),
                    "currency_id": "BRL"
                }],
                "payer": {
                    "email": usuario["email"],
                    "name": usuario["nome"]
                },
                "metadata": metadata,
                "external_reference": f"usuario_{usuario_id}",
                "notification_url": "https://calculadora-mei.onrender.com/api/webhook/mercadopago",
                "auto_return": "approved",
                "back_urls": {
                    "success": "https://calculadora-mei.onrender.com/?pagamento=sucesso",
                    "pending": "https://calculadora-mei.onrender.com/?pagamento=pendente",
                    "failure": "https://calculadora-mei.onrender.com/?pagamento=erro"
                }
            }
        )
        dados = resp.json()
        checkout_url = dados.get("init_point")

        await database.criar_assinatura({
            "usuario_id": usuario_id,
            "email": usuario["email"],
            "nome": usuario["nome"],
            "status": "pendente",
            "mp_subscription_id": dados.get("id")
        })

        resposta = {
            "sucesso": True,
            "checkout_url": checkout_url,
            "preference_id": dados.get("id"),
            "valor": round(valor_unitario, 2)
        }
        if cupom_aplicado:
            valores = _aplicar_cupom(cupom_aplicado["percentual"])
            resposta["valor_original"] = PRECO_PRO_MENSAL
            resposta["desconto"] = valores["desconto"]
            resposta["valor_final"] = valores["valor_final"]
        return resposta


@app.post("/api/webhook/mercadopago")
async def webhook_mercadopago(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}
    tipo = body.get("type", "")
    dados = body.get("data", {})

    if tipo != "payment":
        return {"sucesso": True, "processado": False, "motivo": "tipo_ignorado"}

    payment_id = dados.get("id")
    if not payment_id:
        return {"sucesso": True, "processado": False, "motivo": "sem_payment_id"}

    ja_processado = await database.obter_pagamento(payment_id)
    if ja_processado:
        print(f"[WEBHOOK] Payment {payment_id} ja processado (idempotencia)")
        return {"sucesso": True, "processado": True, "duplicado": True}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"https://api.mercadopago.com/v1/payments/{payment_id}",
                headers={"Authorization": f"Bearer {MERCADO_PAGO_TOKEN}"}
            )
            if resp.status_code != 200:
                print(f"[WEBHOOK] Erro ao buscar pagamento {payment_id} na MP: HTTP {resp.status_code}")
                return {"sucesso": False, "processado": False, "motivo": "mp_inacessivel"}
            pagamento = resp.json()
    except Exception as e:
        print(f"[WEBHOOK] Excecao ao buscar pagamento {payment_id}: {e}")
        return {"sucesso": False, "processado": False, "motivo": "erro_mp"}

    if pagamento.get("status") != "approved":
        print(f"[WEBHOOK] Pagamento {payment_id} nao aprovado (status={pagamento.get('status')})")
        return {"sucesso": True, "processado": True, "status": pagamento.get("status")}

    metadata = pagamento.get("metadata", {}) or {}
    usuario_id = metadata.get("usuario_id")
    valor = pagamento.get("transaction_amount") or 0.0
    external_ref = pagamento.get("external_reference") or ""

    assinatura = None
    if usuario_id:
        assinatura = await database.obter_assinatura_pendente_usuario(usuario_id)
    if not assinatura and usuario_id and "usuario_" in external_ref:
        ref_id = external_ref.replace("usuario_", "")
        if ref_id.isdigit():
            assinatura = await database.obter_assinatura_usuario(int(ref_id))
    if not assinatura and metadata.get("cliente_id"):
        assinatura = await database.obter_assinatura_cliente(metadata["cliente_id"])
    if not assinatura:
        print(f"[WEBHOOK] Pagamento {payment_id} aprovado sem assinatura correspondente")
        await database.registrar_pagamento(
            str(payment_id), pagamento.get("preference_id"), usuario_id,
            None, "approved", valor, "inicial", str(pagamento)[:1000],
        )
        return {"sucesso": True, "processado": False, "motivo": "sem_assinatura"}

    registrado = await database.registrar_pagamento(
        str(payment_id), pagamento.get("preference_id"), usuario_id,
        assinatura["id"], "approved", valor, "inicial", str(pagamento)[:1000],
    )
    renovou = False
    if registrado:
        renovou = await database.ativar_assinatura(assinatura["id"], str(payment_id))
        print(
            f"[WEBHOOK] Assinatura {assinatura['id']} {'renovada' if renovou else 'ativada'} "
            f"(usuario {usuario_id}, payment {payment_id}, R$ {valor:.2f})"
        )
    return {"sucesso": True, "processado": True, "renovada": renovou}


@app.get("/api/assinatura/{cliente_id}")
async def verificar_assinatura(cliente_id: int):
    """Compatibilidade: ainda consulta por cliente_id. GET /api/plano e a fonte de verdade."""
    assinatura = await database.obter_assinatura_cliente(cliente_id)
    if not _ativa_se_vigente(assinatura):
        return {
            "sucesso": True,
            "ativo": False,
            "plano": "free",
            "mensagem": "Sem assinatura ativa"
        }
    return {
        "sucesso": True,
        "ativo": True,
        "plano": "pro",
        "assinatura": assinatura
    }


@app.post("/api/admin/reconciliar")
async def reconciliar_manual(authorization: str = Header(None)):
    import hmac

    expected = os.environ.get("ADMIN_SECRET", "")
    if not expected or not authorization or not hmac.compare_digest(authorization, f"Bearer {expected}"):
        raise HTTPException(status_code=403, detail="Nao autorizado")
    await reconciliar_pagamentos()
    return {"sucesso": True, "mensagem": "Reconciliacao executada"}


@app.get("/api/plano")
async def ver_plano(usuario: dict = Depends(usuario_atual)):
    assinatura = await database.obter_assinatura_usuario(usuario["id"])
    ativa = _ativa_se_vigente(assinatura)
    plano = "pro" if ativa else "free"
    produtos = await database.contar_produtos(usuario["id"])
    clientes = await database.contar_clientes(usuario["id"])
    vendas = await database.contar_vendas_total(usuario["id"])
    despesas = await database.contar_despesas_total(usuario["id"])
    base = {
        "ativo": bool(ativa),
        "plano": plano,
        "assinatura": assinatura,
        "limites": PLANO_LIMITES[plano],
        "uso": {"produtos": produtos, "clientes": clientes, "vendas": vendas, "despesas": despesas},
    }
    if ativa:
        dias_restantes = None
        if assinatura.get("data_fim"):
            try:
                dias_restantes = max(0, (datetime.fromisoformat(assinatura["data_fim"]) - datetime.now()).days)
            except Exception:
                pass
        base["dias_restantes"] = dias_restantes
        base["renovacoes"] = assinatura.get("renovacoes") or 0
        return base
    if assinatura and assinatura.get("status") == "vencida":
        base["mensagem"] = "Assinatura expirada. Renove para continuar usando o PRO."
        return base
    return base


@app.post("/api/assinatura/{cliente_id}/cancelar")
async def cancelar_assinatura_endpoint(cliente_id: int, usuario: dict = Depends(usuario_atual)):
    assinatura = await database.obter_assinatura_usuario(usuario["id"])
    if not assinatura or assinatura.get("status") != "ativa":
        raise HTTPException(status_code=404, detail="Assinatura nao encontrada")
    await database.cancelar_assinatura_usuario(usuario["id"])
    return {"sucesso": True, "mensagem": "Assinatura cancelada"}


# ── Cupons de desconto ────────────────────────────────────────────────────────

@app.post("/api/cupom/validar")
async def validar_cupom(req: CupomValidarRequest, usuario: dict = Depends(usuario_atual)):
    codigo = (req.codigo or "").strip().upper()
    if not codigo:
        return {"valido": False, "motivo": "invalido"}
    cupom = await database.obter_cupom(codigo)
    if not cupom:
        return {"valido": False, "motivo": "invalido"}
    if not cupom.get("ativo"):
        return {"valido": False, "motivo": "inativo"}
    valores = _aplicar_cupom(cupom["percentual"])
    return {
        "valido": True,
        "percentual": cupom["percentual"],
        "desconto": valores["desconto"],
        "valor_final": valores["valor_final"],
        "codigo": cupom["codigo"],
    }


@app.get("/api/cupom")
async def listar_cupons(usuario: dict = Depends(usuario_atual)):
    cupons = await database.listar_cupons_ativos()
    return {"sucesso": True, "cupons": cupons, "total": len(cupons)}


# ── Validacao de email ───────────────────────────────────────────────────────

@app.post("/api/validar-email")
async def validar_email(req: ValidarEmailRequest):
    return await _validar_email_completo(req.email)


# ── Calculos DAS (publicos) ──────────────────────────────────────────────────

@app.post("/api/calcular-das")
async def api_calcular_das(req: CalculoDASRequest):
    try:
        resultado = calcular_das(
            mes=req.mes,
            ano=req.ano,
            faturamento=req.faturamento,
            tipo_atividade=req.tipo_atividade
        )
        return {
            "sucesso": True,
            "resultado": {
                "mes": resultado.mes,
                "ano": resultado.ano,
                "faturamento": resultado.faturamento,
                "faturamento_formatado": formatar_moeda(resultado.faturamento),
                "teto_anual": resultado.teto_anual,
                "dentro_do_teto": resultado.dentro_do_teto,
                "componentes": {
                    "inss": resultado.inss,
                    "icms": resultado.icms,
                    "iss": resultado.iss,
                    "total": resultado.valor_total
                },
                "total_formatado": formatar_moeda(resultado.valor_total),
                "data_vencimento": resultado.data_vencimento,
                "dias_ate_vencer": resultado.dias_ate_vencer,
                "pode_emitir_nfe": resultado.pode_emitir_nfe,
                "alerta": obter_alertas_vencimento(req.mes, req.ano)
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/simular")
async def api_simular(req: SimulacaoRequest):
    try:
        cenarios = []
        for c in req.cenarios:
            cenarios.append(CenarioSimulacao(
                nome=c.get("nome", "Cenario"),
                faturamento_mensal=c.get("faturamento_mensal", 0),
                custos_fixos=c.get("custos_fixos", 0),
                custos_variaveis_pct=c.get("custos_variaveis_pct", 0),
                meses=c.get("meses", 12),
                atividade=c.get("atividade") or c.get("tipo_atividade") or "comercio"
            ))

        resultados = simular_cenarios(cenarios)

        return {
            "sucesso": True,
            "resultados": [
                {
                    "nome": r.cenario.nome,
                    "faturamento_mensal": r.cenario.faturamento_mensal,
                    "faturamento_mensal_fmt": formatar_moeda(r.cenario.faturamento_mensal),
                    "faturamento_anual": r.faturamento_anual,
                    "faturamento_anual_fmt": formatar_moeda(r.faturamento_anual),
                    "lucro_bruto": r.lucro_bruto,
                    "lucro_bruto_fmt": formatar_moeda(r.lucro_bruto),
                    "lucro_liquido": r.lucro_liquido,
                    "lucro_liquido_fmt": formatar_moeda(r.lucro_liquido),
                    "das_anual": r.das_anual,
                    "das_anual_fmt": formatar_moeda(r.das_anual),
                    "margem": round(r.margem_eff, 1),
                    "roi_meses": round(r.roi_meses, 1) if r.roi_meses != float('inf') else None,
                    "dentro_teto": r.faturamento_anual <= TETO_ANUAL_2025
                }
                for r in resultados
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/alertas")
async def api_alertas(mes: Optional[int] = None, ano: Optional[int] = None):
    agora = datetime.now()
    mes = mes or agora.month
    ano = ano or agora.year

    alerta = obter_alertas_vencimento(mes, ano)
    return {"sucesso": True, "alerta": alerta}


@app.get("/api/tabela-das")
async def api_tabela_das():
    return {
        "sucesso": True,
        "ano": 2025,
        "teto_anual": TETO_ANUAL_2025,
        "teto_mensal": round(TETO_MENSAL_2025, 2),
        "tabela": TABELA_DAS_2025,
        "vencimento_dia": 20,
        "multa_atraso_pct": 2.0,
        "juros_mes_pct": 1.0
    }


@app.get("/api/dashboard")
async def api_dashboard():
    agora = datetime.now()
    alerta = obter_alertas_vencimento(agora.month, agora.year)

    cenarios_padrao = [
        CenarioSimulacao("Conservador", 3000, 800, 20, 12),
        CenarioSimulacao("Moderado", 5000, 1200, 25, 12),
        CenarioSimulacao("Otimista", 6750, 1500, 30, 12),
    ]
    resultados = simular_cenarios(cenarios_padrao)

    return {
        "sucesso": True,
        "resumo": {
            "mes_atual": agora.month,
            "ano_atual": agora.year,
            "mes_nome": agora.strftime("%B").title(),
            "teto_anual": TETO_ANUAL_2025,
            "teto_mensal": round(TETO_MENSAL_2025, 2)
        },
        "alerta": alerta,
        "simulacoes": [
            {
                "nome": r.cenario.nome,
                "faturamento": formatar_moeda(r.cenario.faturamento_mensal),
                "lucro_liquido": formatar_moeda(r.lucro_liquido),
                "margem": f"{r.margem_eff:.1f}%"
            }
            for r in resultados
        ]
    }


# ── Funcoes auxiliares ────────────────────────────────────────────────────────

def _calcular_dias_validade(data_validade: str) -> int:
    try:
        data_val = datetime.strptime(data_validade, "%Y-%m-%d")
        hoje = datetime.now()
        return (data_val - hoje).days
    except:
        return None


def _status_validade(data_validade: str) -> dict:
    dias = _calcular_dias_validade(data_validade)
    if dias is None:
        return {"nivel": "indefinido", "mensagem": "Data invalida"}

    if dias < 0:
        return {"nivel": "vencido", "mensagem": f"Vencido ha {abs(dias)} dias", "cor": "#dc2626"}
    elif dias <= 7:
        return {"nivel": "critico", "mensagem": f"Vence em {dias} dias!", "cor": "#f59e0b"}
    elif dias <= 30:
        return {"nivel": "atencao", "mensagem": f"Vence em {dias} dias", "cor": "#f59e0b"}
    elif dias <= 90:
        return {"nivel": "ok", "mensagem": f"Vence em {dias} dias", "cor": "#16a34a"}
    else:
        return {"nivel": "otimo", "mensagem": f"Valido por {dias} dias", "cor": "#16a34a"}


def _gerar_codigo_barras_texto(codigo: str) -> str:
    if not codigo:
        return ""
    return f"||| {codigo} |||"


# ── Endpoints de Cadastro de Produtos ────────────────────────────────────────

@app.post("/api/produtos")
async def cadastrar_produto(req: ProdutoRequest, usuario: dict = Depends(usuario_atual)):
    plano = await _plano_usuario(usuario["id"])
    limite = PLANO_LIMITES[plano]["produtos"]
    total = await database.contar_produtos(usuario["id"])
    if total >= limite:
        raise HTTPException(
            status_code=422,
            detail=f"Limite do plano {plano.upper()} atingido: {limite} produtos. "
                   "Exclua itens ou faca upgrade para o PRO."
        )
    produto = await database.criar_produto({
        "nome": req.nome,
        "preco": req.preco,
        "categoria": req.categoria,
        "descricao": req.descricao or "",
        "data_fabricacao": req.data_fabricacao,
        "data_validade": req.data_validade,
        "codigo_barras": req.codigo_barras,
        "estoque": req.estoque,
        "foto_url": req.foto_url,
        "unidade": req.unidade,
    }, usuario["id"])
    produto["preco_formatado"] = formatar_moeda(produto["preco"])
    if produto.get("data_validade"):
        produto["dias_para_vencer"] = _calcular_dias_validade(produto["data_validade"])
        produto["status_validade"] = _status_validade(produto["data_validade"])
    return {"sucesso": True, "produto": produto}


@app.get("/api/produtos")
async def listar_produtos(usuario: dict = Depends(usuario_atual)):
    produtos = await database.listar_produtos(usuario["id"])
    for p in produtos:
        p["preco_formatado"] = formatar_moeda(p["preco"])
        if p.get("data_validade"):
            p["dias_para_vencer"] = _calcular_dias_validade(p["data_validade"])
            p["status_validade"] = _status_validade(p["data_validade"])
    return {"sucesso": True, "produtos": produtos, "total": len(produtos)}


@app.get("/api/produtos/{produto_id}")
async def obter_produto(produto_id: int, usuario: dict = Depends(usuario_atual)):
    produto = await database.obter_produto(produto_id, usuario["id"])
    if not produto:
        raise HTTPException(status_code=404, detail="Produto nao encontrado")
    produto["preco_formatado"] = formatar_moeda(produto["preco"])
    if produto.get("data_validade"):
        produto["dias_para_vencer"] = _calcular_dias_validade(produto["data_validade"])
        produto["status_validade"] = _status_validade(produto["data_validade"])
    return {"sucesso": True, "produto": produto}


@app.put("/api/produtos/{produto_id}")
async def atualizar_produto(produto_id: int, req: ProdutoRequest, usuario: dict = Depends(usuario_atual)):
    existente = await database.obter_produto(produto_id, usuario["id"])
    if not existente:
        raise HTTPException(status_code=404, detail="Produto nao encontrado")
    produto = await database.atualizar_produto(produto_id, {
        "nome": req.nome,
        "preco": req.preco,
        "categoria": req.categoria,
        "descricao": req.descricao or "",
        "data_fabricacao": req.data_fabricacao,
        "data_validade": req.data_validade,
        "codigo_barras": req.codigo_barras,
        "estoque": req.estoque,
        "foto_url": req.foto_url,
        "unidade": req.unidade,
    }, usuario["id"])
    produto["preco_formatado"] = formatar_moeda(produto["preco"])
    if produto.get("data_validade"):
        produto["dias_para_vencer"] = _calcular_dias_validade(produto["data_validade"])
        produto["status_validade"] = _status_validade(produto["data_validade"])
    return {"sucesso": True, "produto": produto}


@app.delete("/api/produtos/{produto_id}")
async def excluir_produto(produto_id: int, usuario: dict = Depends(usuario_atual)):
    await database.excluir_produto(produto_id, usuario["id"])
    return {"sucesso": True, "mensagem": "Produto excluido"}


@app.post("/api/produtos/{produto_id}/foto")
async def upload_foto_produto(produto_id: int, arquivo: UploadFile = File(...), usuario: dict = Depends(usuario_atual)):
    produto = await database.obter_produto(produto_id, usuario["id"])
    if not produto:
        raise HTTPException(status_code=404, detail="Produto nao encontrado")

    conteudo = await arquivo.read()
    if len(conteudo) > LIMITES_UPLOAD["tamanho_max"]:
        raise HTTPException(status_code=413, detail="Imagem muito grande: maximo de 2 MB.")
    if not conteudo:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")

    ext = _detectar_imagem(arquivo.content_type, conteudo)
    if not ext:
        raise HTTPException(
            status_code=415,
            detail="Formato de imagem invalido. Use JPEG, PNG ou WebP.",
        )

    upload_dir = os.path.join("static", "uploads", "produtos")
    os.makedirs(upload_dir, exist_ok=True)

    nome_arquivo = f"{uuid.uuid4().hex}{ext}"
    caminho = os.path.join(upload_dir, nome_arquivo)

    with open(caminho, "wb") as buffer:
        shutil.copyfileobj(arquivo.file, buffer)

    foto_url = f"/static/uploads/produtos/{nome_arquivo}"
    produto["foto_url"] = foto_url
    await database.atualizar_produto(produto_id, produto, usuario["id"])

    return {"sucesso": True, "foto_url": foto_url, "produto": produto}


@app.post("/api/scan-codigo")
async def scan_codigo(req: ScanCodigoRequest, usuario: dict = Depends(usuario_atual)):
    return {
        "sucesso": True,
        "codigo_detectado": req.codigo,
        "usuario_id": usuario["id"],
        "mensagem": "Endpoint placeholder - integracao com IA pendente"
    }


# ── Endpoints de Registro de Vendas ──────────────────────────────────────────

@app.post("/api/vendas")
async def registrar_venda(req: VendaRequest, usuario: dict = Depends(usuario_atual)):
    plano = await _plano_usuario(usuario["id"])
    limite = PLANO_LIMITES[plano]["vendas"]
    total = await database.contar_vendas_total(usuario["id"])
    if total >= limite:
        raise HTTPException(
            status_code=422,
            detail=f"Limite do plano {plano.upper()} atingido: {limite} vendas. "
                   "Exclua registros ou faca upgrade para o PRO."
        )
    data_venda = req.data or datetime.now().strftime("%Y-%m-%d")

    produto_info = None
    if req.produto_id:
        p = await database.obter_produto(req.produto_id, usuario["id"])
        if p:
            produto_info = {"id": p["id"], "nome": p["nome"], "preco_unitario": p["preco"]}

    valor_total = req.valor * req.quantidade

    cliente_info = None
    if req.cliente_id:
        c = await database.obter_cliente(req.cliente_id, usuario["id"])
        if c:
            cliente_info = {"id": c["id"], "nome": c["nome"]}

    venda = await database.criar_venda({
        "produto_id": req.produto_id,
        "descricao": req.descricao,
        "valor": valor_total,
        "quantidade": req.quantidade,
        "data": data_venda,
        "cliente": req.cliente or "",
        "cliente_id": req.cliente_id,
    }, usuario["id"])
    venda["valor_unitario"] = req.valor
    venda["valor_formatado"] = formatar_moeda(valor_total)
    venda["produto"] = produto_info
    venda["cliente_info"] = cliente_info

    return {"sucesso": True, "venda": venda}


@app.get("/api/vendas")
async def listar_vendas(mes: Optional[int] = None, ano: Optional[int] = None, usuario: dict = Depends(usuario_atual)):
    vendas = await database.listar_vendas(usuario["id"], mes=mes, ano=ano)
    total = sum(v["valor"] for v in vendas)
    for v in vendas:
        v["valor_formatado"] = formatar_moeda(v["valor"])

    return {
        "sucesso": True,
        "vendas": vendas,
        "total": total,
        "total_formatado": formatar_moeda(total),
        "quantidade": len(vendas)
    }


@app.delete("/api/vendas/{venda_id}")
async def excluir_venda(venda_id: int, usuario: dict = Depends(usuario_atual)):
    await database.excluir_venda(venda_id, usuario["id"])
    return {"sucesso": True, "mensagem": "Venda excluida"}


@app.post("/api/despesas")
async def registrar_despesa(req: DespesaRequest, usuario: dict = Depends(usuario_atual)):
    plano = await _plano_usuario(usuario["id"])
    limite = PLANO_LIMITES[plano]["despesas"]
    total = await database.contar_despesas_total(usuario["id"])
    if total >= limite:
        raise HTTPException(
            status_code=422,
            detail=f"Limite do plano {plano.upper()} atingido: {limite} despesas. "
                   "Exclua registros ou faca upgrade para o PRO."
        )
    data_despesa = req.data or datetime.now().strftime("%Y-%m-%d")

    despesa = await database.criar_despesa({
        "descricao": req.descricao,
        "valor": req.valor,
        "data": data_despesa,
        "categoria": req.categoria,
    }, usuario["id"])
    despesa["valor_formatado"] = formatar_moeda(despesa["valor"])

    return {"sucesso": True, "despesa": despesa}


@app.get("/api/despesas")
async def listar_despesas(mes: Optional[int] = None, ano: Optional[int] = None, usuario: dict = Depends(usuario_atual)):
    despesas = await database.listar_despesas(usuario["id"], mes=mes, ano=ano)
    total = sum(d["valor"] for d in despesas)
    for d in despesas:
        d["valor_formatado"] = formatar_moeda(d["valor"])

    return {
        "sucesso": True,
        "despesas": despesas,
        "total": total,
        "total_formatado": formatar_moeda(total),
        "quantidade": len(despesas)
    }


@app.delete("/api/despesas/{despesa_id}")
async def excluir_despesa(despesa_id: int, usuario: dict = Depends(usuario_atual)):
    await database.excluir_despesa(despesa_id, usuario["id"])
    return {"sucesso": True, "mensagem": "Despesa excluida"}


@app.get("/api/clientes")
async def listar_clientes(q: Optional[str] = None, usuario: dict = Depends(usuario_atual)):
    clientes = await database.listar_clientes(usuario["id"], busca=q)
    return {"sucesso": True, "clientes": clientes, "total": len(clientes)}


@app.post("/api/clientes")
async def cadastrar_cliente(req: ClienteRequest, usuario: dict = Depends(usuario_atual)):
    plano = await _plano_usuario(usuario["id"])
    limite = PLANO_LIMITES[plano]["clientes"]
    total = await database.contar_clientes(usuario["id"])
    if total >= limite:
        raise HTTPException(
            status_code=422,
            detail=f"Limite do plano {plano.upper()} atingido: {limite} clientes. "
                   "Exclua registros ou faca upgrade para o PRO."
        )
    cliente = await database.criar_cliente({
        "nome": req.nome,
        "telefone": req.telefone,
        "email": req.email,
        "data_aniversario": req.data_aniversario,
        "endereco": req.endereco,
        "observacoes": req.observacoes or "",
        "produto_preferido": req.produto_preferido,
        "periodicidade": req.periodicidade,
    }, usuario["id"])
    cliente["total_compras"] = 0
    cliente["total_compras_formatado"] = formatar_moeda(0)
    return {"sucesso": True, "cliente": cliente}


@app.get("/api/clientes/aniversarios")
async def clientes_aniversarios(usuario: dict = Depends(usuario_atual)):
    mes_atual = datetime.now().month
    aniversariantes = await database.clientes_aniversario_mes(usuario["id"], mes_atual)
    return {"sucesso": True, "clientes": aniversariantes, "total": len(aniversariantes), "mes": mes_atual}


@app.get("/api/clientes/{cliente_id}")
async def obter_cliente(cliente_id: int, usuario: dict = Depends(usuario_atual)):
    cliente = await database.obter_cliente(cliente_id, usuario["id"])
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente nao encontrado")
    return {"sucesso": True, "cliente": cliente}


@app.put("/api/clientes/{cliente_id}")
async def atualizar_cliente(cliente_id: int, req: ClienteRequest, usuario: dict = Depends(usuario_atual)):
    cliente = await database.atualizar_cliente(cliente_id, {
        "nome": req.nome,
        "telefone": req.telefone,
        "email": req.email,
        "data_aniversario": req.data_aniversario,
        "endereco": req.endereco,
        "observacoes": req.observacoes or "",
        "produto_preferido": req.produto_preferido,
        "periodicidade": req.periodicidade,
    }, usuario["id"])
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente nao encontrado")
    return {"sucesso": True, "cliente": cliente}


@app.delete("/api/clientes/{cliente_id}")
async def excluir_cliente(cliente_id: int, usuario: dict = Depends(usuario_atual)):
    await database.excluir_cliente(cliente_id, usuario["id"])
    return {"sucesso": True, "mensagem": "Cliente excluido"}


@app.get("/api/clientes/{cliente_id}/compras")
async def historico_compras_cliente(cliente_id: int, usuario: dict = Depends(usuario_atual)):
    cliente = await database.obter_cliente(cliente_id, usuario["id"])
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente nao encontrado")
    todas_vendas = await database.listar_vendas(usuario["id"])
    compras = [v for v in todas_vendas if v.get("cliente_id") == cliente_id]
    total = sum(v["valor"] for v in compras)
    for v in compras:
        v["valor_formatado"] = formatar_moeda(v["valor"])
    return {
        "sucesso": True,
        "cliente": cliente,
        "compras": compras,
        "total": total,
        "total_formatado": formatar_moeda(total),
        "quantidade": len(compras)
    }


@app.get("/api/resumo-mensal")
async def resumo_mensal(mes: int, ano: int, tipo_atividade: str = "servico", usuario: dict = Depends(usuario_atual)):
    vendas_mes = await database.listar_vendas(usuario["id"], mes=mes, ano=ano)
    total_vendas = sum(v["valor"] for v in vendas_mes)

    despesas_mes = await database.listar_despesas(usuario["id"], mes=mes, ano=ano)
    total_despesas = sum(d["valor"] for d in despesas_mes)
    despesas_fixas = sum(d["valor"] for d in despesas_mes if d["categoria"] == "fixa")
    despesas_variaveis = sum(d["valor"] for d in despesas_mes if d["categoria"] == "variavel")

    resultado_das = calcular_das(mes, ano, total_vendas, tipo_atividade)
    valor_das = resultado_das.valor_total

    lucro_bruto = total_vendas - total_despesas
    lucro_liquido = lucro_bruto - valor_das
    margem = (lucro_liquido / total_vendas * 100) if total_vendas > 0 else 0

    if total_vendas > 0:
        eficiencia = min(100, max(0, (lucro_liquido / total_vendas) * 100 * 2.5))
    else:
        eficiencia = 0

    if eficiencia >= 60:
        status = "otimo"
        status_msg = "Excelente! Seu MEI esta muito lucrativo."
    elif eficiencia >= 40:
        status = "bom"
        status_msg = "Bom! Mas ha espaco para melhorar."
    elif eficiencia >= 20:
        status = "medio"
        status_msg = "Regular. Revise seus custos."
    else:
        status = "ruim"
        status_msg = "Atencao! Lucro muito baixo."

    return {
        "sucesso": True,
        "mes": mes,
        "ano": ano,
        "vendas": {
            "quantidade": len(vendas_mes),
            "total": total_vendas,
            "total_formatado": formatar_moeda(total_vendas)
        },
        "despesas": {
            "quantidade": len(despesas_mes),
            "total": total_despesas,
            "fixas": despesas_fixas,
            "variaveis": despesas_variaveis,
            "total_formatado": formatar_moeda(total_despesas)
        },
        "das": {
            "valor": valor_das,
            "valor_formatado": formatar_moeda(valor_das),
            "data_vencimento": resultado_das.data_vencimento,
            "dentro_do_teto": resultado_das.dentro_do_teto,
            "pode_emitir_nfe": resultado_das.pode_emitir_nfe
        },
        "lucro": {
            "bruto": lucro_bruto,
            "bruto_formatado": formatar_moeda(lucro_bruto),
            "liquido": lucro_liquido,
            "liquido_formatado": formatar_moeda(lucro_liquido),
            "margem": round(margem, 1)
        },
        "eficiencia": {
            "percentual": round(eficiencia, 1),
            "status": status,
            "mensagem": status_msg
        }
    }


@app.get("/api/resumo-anual")
async def resumo_anual(ano: int, tipo_atividade: str = "servico", usuario: dict = Depends(usuario_atual)):
    mesesDados = []
    total_vendas_ano = 0
    total_despesas_ano = 0
    total_das_ano = 0

    for mes in range(1, 13):
        vendas_mes_dados = await database.listar_vendas(usuario["id"], mes=mes, ano=ano)
        vendas_mes = sum(v["valor"] for v in vendas_mes_dados)
        despesas_mes_dados = await database.listar_despesas(usuario["id"], mes=mes, ano=ano)
        despesas_mes = sum(d["valor"] for d in despesas_mes_dados)
        das_mes = calcular_das(mes, ano, vendas_mes, tipo_atividade).valor_total

        total_vendas_ano += vendas_mes
        total_despesas_ano += despesas_mes
        total_das_ano += das_mes

        mesesDados.append({
            "mes": mes,
            "vendas": vendas_mes,
            "despesas": despesas_mes,
            "das": das_mes,
            "lucro": vendas_mes - despesas_mes - das_mes
        })

    lucro_liquido_ano = total_vendas_ano - total_despesas_ano - total_das_ano
    margem_ano = (lucro_liquido_ano / total_vendas_ano * 100) if total_vendas_ano > 0 else 0
    dentro_teto = total_vendas_ano <= TETO_ANUAL_2025

    return {
        "sucesso": True,
        "ano": ano,
        "resumo": {
            "total_vendas": total_vendas_ano,
            "total_vendas_fmt": formatar_moeda(total_vendas_ano),
            "total_despesas": total_despesas_ano,
            "total_despesas_fmt": formatar_moeda(total_despesas_ano),
            "total_das": total_das_ano,
            "total_das_fmt": formatar_moeda(total_das_ano),
            "lucro_liquido": lucro_liquido_ano,
            "lucro_liquido_fmt": formatar_moeda(lucro_liquido_ano),
            "margem": round(margem_ano, 1),
            "dentro_do_teto": dentro_teto
        },
        "meses": mesesDados
    }


@app.get("/api/faturamento-anual")
async def faturamento_anual(ano: int, usuario: dict = Depends(usuario_atual)):
    por_mes = {}
    total = 0

    for mes in range(1, 13):
        vendas_mes_dados = await database.listar_vendas(usuario["id"], mes=mes, ano=ano)
        vendas_mes = sum(v["valor"] for v in vendas_mes_dados)
        por_mes[mes] = vendas_mes
        total += vendas_mes

    return {
        "sucesso": True,
        "ano": ano,
        "total": total,
        "total_formatado": formatar_moeda(total),
        "por_mes": por_mes,
        "limite": TETO_ANUAL_2025,
        "limite_formatado": formatar_moeda(TETO_ANUAL_2025)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)