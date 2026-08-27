"""
Calculadora MEI - Database PostgreSQL
Conexao com o mesmo banco do SISGERSA (tabelas separadas com prefixo 'mei_')
"""
import os
import asyncpg
from datetime import datetime

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://sisgersa_app:ixnU2aktneWNQhJoqiiKRQs033NSUnM5@dpg-d9hqikr7uimc73dt3e0g-a.oregon-postgres.render.com/sisgersa"
)

pool = None


async def get_pool():
    global pool
    if pool is None:
        pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
    return pool


async def init_db():
    """Cria tabelas se nao existirem (prefixo mei_ para isolar do SISGERSA)."""
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS mei_produtos (
                id SERIAL PRIMARY KEY,
                nome TEXT NOT NULL,
                preco REAL NOT NULL,
                categoria TEXT DEFAULT 'servico',
                descricao TEXT DEFAULT '',
                data_fabricacao TEXT,
                data_validade TEXT,
                codigo_barras TEXT,
                estoque INTEGER DEFAULT 0,
                foto_url TEXT,
                unidade TEXT DEFAULT 'un',
                criado_em TEXT DEFAULT (NOW()::TEXT)
            );

            CREATE TABLE IF NOT EXISTS mei_vendas (
                id SERIAL PRIMARY KEY,
                produto_id INTEGER,
                descricao TEXT NOT NULL,
                valor REAL NOT NULL,
                quantidade INTEGER DEFAULT 1,
                data TEXT NOT NULL,
                cliente TEXT DEFAULT '',
                cliente_id INTEGER,
                criado_em TEXT DEFAULT (NOW()::TEXT)
            );

            CREATE TABLE IF NOT EXISTS mei_despesas (
                id SERIAL PRIMARY KEY,
                descricao TEXT NOT NULL,
                valor REAL NOT NULL,
                data TEXT,
                categoria TEXT DEFAULT 'fixa',
                criado_em TEXT DEFAULT (NOW()::TEXT)
            );

            CREATE TABLE IF NOT EXISTS mei_clientes (
                id SERIAL PRIMARY KEY,
                nome TEXT NOT NULL,
                telefone TEXT,
                email TEXT,
                data_aniversario TEXT,
                endereco TEXT,
                observacoes TEXT DEFAULT '',
                produto_preferido TEXT,
                periodicidade TEXT,
                criado_em TEXT DEFAULT (NOW()::TEXT)
            );

            CREATE TABLE IF NOT EXISTS mei_assinaturas (
                id SERIAL PRIMARY KEY,
                cliente_id INTEGER,
                email TEXT,
                nome TEXT,
                status TEXT DEFAULT 'pendente',
                mp_subscription_id TEXT,
                data_inicio TEXT,
                data_fim TEXT,
                proximo_pagamento TEXT,
                criado_em TEXT DEFAULT (NOW()::TEXT)
            );
        """)
    print("[DB] Tabelas mei_* criadas/verificadas com sucesso!")


# ── CRUD Produtos ────────────────────────────────────────────────────────────

async def criar_produto(dados: dict) -> dict:
    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO mei_produtos (nome, preco, categoria, descricao, data_fabricacao, data_validade, codigo_barras, estoque, foto_url, unidade)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
            RETURNING id
        """, dados['nome'], dados['preco'], dados.get('categoria','servico'),
             dados.get('descricao',''), dados.get('data_fabricacao'),
             dados.get('data_validade'), dados.get('codigo_barras'),
             dados.get('estoque',0), dados.get('foto_url'), dados.get('unidade','un'))
        dados['id'] = row['id']
        return dados


async def listar_produtos() -> list:
    p = await get_pool()
    async with p.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM mei_produtos ORDER BY id DESC")
        return [dict(r) for r in rows]


async def obter_produto(produto_id: int) -> dict | None:
    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM mei_produtos WHERE id=$1", produto_id)
        return dict(row) if row else None


async def atualizar_produto(produto_id: int, dados: dict) -> dict | None:
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute("""
            UPDATE mei_produtos SET nome=$1, preco=$2, categoria=$3, descricao=$4,
            data_fabricacao=$5, data_validade=$6, codigo_barras=$7, estoque=$8,
            foto_url=$9, unidade=$10 WHERE id=$11
        """, dados['nome'], dados['preco'], dados.get('categoria','servico'),
             dados.get('descricao',''), dados.get('data_fabricacao'),
             dados.get('data_validade'), dados.get('codigo_barras'),
             dados.get('estoque',0), dados.get('foto_url'), dados.get('unidade','un'), produto_id)
        return await obter_produto(produto_id)


async def excluir_produto(produto_id: int):
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute("DELETE FROM mei_produtos WHERE id=$1", produto_id)


# ── CRUD Vendas ──────────────────────────────────────────────────────────────

async def criar_venda(dados: dict) -> dict:
    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO mei_vendas (produto_id, descricao, valor, quantidade, data, cliente, cliente_id)
            VALUES ($1,$2,$3,$4,$5,$6,$7)
            RETURNING id
        """, dados.get('produto_id'), dados['descricao'], dados['valor'],
             dados.get('quantidade',1), dados['data'],
             dados.get('cliente',''), dados.get('cliente_id'))
        dados['id'] = row['id']
        return dados


async def listar_vendas(mes: int = None, ano: int = None) -> list:
    p = await get_pool()
    async with p.acquire() as conn:
        if mes and ano:
            prefixo = f"{ano}-{mes:02d}"
            rows = await conn.fetch(
                "SELECT * FROM mei_vendas WHERE data LIKE $1 ORDER BY id DESC",
                f"{prefixo}%"
            )
        else:
            rows = await conn.fetch("SELECT * FROM mei_vendas ORDER BY id DESC")
        return [dict(r) for r in rows]


async def excluir_venda(venda_id: int):
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute("DELETE FROM mei_vendas WHERE id=$1", venda_id)


# ── CRUD Despesas ────────────────────────────────────────────────────────────

async def criar_despesa(dados: dict) -> dict:
    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO mei_despesas (descricao, valor, data, categoria)
            VALUES ($1,$2,$3,$4)
            RETURNING id
        """, dados['descricao'], dados['valor'], dados.get('data'), dados.get('categoria','fixa'))
        dados['id'] = row['id']
        return dados


async def listar_despesas(mes: int = None, ano: int = None) -> list:
    p = await get_pool()
    async with p.acquire() as conn:
        if mes and ano:
            prefixo = f"{ano}-{mes:02d}"
            rows = await conn.fetch(
                "SELECT * FROM mei_despesas WHERE data LIKE $1 ORDER BY id DESC",
                f"{prefixo}%"
            )
        else:
            rows = await conn.fetch("SELECT * FROM mei_despesas ORDER BY id DESC")
        return [dict(r) for r in rows]


async def excluir_despesa(despesa_id: int):
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute("DELETE FROM mei_despesas WHERE id=$1", despesa_id)


# ── CRUD Clientes ────────────────────────────────────────────────────────────

async def criar_cliente(dados: dict) -> dict:
    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO mei_clientes (nome, telefone, email, data_aniversario, endereco, observacoes, produto_preferido, periodicidade)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
            RETURNING id
        """, dados['nome'], dados.get('telefone'), dados.get('email'),
             dados.get('data_aniversario'), dados.get('endereco'),
             dados.get('observacoes',''), dados.get('produto_preferido'),
             dados.get('periodicidade'))
        dados['id'] = row['id']
        return dados


async def listar_clientes(busca: str = None) -> list:
    p = await get_pool()
    async with p.acquire() as conn:
        if busca:
            rows = await conn.fetch(
                "SELECT * FROM mei_clientes WHERE nome ILIKE $1 ORDER BY id DESC",
                f"%{busca}%"
            )
        else:
            rows = await conn.fetch("SELECT * FROM mei_clientes ORDER BY id DESC")
        return [dict(r) for r in rows]


async def obter_cliente(cliente_id: int) -> dict | None:
    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM mei_clientes WHERE id=$1", cliente_id)
        return dict(row) if row else None


async def excluir_cliente(cliente_id: int):
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute("DELETE FROM mei_clientes WHERE id=$1", cliente_id)


async def clientes_aniversario_mes(mes_atual: int) -> list:
    p = await get_pool()
    async with p.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM mei_clientes WHERE EXTRACT(MONTH FROM data_aniversario::DATE) = $1",
            mes_atual
        )
        return [dict(r) for r in rows]


# ── CRUD Assinaturas ─────────────────────────────────────────────────────────

async def criar_assinatura(dados: dict) -> dict:
    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO mei_assinaturas (cliente_id, email, nome, status, mp_subscription_id)
            VALUES ($1,$2,$3,$4,$5)
            RETURNING id
        """, dados.get('cliente_id'), dados.get('email'), dados.get('nome'),
             dados.get('status','pendente'), dados.get('mp_subscription_id'))
        dados['id'] = row['id']
        return dados


async def obter_assinatura_cliente(cliente_id: int) -> dict | None:
    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM mei_assinaturas WHERE cliente_id=$1 AND status='ativa' ORDER BY id DESC LIMIT 1",
            cliente_id
        )
        return dict(row) if row else None


async def cancelar_assinatura(cliente_id: int):
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute(
            "UPDATE mei_assinaturas SET status='cancelada' WHERE cliente_id=$1 AND status='ativa'",
            cliente_id
        )


async def contar_assinaturas_ativas() -> int:
    p = await get_pool()
    async with p.acquire() as conn:
        result = await conn.fetchval("SELECT COUNT(*) FROM mei_assinaturas WHERE status='ativa'")
        return result or 0
