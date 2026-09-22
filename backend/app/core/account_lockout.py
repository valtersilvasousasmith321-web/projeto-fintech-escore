"""
app/core/account_lockout.py

Lógica de bloqueio temporário de conta após tentativas de senha
incorretas. Lógica pura — sem banco, sem rede.
"""

from __future__ import annotations

from datetime import datetime, timedelta

LIMITE_TENTATIVAS = 5
DURACAO_BLOQUEIO_MINUTOS = 15


def deve_bloquear(tentativas_falhas: int) -> bool:
    return tentativas_falhas >= LIMITE_TENTATIVAS


def calcular_fim_bloqueio(agora: datetime) -> datetime:
    return agora + timedelta(minutes=DURACAO_BLOQUEIO_MINUTOS)


def esta_bloqueado(bloqueado_ate: datetime | None, agora: datetime) -> bool:
    if bloqueado_ate is None:
        return False
    return agora < bloqueado_ate
