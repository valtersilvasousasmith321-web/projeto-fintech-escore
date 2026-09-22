"""
app/core/negociacao.py

Máquina de estados da negociação de dívida (Pilar 2 do produto —
ver docs/solucao_completa_nome_limpo_score.md). Lógica pura, sem
dependências externas.

Regra de negócio inegociável: a cobrança de comissão só pode ser
calculada/efetivada quando o status chega a BAIXA_CONFIRMADA. Isso é
reforçado no código, não só na documentação.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class StatusNegociacao(str, Enum):
    INICIADA = "iniciada"
    PROPOSTA_RECEBIDA = "proposta_recebida"
    ACEITA_PELO_USUARIO = "aceita_pelo_usuario"
    PAGA = "paga"
    BAIXA_CONFIRMADA = "baixa_confirmada"
    CANCELADA = "cancelada"


# Transições permitidas — qualquer transição fora deste mapa é rejeitada.
TRANSICOES_VALIDAS: dict[StatusNegociacao, set[StatusNegociacao]] = {
    StatusNegociacao.INICIADA: {StatusNegociacao.PROPOSTA_RECEBIDA, StatusNegociacao.CANCELADA},
    StatusNegociacao.PROPOSTA_RECEBIDA: {StatusNegociacao.ACEITA_PELO_USUARIO, StatusNegociacao.CANCELADA},
    StatusNegociacao.ACEITA_PELO_USUARIO: {StatusNegociacao.PAGA, StatusNegociacao.CANCELADA},
    StatusNegociacao.PAGA: {StatusNegociacao.BAIXA_CONFIRMADA},
    StatusNegociacao.BAIXA_CONFIRMADA: set(),  # estado terminal
    StatusNegociacao.CANCELADA: set(),  # estado terminal
}

COMISSAO_PERCENTUAL_ATE_2000 = 0.15
COMISSAO_PERCENTUAL_ACIMA_2000 = 0.10
LIMITE_FAIXA_COMISSAO = 2000.0


class TransicaoInvalida(Exception):
    pass


class ErroValidacaoNegociacao(Exception):
    pass


@dataclass
class EventoNegociacao:
    status: StatusNegociacao
    timestamp: str
    detalhe: str = ""


@dataclass
class Negociacao:
    negociacao_id: str
    usuario_id: str
    credor: str
    valor_original: float
    valor_com_desconto: float | None = None
    status: StatusNegociacao = StatusNegociacao.INICIADA
    historico: list[EventoNegociacao] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.valor_original <= 0:
            raise ErroValidacaoNegociacao("valor_original deve ser positivo")
        if not self.usuario_id or not self.credor:
            raise ErroValidacaoNegociacao("usuario_id e credor são obrigatórios")
        if not self.historico:
            self.historico.append(EventoNegociacao(
                status=self.status,
                timestamp=datetime.now(timezone.utc).isoformat(),
                detalhe="negociação iniciada",
            ))

    def transicionar(self, novo_status: StatusNegociacao, detalhe: str = "") -> None:
        permitidas = TRANSICOES_VALIDAS.get(self.status, set())
        if novo_status not in permitidas:
            raise TransicaoInvalida(
                f"Transição inválida: {self.status.value} -> {novo_status.value}. "
                f"Permitidas a partir de {self.status.value}: "
                f"{[s.value for s in permitidas] or 'nenhuma (estado terminal)'}"
            )
        self.status = novo_status
        self.historico.append(EventoNegociacao(
            status=novo_status,
            timestamp=datetime.now(timezone.utc).isoformat(),
            detalhe=detalhe,
        ))

    def registrar_proposta(self, valor_com_desconto: float) -> None:
        if valor_com_desconto <= 0 or valor_com_desconto > self.valor_original:
            raise ErroValidacaoNegociacao(
                "valor_com_desconto deve ser positivo e menor ou igual ao valor original"
            )
        self.valor_com_desconto = valor_com_desconto
        self.transicionar(StatusNegociacao.PROPOSTA_RECEBIDA, detalhe=f"proposta de R$ {valor_com_desconto:.2f}")

    def calcular_comissao(self) -> float:
        """
        Calcula a comissão devida. REGRA DE NEGÓCIO CRÍTICA: só pode ser
        chamada (e o valor só pode ser cobrado do usuário) quando o status
        é BAIXA_CONFIRMADA — nunca antes. Isso é validado explicitamente
        aqui para impedir cobrança prematura mesmo por erro de integração.
        """
        if self.status != StatusNegociacao.BAIXA_CONFIRMADA:
            raise ErroValidacaoNegociacao(
                f"Comissão só pode ser calculada com status BAIXA_CONFIRMADA. "
                f"Status atual: {self.status.value}"
            )
        if self.valor_com_desconto is None:
            raise ErroValidacaoNegociacao("Não há valor com desconto registrado para calcular comissão")

        desconto_obtido = self.valor_original - self.valor_com_desconto
        if desconto_obtido <= 0:
            return 0.0

        percentual = (
            COMISSAO_PERCENTUAL_ATE_2000
            if self.valor_original <= LIMITE_FAIXA_COMISSAO
            else COMISSAO_PERCENTUAL_ACIMA_2000
        )
        return round(desconto_obtido * percentual, 2)
