"""
app/database.py

Persistência usando sqlite3 (biblioteca padrão do Python — nenhum
pacote externo necessário para esta camada). Em produção com volume
nacional, ver docs/estrategia_nacional_diferenciais.md — recomendação
é migrar para PostgreSQL gerenciado, mantendo a mesma interface.

IMPORTANTE (segurança): todas as queries usam parâmetros (?),
nunca concatenação de string — isso elimina SQL injection por
construção. Ver SECURITY.md, seção "Injeção de SQL".
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


def resolver_caminho_banco() -> Path:
    """
    Resolve onde o arquivo do banco fica.

    Se DATABASE_PATH estiver configurada (ex: apontando pro disco
    persistente montado no Render — sem isso, o Render Free apaga o
    arquivo a cada reinício do serviço), usa esse caminho. Senão, usa
    o caminho local de sempre — não muda nada pra quem já roda local
    ou no VS Code.
    """
    caminho_customizado = os.environ.get("DATABASE_PATH")
    if caminho_customizado:
        return Path(caminho_customizado)
    return Path(__file__).parent.parent / "dados_app.db"


DB_PATH = resolver_caminho_banco()


SCHEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
    id TEXT PRIMARY KEY,
    documento_hash TEXT NOT NULL UNIQUE,  -- nunca armazenamos o CPF/CNPJ em texto puro
    email TEXT NOT NULL UNIQUE,
    senha_hash TEXT NOT NULL,
    criado_em TEXT NOT NULL,
    is_admin INTEGER NOT NULL DEFAULT 0,
    tentativas_login_falhas INTEGER NOT NULL DEFAULT 0,
    bloqueado_ate TEXT
);

CREATE TABLE IF NOT EXISTS consentimentos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id TEXT NOT NULL,
    fonte TEXT NOT NULL,  -- open_finance | biro | base_publica
    concedido_em TEXT NOT NULL,
    revogado_em TEXT,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS negociacoes (
    id TEXT PRIMARY KEY,
    usuario_id TEXT NOT NULL,
    credor TEXT NOT NULL,
    valor_original REAL NOT NULL,
    valor_com_desconto REAL,
    status TEXT NOT NULL,
    criado_em TEXT NOT NULL,
    asaas_payment_id TEXT,
    comissao_paga INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS negociacao_eventos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    negociacao_id TEXT NOT NULL,
    status TEXT NOT NULL,
    detalhe TEXT NOT NULL DEFAULT '',
    timestamp TEXT NOT NULL,
    FOREIGN KEY (negociacao_id) REFERENCES negociacoes(id)
);

CREATE TABLE IF NOT EXISTS creditos_consulta_avulsa (
    id TEXT PRIMARY KEY,
    usuario_id TEXT NOT NULL,
    asaas_payment_id TEXT,
    status TEXT NOT NULL DEFAULT 'pendente',  -- pendente | pago | usado
    criado_em TEXT NOT NULL,
    usado_em TEXT,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS assinaturas (
    id TEXT PRIMARY KEY,
    usuario_id TEXT NOT NULL,
    plano TEXT NOT NULL,
    asaas_customer_id TEXT,
    asaas_subscription_id TEXT,
    status TEXT NOT NULL DEFAULT 'pendente',
    criado_em TEXT NOT NULL,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS clientes_asaas (
    usuario_id TEXT PRIMARY KEY,
    asaas_customer_id TEXT NOT NULL,
    criado_em TEXT NOT NULL,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS tokens_reset_senha (
    token_hash TEXT PRIMARY KEY,
    usuario_id TEXT NOT NULL,
    criado_em TEXT NOT NULL,
    expira_em TEXT NOT NULL,
    usado INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS cache_consulta_serasa (
    documento_hash TEXT PRIMARY KEY,
    usuario_id TEXT NOT NULL,
    resposta_json TEXT NOT NULL,
    consultado_em TEXT NOT NULL,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

CREATE TABLE IF NOT EXISTS log_auditoria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    score_anterior INTEGER,
    score_novo INTEGER,
    payload_json TEXT NOT NULL,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);
"""


def inicializar_banco(caminho: Path = DB_PATH) -> None:
    with sqlite3.connect(caminho) as conn:
        conn.executescript(SCHEMA)


@contextmanager
def obter_conexao(caminho: Path = DB_PATH):
    conn = sqlite3.connect(caminho)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def inserir_evento_negociacao(conn: sqlite3.Connection, negociacao_id: str, status: str, detalhe: str, timestamp: str) -> None:
    conn.execute(
        "INSERT INTO negociacao_eventos (negociacao_id, status, detalhe, timestamp) VALUES (?, ?, ?, ?)",
        (negociacao_id, status, detalhe, timestamp),
    )


def possui_assinatura_ativa(conn: sqlite3.Connection, usuario_id: str) -> bool:
    """
    Confere se o usuário tem assinatura Plus/Premium com status 'ativa'.
    Usado pra travar endpoints que geram custo real (ex: consulta ao
    Serasa, ~R$16 por chamada) — sem assinatura ativa, o endpoint nem
    chega a gastar dinheiro.
    """
    row = conn.execute(
        "SELECT 1 FROM assinaturas WHERE usuario_id = ? AND status = 'ativa' LIMIT 1",
        (usuario_id,),
    ).fetchone()
    return row is not None


def possui_credito_avulso_disponivel(conn: sqlite3.Connection, usuario_id: str) -> bool:
    """Confere se o usuário tem crédito de consulta avulsa pago (status
    'pago') e ainda não usado — alternativa à assinatura pra liberar
    uma única consulta real ao Serasa."""
    row = conn.execute(
        "SELECT 1 FROM creditos_consulta_avulsa WHERE usuario_id = ? AND status = 'pago' LIMIT 1",
        (usuario_id,),
    ).fetchone()
    return row is not None


def consumir_credito_avulso(conn: sqlite3.Connection, usuario_id: str) -> bool:
    """
    Marca UM crédito 'pago' como 'usado' (o mais antigo primeiro).
    Retorna True se havia crédito pra consumir, False se não havia
    nenhum (chamador não deveria ter chegado aqui sem checar antes,
    mas a função não assume isso silenciosamente).
    """
    row = conn.execute(
        "SELECT id FROM creditos_consulta_avulsa WHERE usuario_id = ? AND status = 'pago' "
        "ORDER BY criado_em ASC LIMIT 1",
        (usuario_id,),
    ).fetchone()
    if row is None:
        return False
    conn.execute(
        "UPDATE creditos_consulta_avulsa SET status = 'usado', usado_em = ? WHERE id = ?",
        (datetime.now(timezone.utc).isoformat(), row["id"]),
    )
    return True


def listar_eventos_negociacao(conn: sqlite3.Connection, negociacao_id: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT status, detalhe, timestamp FROM negociacao_eventos WHERE negociacao_id = ? ORDER BY id ASC",
        (negociacao_id,),
    ).fetchall()


def inserir_log_auditoria(
    conn: sqlite3.Connection,
    usuario_id: str,
    timestamp: str,
    score_anterior: int,
    score_novo: int,
    payload_json: str,
) -> None:
    conn.execute(
        "INSERT INTO log_auditoria (usuario_id, timestamp, score_anterior, score_novo, payload_json) "
        "VALUES (?, ?, ?, ?, ?)",
        (usuario_id, timestamp, score_anterior, score_novo, payload_json),
    )
