"""
app/core/password_reset.py

Lógica de token de recuperação de senha. Lógica pura (sem banco, sem
rede) — testável isoladamente.

Decisões de segurança:
- O token bruto (enviado por e-mail) NUNCA é armazenado — só o hash
  SHA-256 dele fica no banco. Mesmo que o banco seja vazado, ninguém
  consegue usar os hashes pra redefinir senha de ninguém.
- Token de uso único: depois de usado (`usado=True`), nunca mais é aceito,
  mesmo dentro da validade.
- Validade curta (30 min por padrão) — reduz a janela de um token
  interceptado ser usado por outra pessoa.
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.core.security import gerar_token_seguro


VALIDADE_PADRAO_MINUTOS = 30


@dataclass
class TokenResetSenha:
    token_hash: str
    usuario_id: str
    criado_em: datetime
    expira_em: datetime
    usado: bool = False


def _hash_token(token_bruto: str) -> str:
    return hashlib.sha256(token_bruto.encode("utf-8")).hexdigest()


def criar_token_reset(usuario_id: str, validade_minutos: int = VALIDADE_PADRAO_MINUTOS) -> tuple[str, TokenResetSenha]:
    """
    Retorna (token_bruto, registro). O token_bruto é o que vai por e-mail
    pro usuário — nunca é retornado de novo depois disso, nem armazenado
    em texto puro.
    """
    token_bruto = gerar_token_seguro(tamanho_bytes=32)
    agora = datetime.now(timezone.utc)
    registro = TokenResetSenha(
        token_hash=_hash_token(token_bruto),
        usuario_id=usuario_id,
        criado_em=agora,
        expira_em=agora + timedelta(minutes=validade_minutos),
        usado=False,
    )
    return token_bruto, registro


def token_e_valido(registro: TokenResetSenha, token_fornecido: str, agora: datetime | None = None) -> bool:
    """Verifica: não usado, não expirado, e corresponde ao hash — em tempo constante."""
    agora = agora or datetime.now(timezone.utc)
    if registro.usado:
        return False
    if agora > registro.expira_em:
        return False
    hash_fornecido = _hash_token(token_fornecido)
    return hmac.compare_digest(hash_fornecido, registro.token_hash)


def marcar_como_usado(registro: TokenResetSenha) -> TokenResetSenha:
    return TokenResetSenha(
        token_hash=registro.token_hash,
        usuario_id=registro.usuario_id,
        criado_em=registro.criado_em,
        expira_em=registro.expira_em,
        usado=True,
    )
