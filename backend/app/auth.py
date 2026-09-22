"""
app/auth.py

Autenticação via JWT (JSON Web Token). Requer python-jose instalado
(ver requirements.txt).

Configuração de segurança:
- Algoritmo HS256 com chave secreta forte (nunca hardcoded — vem de
  variável de ambiente, ver Settings abaixo)
- Token de acesso de curta duração (15 min) + refresh token (7 dias),
  padrão OWASP para reduzir janela de exposição de um token vazado
- Toda rota protegida usa a dependency `usuario_atual` do FastAPI
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

ALGORITMO = "HS256"
CHAVE_SECRETA = os.environ.get("JWT_SECRET_KEY")
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

if not CHAVE_SECRETA:
    # Em produção isso deve FALHAR ao subir a aplicação — nunca usar um
    # valor padrão hardcoded para segredo de assinatura de token.
    # Ver SECURITY.md, seção "Gestão de segredos".
    raise RuntimeError(
        "JWT_SECRET_KEY não definida. Configure a variável de ambiente antes de subir a aplicação. "
        "Gere uma com: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
    )

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def criar_access_token(usuario_id: str) -> str:
    expira_em = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": usuario_id, "exp": expira_em, "type": "access"}
    return jwt.encode(payload, CHAVE_SECRETA, algorithm=ALGORITMO)


def criar_refresh_token(usuario_id: str) -> str:
    expira_em = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": usuario_id, "exp": expira_em, "type": "refresh"}
    return jwt.encode(payload, CHAVE_SECRETA, algorithm=ALGORITMO)


def decodificar_token(token: str, tipo_esperado: str = "access") -> str:
    """Retorna o usuario_id se o token for válido, senão lança HTTPException 401."""
    excecao_credenciais = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, CHAVE_SECRETA, algorithms=[ALGORITMO])
        usuario_id = payload.get("sub")
        tipo = payload.get("type")
        if usuario_id is None or tipo != tipo_esperado:
            raise excecao_credenciais
        return usuario_id
    except JWTError:
        raise excecao_credenciais


async def usuario_atual(token: str = Depends(oauth2_scheme)) -> str:
    """Dependency do FastAPI para proteger rotas — injeta o usuario_id do token válido."""
    return decodificar_token(token, tipo_esperado="access")


async def admin_atual(usuario_id: str = Depends(usuario_atual)) -> str:
    """
    Dependency que exige, além de um token válido, que o usuário seja
    administrador (checado no banco a cada requisição — não no payload
    do token, pra que revogar admin de alguém funcione imediatamente,
    sem precisar esperar o token expirar).
    """
    from app.database import obter_conexao  # import local pra evitar import circular

    with obter_conexao() as conn:
        row = conn.execute("SELECT is_admin FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()

    if row is None or not row["is_admin"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="acesso restrito ao administrador")
    return usuario_id
