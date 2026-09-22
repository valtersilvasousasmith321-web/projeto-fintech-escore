"""
app/core/score_engine.py

Motor de cálculo de score, impacto de ações e geração de plano de ação.
Lógica pura em Python padrão (sem dependências externas) para poder ser
testada isoladamente e reutilizada tanto pela API (FastAPI) quanto por
jobs em batch/worker.

Baseado em docs/especificacao_algoritmo.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum


# ---------------------------------------------------------------------------
# Constantes do modelo
# ---------------------------------------------------------------------------

PESO_HISTORICO_PAGAMENTO = 0.35
PESO_UTILIZACAO_CREDITO = 0.30
PESO_TEMPO_RELACIONAMENTO = 0.15
PESO_DIVERSIDADE_CREDITO = 0.10
PESO_CONSULTAS_RECENTES = 0.10

AMPLITUDE_ESCALA_PONTOS = 100
PRAZO_BASE_ATUALIZACAO_FATURA_DIAS = 35
PRAZO_BASE_BAIXA_DIVIDA_DIAS = 55
JANELA_ESTABILIZACAO_POR_CONSULTA_DIAS = 15

SCORE_MIN = 0
SCORE_MAX = 1000


class StatusAcao(str, Enum):
    PENDENTE = "pendente"
    CONCLUIDA = "concluida"
    EM_VALIDACAO = "em_validacao"


class ErroValidacao(Exception):
    """Erro de validação de dados de entrada do motor de score."""


@dataclass
class Divida:
    credor: str
    valor: float
    dias_atraso: int
    origem: str
    negativado: bool
    linha_digitavel: str | None = None

    def __post_init__(self) -> None:
        if self.valor <= 0:
            raise ErroValidacao(f"valor da dívida deve ser positivo, recebido: {self.valor}")
        if self.dias_atraso < 0:
            raise ErroValidacao(f"dias_atraso não pode ser negativo, recebido: {self.dias_atraso}")
        if not self.credor or not self.credor.strip():
            raise ErroValidacao("credor não pode ser vazio")


@dataclass
class DadosOpenFinance:
    utilizacao_credito_atual: float
    utilizacao_credito_meta: float
    meses_historico_disponivel: int
    pontualidade_pagamentos_24m: float

    def __post_init__(self) -> None:
        for campo, valor in [
            ("utilizacao_credito_atual", self.utilizacao_credito_atual),
            ("utilizacao_credito_meta", self.utilizacao_credito_meta),
            ("pontualidade_pagamentos_24m", self.pontualidade_pagamentos_24m),
        ]:
            if not (0.0 <= valor <= 1.0):
                raise ErroValidacao(f"{campo} deve estar entre 0.0 e 1.0, recebido: {valor}")
        if self.meses_historico_disponivel < 0:
            raise ErroValidacao("meses_historico_disponivel não pode ser negativo")


@dataclass
class DadosBiro:
    score_atual: int
    tempo_relacionamento_credito_meses: int
    quantidade_tipos_credito_ativos: int
    dividas_ativas: list[Divida]
    consultas_cpf_ultimos_30_dias: int

    def __post_init__(self) -> None:
        if not (SCORE_MIN <= self.score_atual <= SCORE_MAX):
            raise ErroValidacao(f"score_atual fora da faixa {SCORE_MIN}-{SCORE_MAX}: {self.score_atual}")
        if self.tempo_relacionamento_credito_meses < 0:
            raise ErroValidacao("tempo_relacionamento_credito_meses não pode ser negativo")
        if self.quantidade_tipos_credito_ativos < 0:
            raise ErroValidacao("quantidade_tipos_credito_ativos não pode ser negativo")
        if self.consultas_cpf_ultimos_30_dias < 0:
            raise ErroValidacao("consultas_cpf_ultimos_30_dias não pode ser negativo")


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
    score_atual: int
    score_estimado_apos_plano: int
    fatores: dict
    alertas: list[str]
    plano_acao: list[AcaoPlano]
    confianca_modelo: float


def calcular_fator_confianca(meses_historico: int) -> float:
    if meses_historico <= 0:
        return 0.5
    return round(0.5 + min(meses_historico, 12) * (0.4 / 12), 2)


def calcular_impacto_reducao_utilizacao(
    utilizacao_atual: float, utilizacao_meta: float, fator_confianca: float
) -> tuple[float, float]:
    delta_normalizado = max(0.0, utilizacao_atual - utilizacao_meta)
    impacto_central = PESO_UTILIZACAO_CREDITO * delta_normalizado * fator_confianca * AMPLITUDE_ESCALA_PONTOS
    return round(impacto_central * 0.75, 1), round(impacto_central * 1.25, 1)


def calcular_impacto_quitacao_divida(valor_divida: float, dias_atraso: int, fator_confianca: float) -> tuple[float, float]:
    severidade_normalizada = min(dias_atraso, 365) / 365
    delta_normalizado = 0.3 + (0.7 * severidade_normalizada)
    impacto_central = PESO_HISTORICO_PAGAMENTO * delta_normalizado * fator_confianca * AMPLITUDE_ESCALA_PONTOS
    return round(impacto_central * 0.8, 1), round(impacto_central * 1.3, 1)


def calcular_penalizacao_consultas(consultas_30_dias: int) -> float:
    if consultas_30_dias <= 0:
        return 0.0
    total = 0.0
    severidade = 1.0
    for _ in range(consultas_30_dias):
        total += PESO_CONSULTAS_RECENTES * severidade * AMPLITUDE_ESCALA_PONTOS * 0.1
        severidade += 0.3
    return round(total, 1)


def gerar_alertas(dados_biro: DadosBiro) -> list[str]:
    alertas = []
    if dados_biro.consultas_cpf_ultimos_30_dias > 0:
        alertas.append(f"nova_consulta_cpf_detectada:{dados_biro.consultas_cpf_ultimos_30_dias}")
    for divida in dados_biro.dividas_ativas:
        if divida.dias_atraso > 90:
            alertas.append(f"divida_critica:{divida.credor}:{divida.dias_atraso}")
    return alertas


def montar_plano_de_acao(dados_of: DadosOpenFinance, dados_biro: DadosBiro, fator_confianca: float) -> list[AcaoPlano]:
    plano: list[AcaoPlano] = []
    atraso_extra = dados_biro.consultas_cpf_ultimos_30_dias * JANELA_ESTABILIZACAO_POR_CONSULTA_DIAS

    if dados_of.utilizacao_credito_atual > dados_of.utilizacao_credito_meta:
        imp_min, imp_max = calcular_impacto_reducao_utilizacao(
            dados_of.utilizacao_credito_atual, dados_of.utilizacao_credito_meta, fator_confianca
        )
        plano.append(AcaoPlano(
            descricao=(
                f"Reduzir utilização de limite de crédito de "
                f"{dados_of.utilizacao_credito_atual*100:.0f}% para "
                f"{dados_of.utilizacao_credito_meta*100:.0f}%"
            ),
            impacto_estimado_min=imp_min,
            impacto_estimado_max=imp_max,
            prazo_estimado_dias=PRAZO_BASE_ATUALIZACAO_FATURA_DIAS + atraso_extra,
            esforco="baixo",
        ))

    for divida in dados_biro.dividas_ativas:
        imp_min, imp_max = calcular_impacto_quitacao_divida(divida.valor, divida.dias_atraso, fator_confianca)
        plano.append(AcaoPlano(
            descricao=f"Quitar dívida com {divida.credor} (R$ {divida.valor:.2f})",
            impacto_estimado_min=imp_min,
            impacto_estimado_max=imp_max,
            prazo_estimado_dias=PRAZO_BASE_BAIXA_DIVIDA_DIAS + atraso_extra,
            esforco="médio" if divida.valor < 1000 else "alto",
        ))

    if dados_biro.consultas_cpf_ultimos_30_dias > 0:
        plano.append(AcaoPlano(
            descricao="Evitar novas consultas de CPF nos próximos 90 dias",
            impacto_estimado_min=0.0,
            impacto_estimado_max=0.0,
            prazo_estimado_dias=90,
            esforco="comportamental",
        ))

    plano.sort(key=lambda a: a.impacto_estimado_max, reverse=True)
    return plano


def rodar_auditoria(dados_of: DadosOpenFinance, dados_biro: DadosBiro) -> ResultadoAuditoria:
    """
    Ponto de entrada principal do motor. Recebe dados já validados
    (validação acontece no __post_init__ dos dataclasses) e devolve
    o resultado completo da auditoria.
    """
    fator_confianca = calcular_fator_confianca(dados_of.meses_historico_disponivel)
    plano = montar_plano_de_acao(dados_of, dados_biro, fator_confianca)
    penalizacao = calcular_penalizacao_consultas(dados_biro.consultas_cpf_ultimos_30_dias)

    impacto_total_max = sum(a.impacto_estimado_max for a in plano)
    score_estimado = round(dados_biro.score_atual + impacto_total_max - penalizacao)
    score_estimado = max(SCORE_MIN, min(SCORE_MAX, score_estimado))

    fatores = {
        "historico_pagamento_24m": dados_of.pontualidade_pagamentos_24m,
        "utilizacao_credito_atual": dados_of.utilizacao_credito_atual,
        "tempo_relacionamento_meses": dados_biro.tempo_relacionamento_credito_meses,
        "diversidade_tipos_credito": dados_biro.quantidade_tipos_credito_ativos,
        "consultas_30_dias": dados_biro.consultas_cpf_ultimos_30_dias,
        "penalizacao_estimada_por_consultas": penalizacao,
    }

    return ResultadoAuditoria(
        score_atual=dados_biro.score_atual,
        score_estimado_apos_plano=score_estimado,
        fatores=fatores,
        alertas=gerar_alertas(dados_biro),
        plano_acao=plano,
        confianca_modelo=fator_confianca,
    )
