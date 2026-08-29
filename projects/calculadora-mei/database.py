"""
Calculadora MEI - Database PostgreSQL
Conexao com o mesmo banco do SISGERSA (tabelas separadas com prefixo 'mei_')
"""
import os
import re
import ssl
import asyncpg
from datetime import datetime, timedelta, timezone

RAW_DATABASE_URL = os.environ.get("DATABASE_URL")
if not RAW_DATABASE_URL:
    raise RuntimeError(
        "Variável de ambiente DATABASE_URL é obrigatória (ex.: definida no Render)."
    )


def _parse_database_url(url: str) -> dict:
    """Parseia DATABASE_URL e remove sslmode (asyncpg nao aceita na string)."""
    sslmode = None
    m = re.search(r'[?&]sslmode=([^&]+)', url)
    if m:
        sslmode = m.group(1)
        url = re.sub(r'[?&]sslmode=[^&]+', '', url)
    url = url.rstrip('?&')
    return {"dsn": url, "sslmode": sslmode}


parsed = _parse_database_url(RAW_DATABASE_URL)
DATABASE_URL = parsed["dsn"]
DATABASE_SSL = parsed["sslmode"]

pool = None


async def get_pool():
    global pool
    if pool is None:
        kwargs = {"min_size": 1, "max_size": 5}
        if DATABASE_SSL == "require":
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            kwargs["ssl"] = ctx
        pool = await asyncpg.create_pool(DATABASE_URL, **kwargs)
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
                payment_id TEXT,
                renovacoes INTEGER DEFAULT 0,
                data_inicio TEXT,
                data_fim TEXT,
                proximo_pagamento TEXT,
                criado_em TEXT DEFAULT (NOW()::TEXT)
            );

            CREATE TABLE IF NOT EXISTS mei_pagamentos (
                id SERIAL PRIMARY KEY,
                payment_id TEXT UNIQUE NOT NULL,
                preference_id TEXT,
                usuario_id INTEGER,
                assinatura_id INTEGER,
                status TEXT,
                valor REAL,
                tipo TEXT DEFAULT 'inicial',
                raw TEXT DEFAULT '',
                processado_em TEXT DEFAULT (NOW()::TEXT)
            );

            CREATE TABLE IF NOT EXISTS mei_usuarios (
                id SERIAL PRIMARY KEY,
                nome TEXT,
                email TEXT UNIQUE NOT NULL,
                senha_hash TEXT NOT NULL,
                criado_em TEXT DEFAULT (NOW()::TEXT)
            );

            CREATE TABLE IF NOT EXISTS mei_sessoes (
                id SERIAL PRIMARY KEY,
                usuario_id INTEGER,
                token TEXT UNIQUE,
                criado_em TEXT DEFAULT (NOW()::TEXT),
                expira_em TEXT
            );

            CREATE TABLE IF NOT EXISTS mei_cupons (
                id SERIAL PRIMARY KEY,
                codigo TEXT UNIQUE NOT NULL,
                percentual REAL NOT NULL,
                ativo BOOLEAN DEFAULT TRUE,
                criado_em TEXT DEFAULT (NOW()::TEXT)
            );

            CREATE TABLE IF NOT EXISTS mei_reset_tokens (
                id SERIAL PRIMARY KEY,
                email TEXT NOT NULL,
                token TEXT UNIQUE NOT NULL,
                expira_em TEXT NOT NULL,
                usado BOOLEAN DEFAULT FALSE,
                criado_em TEXT DEFAULT (NOW()::TEXT)
            );
        """)

        for tabela in ("mei_produtos", "mei_vendas", "mei_despesas", "mei_clientes", "mei_assinaturas"):
            try:
                await conn.execute(f"ALTER TABLE {tabela} ADD COLUMN IF NOT EXISTS usuario_id INTEGER")
            except Exception as e:
                print(f"[DB] Aviso: coluna usuario_id em {tabela}: {e}")

        for coluna, tipo in (("payment_id", "TEXT"), ("renovacoes", "INTEGER DEFAULT 0")):
            try:
                await conn.execute(f"ALTER TABLE mei_assinaturas ADD COLUMN IF NOT EXISTS {coluna} {tipo}")
            except Exception as e:
                print(f"[DB] Aviso: coluna {coluna} em mei_assinaturas: {e}")

        await conn.execute("""
            INSERT INTO mei_cupons (codigo, percentual, ativo)
            VALUES ('TESTE100', 100, TRUE)
            ON CONFLICT (codigo) DO NOTHING
        """)

    print("[DB] Tabelas mei_* criadas/verificadas com sucesso!")


# ── Autenticacao ──────────────────────────────────────────────────────────────

async def criar_usuario(nome: str, email: str, senha_hash: str) -> dict | None:
    """Cria usuario. Retorna dict, ou None se o email ja existir."""
    p = await get_pool()
    async with p.acquire() as conn:
        try:
            row = await conn.fetchrow(
                "INSERT INTO mei_usuarios (nome, email, senha_hash) VALUES ($1,$2,$3) RETURNING id, nome, email",
                nome, email, senha_hash
            )
            return dict(row)
        except asyncpg.UniqueViolationError:
            return None


async def obter_usuario_por_email(email: str) -> dict | None:
    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, nome, email, senha_hash FROM mei_usuarios WHERE email=$1",
            email
        )
        return dict(row) if row else None


async def criar_sessao(usuario_id: int, token: str, expira_em: str):
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute(
            "INSERT INTO mei_sessoes (usuario_id, token, expira_em) VALUES ($1,$2,$3)",
            usuario_id, token, expira_em
        )


async def revogar_sessao(token: str):
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute("DELETE FROM mei_sessoes WHERE token=$1", token)


async def criar_token_reset(email: str, token: str, expira_em: str):
    """Grava token de redefinicao de senha (unico por email)."""
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute("DELETE FROM mei_reset_tokens WHERE email=$1", email)
        await conn.execute(
            "INSERT INTO mei_reset_tokens (email, token, expira_em) VALUES ($1,$2,$3)",
            email, token, expira_em
        )


async def obter_token_reset(token: str) -> dict | None:
    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, email, token, expira_em, usado FROM mei_reset_tokens WHERE token=$1",
            token
        )
        return dict(row) if row else None


async def marcar_token_reset_usado(token: str) -> None:
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute(
            "UPDATE mei_reset_tokens SET usado=TRUE WHERE token=$1", token
        )


async def limpar_token_reset(token: str) -> None:
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute("DELETE FROM mei_reset_tokens WHERE token=$1", token)


async def atualizar_senha_usuario(usuario_id: int, senha_hash: str) -> bool:
    """Atualiza a senha de um usuario (remapeamento administrativo de senha esquecida)."""
    p = await get_pool()
    async with p.acquire() as conn:
        async with conn.transaction():
            await conn.execute(
                "DELETE FROM mei_sessoes WHERE usuario_id=$1", usuario_id
            )
            result = await conn.execute(
                "UPDATE mei_usuarios SET senha_hash=$1 WHERE id=$2",
                senha_hash, usuario_id
            )
            return result.endswith(" 1")


async def excluir_usuario(usuario_id: int) -> bool:
    """Exclui a conta do usuario e todos os dados associados (direito de exclusao LGPD)."""
    p = await get_pool()
    async with p.acquire() as conn:
        async with conn.transaction():
            for tabela in ("mei_sessoes", "mei_pagamentos", "mei_assinaturas",
                           "mei_produtos", "mei_clientes", "mei_vendas", "mei_despesas"):
                try:
                    await conn.execute(f"DELETE FROM {tabela} WHERE usuario_id=$1", usuario_id)
                except Exception:
                    pass
            result = await conn.execute("DELETE FROM mei_usuarios WHERE id=$1", usuario_id)
            return result.endswith(" 1")


async def exportar_dados_usuario(usuario_id: int) -> dict:
    """Retorna todos os dados do usuario em formato estruturado (portabilidade LGPD)."""
    p = await get_pool()
    async with p.acquire() as conn:
        usuario = await conn.fetchrow(
            "SELECT id, nome, email FROM mei_usuarios WHERE id=$1", usuario_id
        )
        dados = {}
        for tabela in ("mei_produtos", "mei_clientes", "mei_vendas", "mei_despesas",
                       "mei_assinaturas", "mei_pagamentos"):
            try:
                rows = await conn.fetch(
                    f"SELECT * FROM {tabela} WHERE usuario_id=$1 ORDER BY id", usuario_id
                )
                dados[tabela] = [dict(r) for r in rows]
            except Exception:
                dados[tabela] = []
        return {"usuario": dict(usuario) if usuario else None, "tabelas": dados}


async def usuario_por_token(token: str) -> dict | None:
    """Busca sessao valida (nao expirada) e retorna o usuario."""
    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT u.id, u.nome, u.email, s.expira_em
            FROM mei_sessoes s
            JOIN mei_usuarios u ON u.id = s.usuario_id
            WHERE s.token=$1
            """,
            token
        )
        if not row:
            return None
        expira = row["expira_em"]
        if expira:
            try:
                exp_dt = datetime.fromisoformat(str(expira))
            except Exception:
                return None
            if datetime.now() > exp_dt:
                return None
        return {"id": row["id"], "nome": row["nome"], "email": row["email"]}


# ── CRUD Produtos ────────────────────────────────────────────────────────────

async def criar_produto(dados: dict, usuario_id: int) -> dict:
    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO mei_produtos (nome, preco, categoria, descricao, data_fabricacao, data_validade, codigo_barras, estoque, foto_url, unidade, usuario_id)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
            RETURNING id
        """, dados['nome'], dados['preco'], dados.get('categoria','servico'),
             dados.get('descricao',''), dados.get('data_fabricacao'),
             dados.get('data_validade'), dados.get('codigo_barras'),
             dados.get('estoque',0), dados.get('foto_url'), dados.get('unidade','un'), usuario_id)
        dados['id'] = row['id']
        return dados


async def listar_produtos(usuario_id: int) -> list:
    p = await get_pool()
    async with p.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM mei_produtos WHERE usuario_id=$1 ORDER BY id DESC", usuario_id)
        return [dict(r) for r in rows]


async def obter_produto(produto_id: int, usuario_id: int) -> dict | None:
    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM mei_produtos WHERE id=$1 AND usuario_id=$2", produto_id, usuario_id)
        return dict(row) if row else None


async def atualizar_produto(produto_id: int, dados: dict, usuario_id: int) -> dict | None:
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute("""
            UPDATE mei_produtos SET nome=$1, preco=$2, categoria=$3, descricao=$4,
            data_fabricacao=$5, data_validade=$6, codigo_barras=$7, estoque=$8,
            foto_url=$9, unidade=$10 WHERE id=$11 AND usuario_id=$12
        """, dados.get('nome'), dados.get('preco'), dados.get('categoria','servico'),
             dados.get('descricao',''), dados.get('data_fabricacao'),
             dados.get('data_validade'), dados.get('codigo_barras'),
             dados.get('estoque',0), dados.get('foto_url'), dados.get('unidade','un'), produto_id, usuario_id)
        return await obter_produto(produto_id, usuario_id)


async def excluir_produto(produto_id: int, usuario_id: int):
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute("DELETE FROM mei_produtos WHERE id=$1 AND usuario_id=$2", produto_id, usuario_id)


# ── CRUD Vendas ──────────────────────────────────────────────────────────────

async def criar_venda(dados: dict, usuario_id: int) -> dict:
    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO mei_vendas (produto_id, descricao, valor, quantidade, data, cliente, cliente_id, usuario_id)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
            RETURNING id
        """, dados.get('produto_id'), dados['descricao'], dados['valor'],
             dados.get('quantidade',1), dados['data'],
             dados.get('cliente',''), dados.get('cliente_id'), usuario_id)
        dados['id'] = row['id']
        return dados


async def listar_vendas(usuario_id: int, mes: int = None, ano: int = None) -> list:
    p = await get_pool()
    async with p.acquire() as conn:
        if mes and ano:
            prefixo = f"{ano}-{mes:02d}"
            rows = await conn.fetch(
                "SELECT * FROM mei_vendas WHERE usuario_id=$1 AND data LIKE $2 ORDER BY id DESC",
                usuario_id, f"{prefixo}%"
            )
        else:
            rows = await conn.fetch("SELECT * FROM mei_vendas WHERE usuario_id=$1 ORDER BY id DESC", usuario_id)
        return [dict(r) for r in rows]


async def excluir_venda(venda_id: int, usuario_id: int):
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute("DELETE FROM mei_vendas WHERE id=$1 AND usuario_id=$2", venda_id, usuario_id)


# ── CRUD Despesas ────────────────────────────────────────────────────────────

async def criar_despesa(dados: dict, usuario_id: int) -> dict:
    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO mei_despesas (descricao, valor, data, categoria, usuario_id)
            VALUES ($1,$2,$3,$4,$5)
            RETURNING id
        """, dados['descricao'], dados['valor'], dados.get('data'), dados.get('categoria','fixa'), usuario_id)
        dados['id'] = row['id']
        return dados


async def listar_despesas(usuario_id: int, mes: int = None, ano: int = None) -> list:
    p = await get_pool()
    async with p.acquire() as conn:
        if mes and ano:
            prefixo = f"{ano}-{mes:02d}"
            rows = await conn.fetch(
                "SELECT * FROM mei_despesas WHERE usuario_id=$1 AND data LIKE $2 ORDER BY id DESC",
                usuario_id, f"{prefixo}%"
            )
        else:
            rows = await conn.fetch("SELECT * FROM mei_despesas WHERE usuario_id=$1 ORDER BY id DESC", usuario_id)
        return [dict(r) for r in rows]


async def excluir_despesa(despesa_id: int, usuario_id: int):
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute("DELETE FROM mei_despesas WHERE id=$1 AND usuario_id=$2", despesa_id, usuario_id)


# ── CRUD Clientes ────────────────────────────────────────────────────────────

async def criar_cliente(dados: dict, usuario_id: int) -> dict:
    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO mei_clientes (nome, telefone, email, data_aniversario, endereco, observacoes, produto_preferido, periodicidade, usuario_id)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
            RETURNING id
        """, dados['nome'], dados.get('telefone'), dados.get('email'),
             dados.get('data_aniversario'), dados.get('endereco'),
             dados.get('observacoes',''), dados.get('produto_preferido'),
             dados.get('periodicidade'), usuario_id)
        dados['id'] = row['id']
        return dados


async def listar_clientes(usuario_id: int, busca: str = None) -> list:
    p = await get_pool()
    async with p.acquire() as conn:
        if busca:
            rows = await conn.fetch(
                "SELECT * FROM mei_clientes WHERE usuario_id=$1 AND nome ILIKE $2 ORDER BY id DESC",
                usuario_id, f"%{busca}%"
            )
        else:
            rows = await conn.fetch("SELECT * FROM mei_clientes WHERE usuario_id=$1 ORDER BY id DESC", usuario_id)
        return [dict(r) for r in rows]


async def obter_cliente(cliente_id: int, usuario_id: int) -> dict | None:
    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM mei_clientes WHERE id=$1 AND usuario_id=$2", cliente_id, usuario_id)
        return dict(row) if row else None


async def atualizar_cliente(cliente_id: int, dados: dict, usuario_id: int) -> dict | None:
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute("""
            UPDATE mei_clientes SET nome=$1, telefone=$2, email=$3, data_aniversario=$4,
            endereco=$5, observacoes=$6, produto_preferido=$7, periodicidade=$8
            WHERE id=$9 AND usuario_id=$10
        """, dados.get('nome'), dados.get('telefone'), dados.get('email'),
             dados.get('data_aniversario'), dados.get('endereco'),
             dados.get('observacoes',''), dados.get('produto_preferido'),
             dados.get('periodicidade'), cliente_id, usuario_id)
        return await obter_cliente(cliente_id, usuario_id)


async def excluir_cliente(cliente_id: int, usuario_id: int):
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute("DELETE FROM mei_clientes WHERE id=$1 AND usuario_id=$2", cliente_id, usuario_id)


async def clientes_aniversario_mes(usuario_id: int, mes_atual: int) -> list:
    p = await get_pool()
    async with p.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM mei_clientes WHERE usuario_id=$1 AND EXTRACT(MONTH FROM data_aniversario::DATE) = $2",
            usuario_id, mes_atual
        )
        return [dict(r) for r in rows]


# ── Contagem / limites de plano ───────────────────────────────────────────────

async def contar_produtos(usuario_id: int) -> int:
    p = await get_pool()
    async with p.acquire() as conn:
        result = await conn.fetchval("SELECT COUNT(*) FROM mei_produtos WHERE usuario_id=$1", usuario_id)
        return result or 0


async def contar_clientes(usuario_id: int) -> int:
    p = await get_pool()
    async with p.acquire() as conn:
        result = await conn.fetchval("SELECT COUNT(*) FROM mei_clientes WHERE usuario_id=$1", usuario_id)
        return result or 0


async def contar_vendas_total(usuario_id: int) -> int:
    p = await get_pool()
    async with p.acquire() as conn:
        result = await conn.fetchval("SELECT COUNT(*) FROM mei_vendas WHERE usuario_id=$1", usuario_id)
        return result or 0


async def contar_despesas_total(usuario_id: int) -> int:
    p = await get_pool()
    async with p.acquire() as conn:
        result = await conn.fetchval("SELECT COUNT(*) FROM mei_despesas WHERE usuario_id=$1", usuario_id)
        return result or 0


# ── CRUD Assinaturas ─────────────────────────────────────────────────────────

async def criar_assinatura(dados: dict) -> dict:
    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO mei_assinaturas (cliente_id, usuario_id, email, nome, status, mp_subscription_id)
            VALUES ($1,$2,$3,$4,$5,$6)
            RETURNING id
        """, dados.get('cliente_id'), dados.get('usuario_id'), dados.get('email'), dados.get('nome'),
             dados.get('status','pendente'), dados.get('mp_subscription_id'))
        dados['id'] = row['id']
        return dados


async def obter_assinatura_usuario(usuario_id: int) -> dict | None:
    """Ultima assinatura do usuario (independente do status)."""
    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM mei_assinaturas WHERE usuario_id=$1 ORDER BY id DESC LIMIT 1",
            usuario_id
        )
        return dict(row) if row else None


async def obter_assinatura_ativa_usuario(usuario_id: int) -> dict | None:
    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM mei_assinaturas WHERE usuario_id=$1 AND status='ativa' ORDER BY id DESC LIMIT 1",
            usuario_id
        )
        return dict(row) if row else None


async def obter_assinatura_pendente_usuario(usuario_id: int) -> dict | None:
    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM mei_assinaturas WHERE usuario_id=$1 AND status='pendente' ORDER BY id DESC LIMIT 1",
            usuario_id
        )
        return dict(row) if row else None


async def ativar_assinatura(assinatura_id: int, payment_id: str = None) -> bool:
    """Ativa (ou renova) uma assinatura, gravando data_inicio, data_fim e proximo_pagamento.

    data_fim = agora + 30 dias. Retorna True se renovou uma assinatura que ja esteve ativa.
    """
    p = await get_pool()
    agora = datetime.now(timezone.utc)
    data_fim = (agora + timedelta(days=30)).isoformat()
    async with p.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT status, renovacoes FROM mei_assinaturas WHERE id=$1", assinatura_id
        )
        if not row:
            return False
        renovadas = row["renovacoes"] or 0
        if row["status"] == "ativa":
            renovadas += 1
        elif row["status"] == "vencida" or row["status"] == "pendente":
            renovadas += 1
        await conn.execute(
            """UPDATE mei_assinaturas
               SET status='ativa', data_inicio=$2, data_fim=$3, proximo_pagamento=$3,
                   payment_id=$4, renovacoes=$5
               WHERE id=$1""",
            assinatura_id, agora.isoformat(), data_fim, payment_id, renovadas
        )
    return renovadas > 1


async def registrar_pagamento(payment_id: str, preference_id: str, usuario_id: int,
                              assinatura_id: int, status: str, valor: float,
                              tipo: str, raw: str) -> bool:
    """Registra pagamento com idempotencia (payment_id UNIQUE). Retorna False se ja processado."""
    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO mei_pagamentos (payment_id, preference_id, usuario_id, assinatura_id,
                                           status, valor, tipo, raw)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
               ON CONFLICT (payment_id) DO NOTHING
               RETURNING id""",
            str(payment_id), preference_id, usuario_id, assinatura_id, status, valor, tipo, raw
        )
        return row is not None


async def obter_pagamento(payment_id: str) -> dict | None:
    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM mei_pagamentos WHERE payment_id=$1", str(payment_id)
        )
        return dict(row) if row else None


async def listar_assinaturas_pendentes() -> list:
    p = await get_pool()
    async with p.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM mei_assinaturas WHERE status='pendente' ORDER BY id ASC"
        )
        return [dict(r) for r in rows]


async def expirar_assinaturas_vencidas() -> int:
    """Marca como 'vencida' assinaturas ativas com data_fim no passado. Retorna qtd expirada."""
    p = await get_pool()
    agora = datetime.now(timezone.utc).isoformat()
    async with p.acquire() as conn:
        result = await conn.execute(
            "UPDATE mei_assinaturas SET status='vencida' WHERE status='ativa' AND data_fim < $1",
            agora
        )
    try:
        return int(result.split()[-1])
    except Exception:
        return 0


async def cancelar_pendencias_abandonadas(idade_minutos: int = 120) -> int:
    """Marca como 'cancelada' assinaturas pendentes abandonadas ha mais de idade_minutos.

    Impede que um checkout abandonado trave o usuario para sempre (ja_pendente eterno).
    """
    p = await get_pool()
    async with p.acquire() as conn:
        result = await conn.execute(
            """UPDATE mei_assinaturas SET status='cancelada'
               WHERE status='pendente'
                 AND criado_em IS NOT NULL
                 AND (criado_em::timestamptz) < (NOW() - ($1 || ' minutes')::interval)""",
            idade_minutos
        )
    try:
        return int(result.split()[-1])
    except Exception:
        return 0


async def obter_assinatura_cliente(cliente_id: int) -> dict | None:
    """Compatibilidade: busca por cliente_id."""
    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM mei_assinaturas WHERE cliente_id=$1 ORDER BY id DESC LIMIT 1",
            cliente_id
        )
        return dict(row) if row else None


async def cancelar_assinatura_usuario(usuario_id: int):
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute(
            "UPDATE mei_assinaturas SET status='cancelada' WHERE usuario_id=$1 AND status='ativa'",
            usuario_id
        )


async def cancelar_assinatura_usuario_pendente(usuario_id: int):
    p = await get_pool()
    async with p.acquire() as conn:
        await conn.execute(
            "UPDATE mei_assinaturas SET status='cancelada' WHERE usuario_id=$1 AND status='pendente'",
            usuario_id
        )


async def cancelar_assinatura(cliente_id: int):
    """Compatibilidade: cancela por cliente_id."""
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


# ── Cupons de desconto ────────────────────────────────────────────────────────

async def criar_cupom(codigo: str, percentual: float, ativo: bool = True) -> dict:
    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO mei_cupons (codigo, percentual, ativo) VALUES ($1,$2,$3) RETURNING id, codigo, percentual, ativo, criado_em",
            codigo, percentual, ativo
        )
        return dict(row)


async def obter_cupom(codigo: str) -> dict | None:
    p = await get_pool()
    async with p.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM mei_cupons WHERE codigo=$1",
            codigo
        )
        return dict(row) if row else None


async def listar_cupons_ativos() -> list:
    p = await get_pool()
    async with p.acquire() as conn:
        rows = await conn.fetch(
            "SELECT id, codigo, percentual, ativo, criado_em FROM mei_cupons WHERE ativo=TRUE ORDER BY id ASC"
        )
        return [dict(r) for r in rows]