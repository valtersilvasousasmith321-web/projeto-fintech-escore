"""
app/core/rate_limiter.py

Limitador de taxa por janela deslizante ("sliding window"). Lógica pura
(sem rede, sem estado global) — o estado (lista de timestamps por
identificador) é responsabilidade de quem chama, o que torna isso
100% testável e reutilizável tanto pro rate limit geral quanto pro
mais rígido dos endpoints de autenticação.
"""

from __future__ import annotations


def limpar_janela(timestamps: list[float], agora: float, janela_segundos: float) -> list[float]:
    """Remove da lista qualquer timestamp mais antigo que a janela."""
    return [t for t in timestamps if agora - t < janela_segundos]


def permitir_requisicao(
    timestamps: list[float], agora: float, janela_segundos: float, limite: int
) -> tuple[bool, list[float]]:
    """
    Decide se uma nova requisição é permitida, dado o histórico de
    timestamps desse identificador (IP, por exemplo).

    Retorna (permitido, nova_lista_de_timestamps) — a lista já vem limpa
    da janela antiga, e com o novo timestamp adicionado SE permitido.
    Quem chama deve persistir a lista retornada de volta no dicionário
    de estado (ela substitui a lista antiga).
    """
    janela_limpa = limpar_janela(timestamps, agora, janela_segundos)

    if len(janela_limpa) >= limite:
        return False, janela_limpa

    return True, janela_limpa + [agora]
