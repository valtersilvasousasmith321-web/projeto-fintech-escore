"""
app/integrations/pluggy_adapter.py

Converte a resposta JÁ RECEBIDA da API da Pluggy no formato que o motor
de score (app/core/score_engine.py) espera. Lógica pura — não faz
nenhuma chamada de rede, por isso é totalmente testável sem depender
de credenciais ou sandbox.

Formato de conta de cartão de crédito da Pluggy (campo relevante):
{
  "type": "CREDIT",
  "balance": -1240.50,          # negativo = valor devido
  "creditData": {
    "creditLimit": 5000.0,
    "availableCreditLimit": 3759.5,
    "minimumPayment": 124.05,
    "balanceDueDate": "2026-10-05"
  }
}
"""

from __future__ import annotations

from datetime import date, datetime

from app.core.score_engine import DadosOpenFinance, Divida, ErroValidacao


class ErroAdaptadorPluggy(Exception):
    pass


def calcular_utilizacao_conta_credito(conta: dict) -> float:
    """
    Calcula o percentual de utilização de uma única conta de cartão
    de crédito a partir do payload bruto da Pluggy.
    """
    if conta.get("type") != "CREDIT":
        raise ErroAdaptadorPluggy(f"conta não é do tipo CREDIT: {conta.get('type')}")

    credit_data = conta.get("creditData") or {}
    limite = credit_data.get("creditLimit")
    if not limite or limite <= 0:
        raise ErroAdaptadorPluggy("creditData.creditLimit ausente ou inválido no payload da Pluggy")

    saldo_devedor = abs(conta.get("balance", 0) or 0)
    return round(min(1.0, saldo_devedor / limite), 4)


def calcular_utilizacao_agregada(contas: list[dict]) -> float:
    """
    Quando o usuário tem mais de um cartão conectado, agrega a
    utilização pelo total de limite disponível (mais representativo
    do que a média simples entre os cartões).
    """
    contas_credito = [c for c in contas if c.get("type") == "CREDIT"]
    if not contas_credito:
        raise ErroAdaptadorPluggy("nenhuma conta do tipo CREDIT encontrada para calcular utilização")

    limite_total = 0.0
    saldo_total = 0.0
    for conta in contas_credito:
        credit_data = conta.get("creditData") or {}
        limite = credit_data.get("creditLimit") or 0
        if limite <= 0:
            continue
        limite_total += limite
        saldo_total += abs(conta.get("balance", 0) or 0)

    if limite_total <= 0:
        raise ErroAdaptadorPluggy("soma dos limites de crédito é zero — não é possível calcular utilização")

    return round(min(1.0, saldo_total / limite_total), 4)


def extrair_faturas_em_aberto(contas: list[dict], hoje: date | None = None) -> list[Divida]:
    """
    A partir das contas de crédito retornadas pela Pluggy, monta a
    lista de Divida (mesmo formato usado em docs/listagem_boletos_pendencias.md)
    para faturas com balanceDueDate já vencida e saldo devedor positivo.
    """
    hoje = hoje or date.today()
    dividas: list[Divida] = []

    for conta in contas:
        if conta.get("type") != "CREDIT":
            continue
        credit_data = conta.get("creditData") or {}
        saldo = abs(conta.get("balance", 0) or 0)
        data_vencimento_str = credit_data.get("balanceDueDate")
        if saldo <= 0 or not data_vencimento_str:
            continue

        try:
            data_vencimento = datetime.fromisoformat(data_vencimento_str.replace("Z", "+00:00")).date()
        except ValueError:
            continue

        dias_atraso = (hoje - data_vencimento).days
        if dias_atraso <= 0:
            continue  # ainda não venceu

        nome_credor = conta.get("name") or conta.get("marketingName") or "Cartão de crédito"
        try:
            dividas.append(Divida(
                credor=nome_credor,
                valor=saldo,
                dias_atraso=dias_atraso,
                origem="open_finance_pluggy",
                negativado=False,  # dado de Open Finance nunca é "negativado" por definição — isso vem do birô
                linha_digitavel=None,  # Pluggy não expõe linha digitável de fatura de cartão
            ))
        except ErroValidacao as e:
            raise ErroAdaptadorPluggy(f"dado inconsistente vindo da Pluggy para a conta {conta.get('id')}: {e}")

    return dividas


def montar_dados_open_finance(
    contas: list[dict],
    utilizacao_credito_meta: float = 0.30,
    meses_historico_disponivel: int = 0,
    pontualidade_pagamentos_24m: float = 1.0,
) -> DadosOpenFinance:
    """
    Monta o objeto DadosOpenFinance completo a partir das contas retornadas
    pela Pluggy. `pontualidade_pagamentos_24m` ainda não vem calculada
    automaticamente da Pluggy neste adaptador — precisa ser derivada do
    histórico de transações (ver observação em docs/arquitetura_dados.md
    sobre limitações de dado de pontualidade via Open Finance) ou informada
    por outra fonte (ex: birô).
    """
    utilizacao_atual = calcular_utilizacao_agregada(contas)
    return DadosOpenFinance(
        utilizacao_credito_atual=utilizacao_atual,
        utilizacao_credito_meta=utilizacao_credito_meta,
        meses_historico_disponivel=meses_historico_disponivel,
        pontualidade_pagamentos_24m=pontualidade_pagamentos_24m,
    )
