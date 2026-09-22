"""
app/core/billing.py

Lógica de cobrança — PURA, sem chamada de rede. Decide valores a
cobrar, interpreta o payload do webhook do Asaas, e valida o token
de autenticação do webhook. A chamada HTTP de verdade fica em
app/integrations/asaas_client.py.

Por que a validação de webhook aqui é por token estático, e não HMAC:
confirmei na documentação oficial do Asaas (docs.asaas.com, seção de
sugestões) que assinatura criptográfica HMAC-SHA256 nos webhooks
ainda NÃO existe na API — está listada como pedido de melhoria
pendente. O mecanismo que a Asaas oferece hoje é um token de
autenticação estático que você define ao cadastrar o webhook no
painel deles, e que eles devolvem no header a cada chamada. É isso
que validamos aqui.
"""

from __future__ import annotations

import hmac
from dataclasses import dataclass
from enum import Enum


class PlanoAssinatura(str, Enum):
    PLUS = "plus"
    PREMIUM = "premium"


PRECOS_PLANOS: dict[PlanoAssinatura, float] = {
    PlanoAssinatura.PLUS: 19.90,
    PlanoAssinatura.PREMIUM: 39.90,
}

# IMPORTANTE: cada consulta CredNet custa ~R$16,06 pro provedor
# (confirmado no painel da conta na SOA Web Services). O preço da
# consulta avulsa precisa ficar ACIMA disso, senão cada consulta dá
# prejuízo em vez de lucro. R$24,90 garante uma margem real.
PRECO_CONSULTA_AVULSA = 24.90


class ErroCobranca(Exception):
    pass


def obter_valor_plano(plano: PlanoAssinatura) -> float:
    if plano not in PRECOS_PLANOS:
        raise ErroCobranca(f"plano desconhecido: {plano}")
    return PRECOS_PLANOS[plano]


def token_webhook_valido(token_recebido: str | None, token_esperado: str) -> bool:
    """Comparação em tempo constante — mesma lógica de proteção usada
    em verificar_senha (app/core/security.py)."""
    if not token_recebido:
        return False
    return hmac.compare_digest(token_recebido, token_esperado)


class TipoEventoAsaas(str, Enum):
    PAGAMENTO_CONFIRMADO = "pagamento_confirmado"
    PAGAMENTO_RECEBIDO = "pagamento_recebido"
    PAGAMENTO_ATRASADO = "pagamento_atrasado"
    PAGAMENTO_CANCELADO = "pagamento_cancelado"
    DESCONHECIDO = "desconhecido"


@dataclass
class EventoPagamentoInterpretado:
    tipo: TipoEventoAsaas
    asaas_payment_id: str | None
    asaas_customer_id: str | None
    valor: float | None


# Mapeamento dos eventos reais que a Asaas envia (confirmados na doc oficial:
# PAYMENT_CONFIRMED, PAYMENT_RECEIVED, PAYMENT_OVERDUE, PAYMENT_DELETED/PAYMENT_REFUNDED)
_MAPA_EVENTOS: dict[str, TipoEventoAsaas] = {
    "PAYMENT_CONFIRMED": TipoEventoAsaas.PAGAMENTO_CONFIRMADO,
    "PAYMENT_RECEIVED": TipoEventoAsaas.PAGAMENTO_RECEBIDO,
    "PAYMENT_OVERDUE": TipoEventoAsaas.PAGAMENTO_ATRASADO,
    "PAYMENT_DELETED": TipoEventoAsaas.PAGAMENTO_CANCELADO,
    "PAYMENT_REFUNDED": TipoEventoAsaas.PAGAMENTO_CANCELADO,
}


def interpretar_webhook_pagamento(payload: dict) -> EventoPagamentoInterpretado:
    """
    Recebe o JSON já decodificado do webhook do Asaas e extrai o que
    importa pro nosso sistema. Não faz nenhuma chamada de rede — só
    interpreta a estrutura de dado.

    Formato real do payload da Asaas (confirmado na documentação):
    {"event": "PAYMENT_CONFIRMED", "payment": {"id": "pay_...", "customer": "cus_...", "value": 19.9}}
    """
    evento_bruto = payload.get("event", "")
    tipo = _MAPA_EVENTOS.get(evento_bruto, TipoEventoAsaas.DESCONHECIDO)

    pagamento = payload.get("payment") or {}
    return EventoPagamentoInterpretado(
        tipo=tipo,
        asaas_payment_id=pagamento.get("id"),
        asaas_customer_id=pagamento.get("customer"),
        valor=pagamento.get("value"),
    )
