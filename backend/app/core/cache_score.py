"""
app/core/cache_score.py

Decide se uma consulta ao birô (cara, ~R$16 por chamada no CredNet)
pode ser respondida com um resultado já salvo, em vez de consultar de
novo. Lógica pura — sem banco, sem rede.

Por que 30 dias: o próprio motor de score (score_engine.py) já assume
que uma ação leva de 30 a 90 dias pra refletir no birô — não faz
sentido cobrar por uma nova consulta antes disso, o número não vai
ter mudado de forma significativa.
"""

from __future__ import annotations

from datetime import datetime, timedelta

VALIDADE_PADRAO_DIAS = 30


def cache_esta_valido(consultado_em: datetime, agora: datetime | None = None, validade_dias: int = VALIDADE_PADRAO_DIAS) -> bool:
    agora = agora or datetime.now(consultado_em.tzinfo)
    return agora < consultado_em + timedelta(days=validade_dias)


def dias_restantes_ate_proxima_consulta(consultado_em: datetime, agora: datetime | None = None, validade_dias: int = VALIDADE_PADRAO_DIAS) -> int:
    agora = agora or datetime.now(consultado_em.tzinfo)
    data_liberacao = consultado_em + timedelta(days=validade_dias)
    restante = (data_liberacao - agora).days
    return max(restante, 0)
