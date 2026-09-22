"""
app/core/marketplace.py

Motor de elegibilidade do marketplace de crédito pré-qualificado.
NUNCA aprova ou nega crédito — apenas compara os dados do usuário
contra os critérios PÚBLICOS de cada parceiro e retorna um percentual
de aderência. Ver docs/esteira_credito_pre_qualificado.md.
"""

from __future__ import annotations

from dataclasses import dataclass


class ErroValidacaoMarketplace(Exception):
    pass


@dataclass
class CriteriosParceiro:
    parceiro_id: str
    produto: str
    score_minimo: int
    sem_restricao_ativa: bool
    renda_minima_declarada: float
    tempo_minimo_relacionamento_bancario_meses: int

    def __post_init__(self) -> None:
        if self.score_minimo < 0:
            raise ErroValidacaoMarketplace("score_minimo não pode ser negativo")
        if self.renda_minima_declarada < 0:
            raise ErroValidacaoMarketplace("renda_minima_declarada não pode ser negativa")


@dataclass
class PerfilUsuario:
    score_atual: int
    tem_restricao_ativa: bool
    renda_declarada: float
    tempo_relacionamento_bancario_meses: int


@dataclass
class ResultadoElegibilidade:
    parceiro_id: str
    produto: str
    criterios_atendidos: int
    criterios_totais: int
    percentual_aderencia: float
    detalhamento: dict[str, bool]
    elegivel_para_exibicao: bool  # exibimos ofertas mesmo com aderência parcial, mas com aviso


PERCENTUAL_MINIMO_PARA_EXIBIR = 0.5  # não exibe ofertas com menos de 50% de aderência


def avaliar_elegibilidade(perfil: PerfilUsuario, criterios: CriteriosParceiro) -> ResultadoElegibilidade:
    """
    Compara o perfil do usuário aos critérios PÚBLICOS do parceiro.
    Isto é uma pré-qualificação, não uma decisão de crédito — a decisão
    final é sempre do parceiro financeiro.
    """
    detalhamento = {
        "score_minimo": perfil.score_atual >= criterios.score_minimo,
        "sem_restricao_ativa": (not perfil.tem_restricao_ativa) if criterios.sem_restricao_ativa else True,
        "renda_minima": perfil.renda_declarada >= criterios.renda_minima_declarada,
        "tempo_relacionamento": (
            perfil.tempo_relacionamento_bancario_meses >= criterios.tempo_minimo_relacionamento_bancario_meses
        ),
    }

    atendidos = sum(1 for v in detalhamento.values() if v)
    total = len(detalhamento)
    percentual = round(atendidos / total, 2) if total > 0 else 0.0

    return ResultadoElegibilidade(
        parceiro_id=criterios.parceiro_id,
        produto=criterios.produto,
        criterios_atendidos=atendidos,
        criterios_totais=total,
        percentual_aderencia=percentual,
        detalhamento=detalhamento,
        elegivel_para_exibicao=percentual >= PERCENTUAL_MINIMO_PARA_EXIBIR,
    )


def rankear_ofertas(
    perfil: PerfilUsuario, lista_criterios: list[CriteriosParceiro]
) -> list[ResultadoElegibilidade]:
    """Avalia todas as ofertas e retorna ordenadas por aderência (maior primeiro),
    mostrando apenas as que atingem o percentual mínimo de exibição."""
    resultados = [avaliar_elegibilidade(perfil, c) for c in lista_criterios]
    exibiveis = [r for r in resultados if r.elegivel_para_exibicao]
    exibiveis.sort(key=lambda r: r.percentual_aderencia, reverse=True)
    return exibiveis
