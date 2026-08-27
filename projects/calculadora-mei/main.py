"""
Calculadora de MEI - Backend API
FastAPI server com endpoints para calculos DAS, simulacoes, alertas e registro de vendas
"""
from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from collections import defaultdict
import json
import os
import shutil
import uuid
import httpx
import database

MERCADO_PAGO_TOKEN = os.environ.get("MP_ACCESS_TOKEN", "TEST-xxx")
MERCADO_PAGO_PUBLIC_KEY = os.environ.get("MP_PUBLIC_KEY", "TEST-xxx")
PRECO_PRO_MENSAL = 9.90

from calculadora import (
    calcular_das,
    simular_cenarios,
    obter_alertas_vencimento,
    formatar_moeda,
    CenarioSimulacao,
    TABELA_DAS_2025,
    TETO_ANUAL_2025,
    TETO_MENSAL_2025,
)

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app):
    await database.init_db()
    yield

app = FastAPI(
    title="Calculadora MEI",
    description="Calculadora de DAS para Microempreendedores Individuais",
    version="1.0.0",
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
    cliente_id: int
    email: str
    nome: str


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
        "version": "1.0.0",
        "teto_anual": TETO_ANUAL_2025,
        "teto_mensal": round(TETO_MENSAL_2025, 2),
        "tabela_das": TABELA_DAS_2025,
        "assinaturas_ativas": assinaturas,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/api/assinatura/checkout")
async def criar_checkout(req: AssinaturaRequest):
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://api.mercadopago.com/checkout/preferences",
            headers={
                "Authorization": f"Bearer {MERCADO_PAGO_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "items": [{
                    "title": "Calculadora MEI - Plano PRO",
                    "quantity": 1,
                    "unit_price": PRECO_PRO_MENSAL
                }],
                "payer": {
                    "email": req.email,
                    "name": req.nome
                },
                "metadata": {
                    "cliente_id": req.cliente_id
                }
            }
        )
        dados = resp.json()
        checkout_url = dados.get("init_point")

        await database.criar_assinatura({
            "cliente_id": req.cliente_id,
            "email": req.email,
            "nome": req.nome,
            "status": "pendente",
            "mp_subscription_id": dados.get("id")
        })

        return {
            "sucesso": True,
            "checkout_url": checkout_url,
            "preference_id": dados.get("id"),
            "valor": PRECO_PRO_MENSAL
        }


@app.post("/api/webhook/mercadopago")
async def webhook_mercadopago(request: Request):
    body = await request.json()
    tipo = body.get("type", "")
    dados = body.get("data", {})

    if tipo == "payment":
        payment_id = dados.get("id")
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://api.mercadopago.com/v1/payments/{payment_id}",
                headers={"Authorization": f"Bearer {MERCADO_PAGO_TOKEN}"}
            )
            if resp.status_code == 200:
                pagamento = resp.json()
                status = pagamento.get("status")
                if status == "approved":
                    metadata = pagamento.get("metadata", {})
                    cliente_id = metadata.get("cliente_id")
                    if cliente_id:
                        assinatura = await database.obter_assinatura_cliente(cliente_id)
                        if assinatura:
                            p = await database.get_pool()
                            async with p.acquire() as conn:
                                await conn.execute(
                                    "UPDATE mei_assinaturas SET status='ativa', data_inicio=NOW()::TEXT WHERE id=$1",
                                    assinatura["id"]
                                )

    return {"sucesso": True, "processado": True}


@app.get("/api/assinatura/{cliente_id}")
async def verificar_assinatura(cliente_id: int):
    from database import obter_assinatura_cliente
    assinatura = await obter_assinatura_cliente(cliente_id)
    if not assinatura:
        return {
            "sucesso": True,
            "ativo": False,
            "plano": "free",
            "mensagem": "Sem assinatura ativa"
        }
    return {
        "sucesso": True,
        "ativo": assinatura["status"] == "ativa",
        "plano": "pro" if assinatura["status"] == "ativa" else "free",
        "assinatura": assinatura
    }


@app.post("/api/assinatura/{cliente_id}/cancelar")
async def cancelar_assinatura_endpoint(cliente_id: int):
    from database import cancelar_assinatura, obter_assinatura_cliente
    assinatura = await obter_assinatura_cliente(cliente_id)
    if not assinatura:
        raise HTTPException(status_code=404, detail="Assinatura nao encontrada")
    await cancelar_assinatura(cliente_id)
    return {"sucesso": True, "mensagem": "Assinatura cancelada"}


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
                meses=c.get("meses", 12)
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
async def cadastrar_produto(req: ProdutoRequest):
    from database import criar_produto
    produto = await criar_produto({
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
    })
    produto["preco_formatado"] = formatar_moeda(produto["preco"])
    if produto.get("data_validade"):
        produto["dias_para_vencer"] = _calcular_dias_validade(produto["data_validade"])
        produto["status_validade"] = _status_validade(produto["data_validade"])
    return {"sucesso": True, "produto": produto}


@app.get("/api/produtos")
async def listar_produtos():
    from database import listar_produtos as db_listar
    produtos = await db_listar()
    for p in produtos:
        p["preco_formatado"] = formatar_moeda(p["preco"])
        if p.get("data_validade"):
            p["dias_para_vencer"] = _calcular_dias_validade(p["data_validade"])
            p["status_validade"] = _status_validade(p["data_validade"])
    return {"sucesso": True, "produtos": produtos, "total": len(produtos)}


@app.get("/api/produtos/{produto_id}")
async def obter_produto(produto_id: int):
    from database import obter_produto as db_obter
    produto = await db_obter(produto_id)
    if not produto:
        raise HTTPException(status_code=404, detail="Produto nao encontrado")
    produto["preco_formatado"] = formatar_moeda(produto["preco"])
    if produto.get("data_validade"):
        produto["dias_para_vencer"] = _calcular_dias_validade(produto["data_validade"])
        produto["status_validade"] = _status_validade(produto["data_validade"])
    return {"sucesso": True, "produto": produto}


@app.put("/api/produtos/{produto_id}")
async def atualizar_produto(produto_id: int, req: ProdutoRequest):
    from database import atualizar_produto as db_atualizar, obter_produto as db_obter
    existente = await db_obter(produto_id)
    if not existente:
        raise HTTPException(status_code=404, detail="Produto nao encontrado")
    produto = await db_atualizar(produto_id, {
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
    })
    produto["preco_formatado"] = formatar_moeda(produto["preco"])
    if produto.get("data_validade"):
        produto["dias_para_vencer"] = _calcular_dias_validade(produto["data_validade"])
        produto["status_validade"] = _status_validade(produto["data_validade"])
    return {"sucesso": True, "produto": produto}


@app.delete("/api/produtos/{produto_id}")
async def excluir_produto(produto_id: int):
    from database import excluir_produto
    await excluir_produto(produto_id)
    return {"sucesso": True, "mensagem": "Produto excluido"}


@app.post("/api/produtos/{produto_id}/foto")
async def upload_foto_produto(produto_id: int, arquivo: UploadFile = File(...)):
    from database import obter_produto, atualizar_produto
    produto = await obter_produto(produto_id)
    if not produto:
        raise HTTPException(status_code=404, detail="Produto nao encontrado")

    upload_dir = os.path.join("static", "uploads", "produtos")
    os.makedirs(upload_dir, exist_ok=True)

    ext = os.path.splitext(arquivo.filename)[1] if arquivo.filename else ".jpg"
    nome_arquivo = f"{uuid.uuid4().hex}{ext}"
    caminho = os.path.join(upload_dir, nome_arquivo)

    with open(caminho, "wb") as buffer:
        shutil.copyfileobj(arquivo.file, buffer)

    foto_url = f"/static/uploads/produtos/{nome_arquivo}"
    produto["foto_url"] = foto_url
    await atualizar_produto(produto_id, produto)

    return {"sucesso": True, "foto_url": foto_url, "produto": produto}


class ScanCodigoRequest(BaseModel):
    imagem_base64: Optional[str] = Field(None, description="Imagem em base64")
    codigo: Optional[str] = Field(None, description="Codigo ja detectado")


@app.post("/api/scan-codigo")
async def scan_codigo(req: ScanCodigoRequest):
    return {
        "sucesso": True,
        "codigo_detectado": req.codigo,
        "mensagem": "Endpoint placeholder - integracao com IA pendente"
    }


# ── Endpoints de Registro de Vendas ──────────────────────────────────────────

@app.post("/api/vendas")
async def registrar_venda(req: VendaRequest):
    from database import criar_venda, obter_produto, obter_cliente
    data_venda = req.data or datetime.now().strftime("%Y-%m-%d")

    produto_info = None
    if req.produto_id:
        p = await obter_produto(req.produto_id)
        if p:
            produto_info = {"id": p["id"], "nome": p["nome"], "preco_unitario": p["preco"]}

    valor_total = req.valor * req.quantidade

    cliente_info = None
    if req.cliente_id:
        c = await obter_cliente(req.cliente_id)
        if c:
            cliente_info = {"id": c["id"], "nome": c["nome"]}

    venda = await criar_venda({
        "produto_id": req.produto_id,
        "descricao": req.descricao,
        "valor": valor_total,
        "quantidade": req.quantidade,
        "data": data_venda,
        "cliente": req.cliente or "",
        "cliente_id": req.cliente_id,
    })
    venda["valor_unitario"] = req.valor
    venda["valor_formatado"] = formatar_moeda(valor_total)
    venda["produto"] = produto_info
    venda["cliente_info"] = cliente_info

    return {"sucesso": True, "venda": venda}


@app.get("/api/vendas")
async def listar_vendas(mes: Optional[int] = None, ano: Optional[int] = None):
    from database import listar_vendas as db_listar
    vendas = await db_listar(mes=mes, ano=ano)
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
async def excluir_venda(venda_id: int):
    from database import excluir_venda
    await excluir_venda(venda_id)
    return {"sucesso": True, "mensagem": "Venda excluida"}


@app.post("/api/despesas")
async def registrar_despesa(req: DespesaRequest):
    from database import criar_despesa
    data_despesa = req.data or datetime.now().strftime("%Y-%m-%d")

    despesa = await criar_despesa({
        "descricao": req.descricao,
        "valor": req.valor,
        "data": data_despesa,
        "categoria": req.categoria,
    })
    despesa["valor_formatado"] = formatar_moeda(despesa["valor"])

    return {"sucesso": True, "despesa": despesa}


@app.get("/api/despesas")
async def listar_despesas(mes: Optional[int] = None, ano: Optional[int] = None):
    from database import listar_despesas as db_listar
    despesas = await db_listar(mes=mes, ano=ano)
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
async def excluir_despesa(despesa_id: int):
    from database import excluir_despesa
    await excluir_despesa(despesa_id)
    return {"sucesso": True, "mensagem": "Despesa excluida"}


@app.get("/api/clientes")
async def listar_clientes(q: Optional[str] = None):
    from database import listar_clientes as db_listar
    clientes = await db_listar(busca=q)
    return {"sucesso": True, "clientes": clientes, "total": len(clientes)}


@app.post("/api/clientes")
async def cadastrar_cliente(req: ClienteRequest):
    from database import criar_cliente
    cliente = await criar_cliente({
        "nome": req.nome,
        "telefone": req.telefone,
        "email": req.email,
        "data_aniversario": req.data_aniversario,
        "endereco": req.endereco,
        "observacoes": req.observacoes or "",
        "produto_preferido": req.produto_preferido,
        "periodicidade": req.periodicidade,
    })
    cliente["total_compras"] = 0
    cliente["total_compras_formatado"] = formatar_moeda(0)
    return {"sucesso": True, "cliente": cliente}


@app.get("/api/clientes/aniversarios")
async def clientes_aniversarios():
    from database import clientes_aniversario_mes
    mes_atual = datetime.now().month
    aniversariantes = await clientes_aniversario_mes(mes_atual)
    return {"sucesso": True, "clientes": aniversariantes, "total": len(aniversariantes), "mes": mes_atual}


@app.get("/api/clientes/{cliente_id}")
async def obter_cliente(cliente_id: int):
    from database import obter_cliente as db_obter
    cliente = await db_obter(cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente nao encontrado")
    return {"sucesso": True, "cliente": cliente}


@app.put("/api/clientes/{cliente_id}")
async def atualizar_cliente(cliente_id: int, req: ClienteRequest):
    from database import obter_cliente, criar_cliente, excluir_cliente
    existente = await obter_cliente(cliente_id)
    if not existente:
        raise HTTPException(status_code=404, detail="Cliente nao encontrado")
    await excluir_cliente(cliente_id)
    cliente = await criar_cliente({
        "nome": req.nome,
        "telefone": req.telefone,
        "email": req.email,
        "data_aniversario": req.data_aniversario,
        "endereco": req.endereco,
        "observacoes": req.observacoes or "",
        "produto_preferido": req.produto_preferido,
        "periodicidade": req.periodicidade,
    })
    return {"sucesso": True, "cliente": cliente}


@app.delete("/api/clientes/{cliente_id}")
async def excluir_cliente(cliente_id: int):
    from database import excluir_cliente
    await excluir_cliente(cliente_id)
    return {"sucesso": True, "mensagem": "Cliente excluido"}


@app.get("/api/clientes/{cliente_id}/compras")
async def historico_compras_cliente(cliente_id: int):
    from database import obter_cliente, listar_vendas
    cliente = await obter_cliente(cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente nao encontrado")
    todas_vendas = await listar_vendas()
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
async def resumo_mensal(mes: int, ano: int, tipo_atividade: str = "servico"):
    from database import listar_vendas, listar_despesas
    vendas_mes = await listar_vendas(mes=mes, ano=ano)
    total_vendas = sum(v["valor"] for v in vendas_mes)

    despesas_mes = await listar_despesas(mes=mes, ano=ano)
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
async def resumo_anual(ano: int, tipo_atividade: str = "servico"):
    from database import listar_vendas, listar_despesas
    mesesDados = []
    total_vendas_ano = 0
    total_despesas_ano = 0
    total_das_ano = 0

    for mes in range(1, 13):
        vendas_mes_dados = await listar_vendas(mes=mes, ano=ano)
        vendas_mes = sum(v["valor"] for v in vendas_mes_dados)
        despesas_mes_dados = await listar_despesas(mes=mes, ano=ano)
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
async def faturamento_anual(ano: int):
    from database import listar_vendas
    por_mes = {}
    total = 0

    for mes in range(1, 13):
        vendas_mes_dados = await listar_vendas(mes=mes, ano=ano)
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
