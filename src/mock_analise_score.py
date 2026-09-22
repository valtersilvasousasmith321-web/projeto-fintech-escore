"""
mock_analise_score.py

Simulação funcional do motor de auditoria de score e geração de plano de ação.

Este script NÃO se conecta a nenhuma API real (Open Finance, birôs, etc).
Ele usa dados fictícios de entrada para demonstrar a LÓGICA do algoritmo
descrito em docs/especificacao_algoritmo.md:

  - Cálculo de impacto estimado de ações no score
  - Penalização por consulta de CPF (hard inquiry)
  - Recalculo de prazos quando um evento negativo é detectado
  - Geração de log estruturado de auditoria (JSON)

Rodar: python mock_analise_score.py
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional


# ---------------------------------------------------------------------------
# Constantes do modelo (pesos e amplitude) — ver docs/especificacao_algoritmo.md
# ---------------------------------------------------------------------------

PESO_HISTORICO_PAGAMENTO = 0.35
PESO_UTILIZACAO_CREDITO = 0.30
PESO_TEMPO_RELACIONAMENTO = 0.15
PESO_DIVERSIDADE_CREDITO = 0.10
PESO_CONSULTAS_RECENTES = 0.10

AMPLITUDE_ESCALA_PONTOS = 100  # variação máxima considerada "normal" numa simulação
PRAZO_BASE_ATUALIZACAO_FATURA_DIAS = 35
PRAZO_BASE_BAIXA_DIVIDA_DIAS = 55
JANELA_ESTABILIZACAO_POR_CONSULTA_DIAS = 15


class StatusAcao(str, Enum):
    PENDENTE = "pendente"
    CONCLUIDA = "concluida"
    EM_VALIDACAO = "em_validacao"


@dataclass
class DadosOpenFinance:
    """Dados fictícios que viriam do agregador (Pluggy/Belvo) via consentimento."""
    utilizacao_credito_atual: float          # 0.0 a 1.0 (percentual do limite usado)
    utilizacao_credito_meta: float           # meta que o usuário está tentando atingir
    meses_historico_disponivel: int          # quanto histórico o app já coletou
    pontualidade_pagamentos_24m: float       # 0.0 a 1.0 (percentual de pagamentos em dia)


@dataclass
class DadosBiro:
    """Dados fictícios que viriam do biro de crédito (Serasa/Quod/Boa Vista)."""
    score_atual: int                          # score oficial, ex: 0-1000
    tempo_relacionamento_credito_meses: int
    quantidade_tipos_credito_ativos: int
    dividas_ativas: list[dict]                 # [{"credor": str, "valor": float, "dias_atraso": int,
                                                #   "origem": str, "negativado": bool, "linha_digitavel": str|None}]
    consultas_cpf_ultimos_30_dias: int


@dataclass
class AcaoPlano:
    descricao: str
    impacto_estimado_min: float
    impacto_estimado_max: float
    prazo_estimado_dias: int
    esforco: str
    status: StatusAcao = StatusAcao.PENDENTE


@dataclass
class ResultadoAuditoria:
    usuario_id: str
    timestamp: str
    score_atual: int
    score_estimado_apos_plano: int
    fatores: dict
    alertas: list[str]
    plano_acao: list[AcaoPlano]
    confianca_modelo: float
    log_json: str


def calcular_fator_confianca(meses_historico: int) -> float:
    """
    Quanto mais histórico de dados via Open Finance, maior a confiança
    na estimativa de impacto. Varia entre 0.5 (pouco histórico) e 0.9 (>= 12 meses).
    """
    if meses_historico <= 0:
        return 0.5
    confianca = 0.5 + min(meses_historico, 12) * (0.4 / 12)
    return round(confianca, 2)


def calcular_impacto_reducao_utilizacao(
    utilizacao_atual: float,
    utilizacao_meta: float,
    fator_confianca: float,
) -> tuple[float, float]:
    """
    Calcula a faixa (min, max) de impacto estimado em pontos ao reduzir
    a utilização de crédito de `utilizacao_atual` para `utilizacao_meta`.
    """
    delta_normalizado = max(0.0, utilizacao_atual - utilizacao_meta)
    impacto_central = (
        PESO_UTILIZACAO_CREDITO
        * delta_normalizado
        * fator_confianca
        * AMPLITUDE_ESCALA_PONTOS
    )
    # faixa de incerteza de +/- 25% em torno do valor central
    impacto_min = round(impacto_central * 0.75, 1)
    impacto_max = round(impacto_central * 1.25, 1)
    return impacto_min, impacto_max


def calcular_impacto_quitacao_divida(valor_divida: float, dias_atraso: int, fator_confianca: float) -> tuple[float, float]:
    """
    Dívidas mais antigas (mais dias de atraso) têm peso maior no histórico de
    pagamento, então quitá-las tem impacto estimado proporcionalmente maior.
    """
    # normaliza dias de atraso numa escala 0-1 (cap em 365 dias para o cálculo)
    severidade_normalizada = min(dias_atraso, 365) / 365
    delta_normalizado = 0.3 + (0.7 * severidade_normalizada)  # quitar sempre ajuda, mas mais se estava grave

    impacto_central = (
        PESO_HISTORICO_PAGAMENTO
        * delta_normalizado
        * fator_confianca
        * AMPLITUDE_ESCALA_PONTOS
    )
    impacto_min = round(impacto_central * 0.8, 1)
    impacto_max = round(impacto_central * 1.3, 1)
    return impacto_min, impacto_max


def calcular_penalizacao_consultas(consultas_30_dias: int) -> float:
    """
    Calcula a penalização estimada por consultas recentes ao CPF (hard inquiries).
    Múltiplas consultas em curto período são desproporcionalmente negativas.
    """
    if consultas_30_dias <= 0:
        return 0.0

    penalizacao_total = 0.0
    fator_severidade = 1.0
    for _ in range(consultas_30_dias):
        penalizacao_total += PESO_CONSULTAS_RECENTES * fator_severidade * AMPLITUDE_ESCALA_PONTOS * 0.1
        fator_severidade += 0.3  # cada consulta adicional pesa mais que a anterior

    return round(penalizacao_total, 1)


def gerar_alertas(dados_biro: DadosBiro) -> list[str]:
    alertas = []
    if dados_biro.consultas_cpf_ultimos_30_dias > 0:
        alertas.append(
            f"nova_consulta_cpf_detectada (quantidade: {dados_biro.consultas_cpf_ultimos_30_dias} "
            f"nos últimos 30 dias)"
        )
    for divida in dados_biro.dividas_ativas:
        if divida["dias_atraso"] > 90:
            alertas.append(f"divida_critica: {divida['credor']} com {divida['dias_atraso']} dias de atraso")
    return alertas


def montar_plano_de_acao(
    dados_of: DadosOpenFinance,
    dados_biro: DadosBiro,
    fator_confianca: float,
) -> list[AcaoPlano]:
    plano: list[AcaoPlano] = []

    # Penalidade por consulta recente: aumenta o prazo estimado de TODAS as ações
    atraso_extra_dias = (
        dados_biro.consultas_cpf_ultimos_30_dias * JANELA_ESTABILIZACAO_POR_CONSULTA_DIAS
    )

    # Ação 1: reduzir utilização de crédito, se aplicável
    if dados_of.utilizacao_credito_atual > dados_of.utilizacao_credito_meta:
        imp_min, imp_max = calcular_impacto_reducao_utilizacao(
            dados_of.utilizacao_credito_atual, dados_of.utilizacao_credito_meta, fator_confianca
        )
        plano.append(
            AcaoPlano(
                descricao=(
                    f"Reduzir utilização de limite de crédito de "
                    f"{dados_of.utilizacao_credito_atual*100:.0f}% para "
                    f"{dados_of.utilizacao_credito_meta*100:.0f}%"
                ),
                impacto_estimado_min=imp_min,
                impacto_estimado_max=imp_max,
                prazo_estimado_dias=PRAZO_BASE_ATUALIZACAO_FATURA_DIAS + atraso_extra_dias,
                esforco="baixo",
            )
        )

    # Ação 2: quitar cada dívida ativa
    for divida in dados_biro.dividas_ativas:
        imp_min, imp_max = calcular_impacto_quitacao_divida(
            divida["valor"], divida["dias_atraso"], fator_confianca
        )
        plano.append(
            AcaoPlano(
                descricao=f"Quitar dívida com {divida['credor']} (R$ {divida['valor']:.2f})",
                impacto_estimado_min=imp_min,
                impacto_estimado_max=imp_max,
                prazo_estimado_dias=PRAZO_BASE_BAIXA_DIVIDA_DIAS + atraso_extra_dias,
                esforco="médio" if divida["valor"] < 1000 else "alto",
            )
        )

    # Ação 3: comportamental, se houve consultas recentes
    if dados_biro.consultas_cpf_ultimos_30_dias > 0:
        plano.append(
            AcaoPlano(
                descricao="Evitar novas consultas de CPF nos próximos 90 dias",
                impacto_estimado_min=0.0,
                impacto_estimado_max=0.0,
                prazo_estimado_dias=90,
                esforco="comportamental",
            )
        )

    # ordena por impacto máximo estimado, decrescente
    plano.sort(key=lambda a: a.impacto_estimado_max, reverse=True)
    return plano


def rodar_auditoria(usuario_id: str, dados_of: DadosOpenFinance, dados_biro: DadosBiro) -> ResultadoAuditoria:
    fator_confianca = calcular_fator_confianca(dados_of.meses_historico_disponivel)

    plano = montar_plano_de_acao(dados_of, dados_biro, fator_confianca)
    penalizacao = calcular_penalizacao_consultas(dados_biro.consultas_cpf_ultimos_30_dias)

    impacto_total_max = sum(a.impacto_estimado_max for a in plano)
    score_estimado_apos_plano = round(
        dados_biro.score_atual + impacto_total_max - penalizacao
    )
    # score não pode passar dos limites teóricos da escala (0-1000, modelo Serasa como referência)
    score_estimado_apos_plano = max(0, min(1000, score_estimado_apos_plano))

    alertas = gerar_alertas(dados_biro)

    fatores = {
        "historico_pagamento_24m": dados_of.pontualidade_pagamentos_24m,
        "utilizacao_credito_atual": dados_of.utilizacao_credito_atual,
        "tempo_relacionamento_meses": dados_biro.tempo_relacionamento_credito_meses,
        "diversidade_tipos_credito": dados_biro.quantidade_tipos_credito_ativos,
        "consultas_30_dias": dados_biro.consultas_cpf_ultimos_30_dias,
        "penalizacao_estimada_por_consultas": penalizacao,
    }

    log = {
        "usuario_id": usuario_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "fatores_entrada": fatores,
        "score_estimado_anterior": dados_biro.score_atual,
        "score_estimado_novo": score_estimado_apos_plano,
        "delta": score_estimado_apos_plano - dados_biro.score_atual,
        "acoes_recalculadas": [a.descricao for a in plano],
        "alertas": alertas,
        "confianca_modelo": fator_confianca,
        "fonte_dados": ["open_finance_mock", "biro_mock"],
    }

    return ResultadoAuditoria(
        usuario_id=usuario_id,
        timestamp=log["timestamp"],
        score_atual=dados_biro.score_atual,
        score_estimado_apos_plano=score_estimado_apos_plano,
        fatores=fatores,
        alertas=alertas,
        plano_acao=plano,
        confianca_modelo=fator_confianca,
        log_json=json.dumps(log, indent=2, ensure_ascii=False),
    )


def imprimir_diagnostico(resultado: ResultadoAuditoria) -> None:
    print("=" * 72)
    print(f" DIAGNÓSTICO DE SCORE — usuário {resultado.usuario_id}")
    print("=" * 72)
    print(f" Score atual (biro):              {resultado.score_atual}")
    print(f" Score estimado após plano:       {resultado.score_estimado_apos_plano}")
    print(f" Confiança do modelo:             {resultado.confianca_modelo * 100:.0f}%")
    print("-" * 72)

    if resultado.alertas:
        print(" ALERTAS:")
        for alerta in resultado.alertas:
            print(f"   ⚠  {alerta}")
        print("-" * 72)

    print(" PLANO DE AÇÃO (ordenado por impacto estimado):")
    for i, acao in enumerate(resultado.plano_acao, start=1):
        prazo_data = (datetime.now() + timedelta(days=acao.prazo_estimado_dias)).strftime("%d/%m/%Y")
        print(f"\n   {i}. {acao.descricao}")
        print(f"      Impacto estimado: +{acao.impacto_estimado_min} a +{acao.impacto_estimado_max} pontos")
        print(f"      Prazo estimado:   {acao.prazo_estimado_dias} dias (previsão: {prazo_data})")
        print(f"      Esforço:          {acao.esforco}")
        print(f"      Status:           {acao.status.value}")

    print("\n" + "-" * 72)
    print(" ⚠  Estimativas baseadas em modelo estatístico interno. O score oficial")
    print("    é calculado exclusivamente pelo biro de crédito. Aprovação de")
    print("    crédito é decisão exclusiva da instituição financeira ofertante.")
    print("=" * 72)


def gerar_explicacao_fatores(
    dados_of: DadosOpenFinance,
    dados_biro: DadosBiro,
) -> list[dict]:
    """
    Gera, para cada um dos 5 fatores, um bloco de texto no formato:
    o que está acontecendo / por que afeta o score / direção + prazo.

    Isso alimenta a tela de "Diagnóstico Detalhado" (ver
    docs/relatorio_detalhado_exemplo.md).
    """
    explicacoes = []

    # Fator 1 — histórico de pagamento
    atrasos = [d for d in dados_biro.dividas_ativas if d["dias_atraso"] > 0]
    explicacoes.append({
        "fator": "Histórico de pagamento",
        "peso": PESO_HISTORICO_PAGAMENTO,
        "situacao": f"{dados_of.pontualidade_pagamentos_24m*100:.0f}% dos pagamentos em dia nos últimos 24 meses",
        "porque": (
            "Este é o fator mais pesado do cálculo. Cada atraso reduz a confiança "
            "do modelo em pagamentos futuros."
            + (f" Há {len(atrasos)} dívida(s) em atraso pesando contra o score."
               if atrasos else " Não há atrasos ativos no momento.")
        ),
        "direcao": (
            "Quitar as dívidas em atraso e manter 100% dos pagamentos futuros em dia."
            if atrasos else "Nenhuma ação necessária — continue pagando em dia."
        ),
        "prazo_estimado_dias": PRAZO_BASE_BAIXA_DIVIDA_DIAS if atrasos else 0,
    })

    # Fator 2 — utilização de crédito
    utilizacao_ok = dados_of.utilizacao_credito_atual <= dados_of.utilizacao_credito_meta
    explicacoes.append({
        "fator": "Utilização de crédito",
        "peso": PESO_UTILIZACAO_CREDITO,
        "situacao": f"Uso de {dados_of.utilizacao_credito_atual*100:.0f}% do limite disponível",
        "porque": (
            "Usar a maior parte do limite é interpretado como sinal de aperto financeiro. "
            "O ideal considerado saudável é usar até 30% do limite."
        ),
        "direcao": (
            "Nenhuma ação necessária — sua utilização já está em nível saudável."
            if utilizacao_ok else
            f"Reduzir o uso do limite de {dados_of.utilizacao_credito_atual*100:.0f}% "
            f"para {dados_of.utilizacao_credito_meta*100:.0f}%."
        ),
        "prazo_estimado_dias": 0 if utilizacao_ok else PRAZO_BASE_ATUALIZACAO_FATURA_DIAS,
    })

    # Fator 3 — tempo de relacionamento
    explicacoes.append({
        "fator": "Tempo de relacionamento com crédito",
        "peso": PESO_TEMPO_RELACIONAMENTO,
        "situacao": f"{dados_biro.tempo_relacionamento_credito_meses} meses de histórico",
        "porque": "Quanto mais tempo de histórico, mais dado o modelo tem para confiar em você.",
        "direcao": "Nenhuma ação necessária — esse fator só melhora com o tempo.",
        "prazo_estimado_dias": 0,
    })

    # Fator 4 — diversidade de crédito
    explicacoes.append({
        "fator": "Diversidade de crédito",
        "peso": PESO_DIVERSIDADE_CREDITO,
        "situacao": f"{dados_biro.quantidade_tipos_credito_ativos} tipo(s) de crédito ativos",
        "porque": "Ter tipos diferentes de crédito bem administrados mostra capacidade de lidar com produtos diversos.",
        "direcao": "Nenhuma ação necessária no momento.",
        "prazo_estimado_dias": 0,
    })

    # Fator 5 — consultas recentes
    tem_consultas = dados_biro.consultas_cpf_ultimos_30_dias > 0
    explicacoes.append({
        "fator": "Consultas recentes ao CPF",
        "peso": PESO_CONSULTAS_RECENTES,
        "situacao": f"{dados_biro.consultas_cpf_ultimos_30_dias} consulta(s) nos últimos 30 dias",
        "porque": (
            "Muitas consultas em pouco tempo podem indicar busca de crédito em "
            "vários lugares ao mesmo tempo, visto como sinal de risco."
        ),
        "direcao": (
            "Evitar novas consultas/solicitações de crédito nos próximos 90 dias."
            if tem_consultas else "Nenhuma ação necessária."
        ),
        "prazo_estimado_dias": 90 if tem_consultas else 0,
    })

    return explicacoes


def imprimir_relatorio_detalhado(explicacoes: list[dict]) -> None:
    print("\n" + "=" * 72)
    print(" POR QUE SEU SCORE ESTÁ NESSE NÍVEL — DETALHAMENTO POR FATOR")
    print("=" * 72)
    for exp in explicacoes:
        print(f"\n▶ {exp['fator']}  (peso {exp['peso']*100:.0f}% do cálculo)")
        print(f"   O que está acontecendo: {exp['situacao']}")
        print(f"   Por que isso afeta o score: {exp['porque']}")
        print(f"   Direção para melhorar: {exp['direcao']}")
        if exp["prazo_estimado_dias"] > 0:
            print(f"   Tempo estimado: {exp['prazo_estimado_dias']} dias")
    print("\n" + "=" * 72)


def imprimir_lista_pendencias(dividas_ativas: list[dict]) -> None:
    """
    Exibe a lista de pendências no formato definido em
    docs/listagem_boletos_pendencias.md — priorizando faturas ainda
    não negativadas (mais urgentes de resolver) e depois dívidas já
    negativadas, ordenadas por dias de atraso (mais antigas primeiro).
    """
    nao_negativadas = [d for d in dividas_ativas if not d.get("negativado")]
    negativadas = sorted(
        (d for d in dividas_ativas if d.get("negativado")),
        key=lambda d: d["dias_atraso"],
        reverse=True,
    )

    print("\n" + "=" * 72)
    print(f" SUAS PENDÊNCIAS ATIVAS ({len(dividas_ativas)})")
    print("=" * 72)

    for divida in nao_negativadas + negativadas:
        icone = "🟡" if not divida.get("negativado") else "🔴"
        status = "Ainda não negativada" if not divida.get("negativado") else f"NEGATIVADO ({divida['origem']})"
        print(f"\n  {icone} {divida['credor']} — R$ {divida['valor']:.2f}")
        print(f"     Vencida há {divida['dias_atraso']} dias • {status}")
        if divida.get("linha_digitavel"):
            print(f"     Linha digitável: {divida['linha_digitavel']}")
            print("     [Pagar agora]  [Negociar com o credor]")
        else:
            print("     [Negociar direto com o credor]  [Ver oferta Limpa Nome]  [Assessoria paga]")

    if nao_negativadas:
        print("\n" + "-" * 72)
        print(" ⚠  Pague as pendências ainda não negativadas (🟡) o quanto antes —")
        print("    isso evita que elas virem uma nova negativação no birô.")
    print("=" * 72)


def main() -> None:
    """Ponto de entrada — roda uma simulação completa com dados fictícios."""

    usuario_id = str(uuid.uuid4())

    dados_open_finance = DadosOpenFinance(
        utilizacao_credito_atual=0.88,
        utilizacao_credito_meta=0.30,
        meses_historico_disponivel=8,
        pontualidade_pagamentos_24m=0.92,
    )

    dados_biro = DadosBiro(
        score_atual=560,
        tempo_relacionamento_credito_meses=42,
        quantidade_tipos_credito_ativos=3,
        dividas_ativas=[
            {
                "credor": "Credor Alfa Financeira", "valor": 340.00, "dias_atraso": 120,
                "origem": "biro_serasa", "negativado": True, "linha_digitavel": None,
            },
            {
                "credor": "Loja Beta Varejo", "valor": 89.90, "dias_atraso": 30,
                "origem": "biro_boa_vista", "negativado": True, "linha_digitavel": None,
            },
            {
                "credor": "Banco XPTO — Fatura Cartão", "valor": 612.40, "dias_atraso": 5,
                "origem": "open_finance_pluggy", "negativado": False,
                "linha_digitavel": "34191.79001 01043.510047 91020.150008 1 96380000061240",
            },
        ],
        consultas_cpf_ultimos_30_dias=2,
    )

    resultado = rodar_auditoria(usuario_id, dados_open_finance, dados_biro)
    imprimir_diagnostico(resultado)

    explicacoes = gerar_explicacao_fatores(dados_open_finance, dados_biro)
    imprimir_relatorio_detalhado(explicacoes)

    imprimir_lista_pendencias(dados_biro.dividas_ativas)

    print("\n\nLOG ESTRUTURADO DE AUDITORIA (para persistência/observabilidade):\n")
    print(resultado.log_json)


if __name__ == "__main__":
    main()
