"""
app/core/serasa_adapter.py

Converte a resposta do endpoint CredNet (SOA Web Services → Serasa
Experian) no formato que o motor de score (app/core/score_engine.py)
espera. Lógica pura — não faz nenhuma chamada de rede, por isso é
testável sem depender de credenciais.

Formato real da resposta CredNet (confirmado em teste real no ambiente
de homologação antes de escrever este arquivo):

{
  "informacoesAdicionais": {
    "score": {"pontuacao": 650, "faixa": "...", "probabilidadeInadimplencia": 0.12, ...}
  },
  "dadosNegativos": {
    "pendenciasFinanceiras": {
      "detalhes": [
        {"dataOcorrencia": "2026-05-18", "credor": "...", "valor": 340.0, ...}
      ]
    },
    "restricoesFinanceiras": { ... mesma estrutura ... }
  },
  "transacao": {"status": true, "codigoStatus": null, "codigoStatusDescricao": null}
}
"""

from __future__ import annotations

from datetime import date, datetime

from app.core.score_engine import Divida, ErroValidacao


class ErroAdaptadorSerasa(Exception):
    pass


def transacao_bem_sucedida(resposta_crednet: dict) -> bool:
    """A API SOA/Serasa retorna status da transação em transacao.status —
    diferente de HTTP status code, é um campo de negócio dentro do corpo."""
    return bool((resposta_crednet.get("transacao") or {}).get("status"))


def extrair_score(resposta_crednet: dict) -> int | None:
    """
    Retorna a pontuação de score (0-1000 na escala Serasa) ou None se
    o campo não vier preenchido (ex: CPF sem histórico suficiente pro
    birô calcular score).
    """
    score = ((resposta_crednet.get("informacoesAdicionais") or {}).get("score") or {})
    pontuacao = score.get("pontuacao")
    if pontuacao is None:
        return None
    if not (0 <= pontuacao <= 1000):
        raise ErroAdaptadorSerasa(f"pontuação de score fora da faixa esperada: {pontuacao}")
    return int(pontuacao)


def extrair_probabilidade_inadimplencia(resposta_crednet: dict) -> float | None:
    score = ((resposta_crednet.get("informacoesAdicionais") or {}).get("score") or {})
    return score.get("probabilidadeInadimplencia")


def _calcular_dias_atraso(data_ocorrencia_str: str | None, hoje: date) -> int:
    if not data_ocorrencia_str:
        return 0
    try:
        data_ocorrencia = datetime.fromisoformat(data_ocorrencia_str.replace("Z", "+00:00")).date()
    except ValueError:
        return 0
    dias = (hoje - data_ocorrencia).days
    return max(dias, 0)


def _converter_detalhe_em_divida(detalhe: dict, origem: str, hoje: date) -> Divida | None:
    valor = detalhe.get("valor")
    if not valor or valor <= 0:
        return None  # registro sem valor útil (comum em dado de homologação/teste)

    credor = detalhe.get("credor") or detalhe.get("modalidade") or "Credor não informado pelo birô"
    dias_atraso = _calcular_dias_atraso(detalhe.get("dataOcorrencia"), hoje)

    try:
        return Divida(
            credor=credor, valor=float(valor), dias_atraso=dias_atraso,
            origem=origem, negativado=True, linha_digitavel=None,
        )
    except ErroValidacao as e:
        raise ErroAdaptadorSerasa(f"dado inconsistente vindo do CredNet: {e}")


def extrair_dividas_negativadas(resposta_crednet: dict, hoje: date | None = None) -> list[Divida]:
    """
    Extrai as dívidas negativadas de duas seções da resposta:
    dadosNegativos.pendenciasFinanceiras e dadosNegativos.restricoesFinanceiras.
    Ambas têm a mesma estrutura de detalhe; tratamos as duas como
    dívidas negativadas reais.
    """
    hoje = hoje or date.today()
    dados_negativos = resposta_crednet.get("dadosNegativos") or {}
    dividas: list[Divida] = []

    for secao, origem in [
        ("pendenciasFinanceiras", "serasa_crednet_pendencia"),
        ("restricoesFinanceiras", "serasa_crednet_restricao"),
    ]:
        detalhes = ((dados_negativos.get(secao) or {}).get("detalhes")) or []
        for detalhe in detalhes:
            divida = _converter_detalhe_em_divida(detalhe, origem, hoje)
            if divida is not None:
                dividas.append(divida)

    return dividas


def extrair_consultas_recentes(resposta_crednet: dict, limite_dias: int = 30) -> int:
    """
    Conta quantas consultas ao CPF/CNPJ aconteceram nos últimos
    `limite_dias` dias, a partir de outrasInformacoes.registroConsultas.detalhes[].
    Cada item tem 'quantidadeDias' (dias desde aquela consulta específica).
    """
    detalhes = ((resposta_crednet.get("outrasInformacoes") or {}).get("registroConsultas") or {}).get("detalhes") or []
    return sum(
        1 for d in detalhes
        if d.get("quantidadeDias") is not None and d["quantidadeDias"] <= limite_dias
    )


def extrair_confirmacao_exclusao(resposta_exclusao: dict) -> dict:
    """
    Extrai os dados relevantes da resposta de
    /api/v2/Serasa/Negativacoes/Excluir (formato confirmado em teste
    real na conta de homologação do usuário).
    """
    return {
        "unique_id": resposta_exclusao.get("uniqueID"),
        "valor": resposta_exclusao.get("valor"),
        "data_hora_exclusao": resposta_exclusao.get("dataHoraExclusao"),
        "sucesso": transacao_bem_sucedida(resposta_exclusao),
    }


def resposta_indica_cpf_sem_restricao(resposta_crednet: dict) -> bool:
    """True quando o birô não encontrou nenhuma ocorrência negativa —
    útil pro motor de elegibilidade do marketplace (critério 'sem_restricao_ativa')."""
    resumo = ((resposta_crednet.get("dadosNegativos") or {}).get("resumo") or {})
    total = resumo.get("totalOcorrencias")
    return total is None or total == 0
