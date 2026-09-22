"""
app/core/rate_limiter_redis.py

Implementação do rate limiter usando Redis, pra quando o backend rodar
em MAIS de uma instância (o rate limiter em memória, em
app/core/rate_limiter.py + app/main.py, funciona bem com uma instância
só — cada instância nova teria seu próprio contador isolado, o que
enfraquece o limite).

IMPORTANTE: este módulo não pôde ser testado neste ambiente porque
não há um servidor Redis disponível aqui (nem rede pra um Redis
gerenciado). A lógica de decisão (quando permitir/bloquear) já está
testada em app/core/rate_limiter.py (8 testes) — este arquivo só troca
ONDE o contador é guardado (Redis em vez de um dict em memória), não
a lógica de decisão em si.

Como habilitar: defina REDIS_URL como variável de ambiente (ex:
redis://usuario:senha@host:porta/0 — Render e Upstash têm Redis
gerenciado com plano gratuito). Sem essa variável, o app continua
usando o rate limiter em memória, sem quebrar nada.
"""

from __future__ import annotations

import os

try:
    import redis
except ImportError:
    redis = None  # type: ignore


class ErroRateLimiterRedis(Exception):
    pass


class RateLimiterRedis:
    def __init__(self, redis_url: str | None = None):
        if redis is None:
            raise ErroRateLimiterRedis(
                "pacote 'redis' não instalado. Adicione 'redis==5.0.1' ao requirements.txt "
                "e rode pip install -r requirements.txt."
            )
        self.redis_url = redis_url or os.environ.get("REDIS_URL")
        if not self.redis_url:
            raise ErroRateLimiterRedis("REDIS_URL não configurada.")
        self._cliente = redis.from_url(self.redis_url, decode_responses=True)

    def permitir(self, identificador: str, janela_segundos: int, limite: int) -> bool:
        """
        Usa o padrão INCR + EXPIRE do Redis (contador de janela fixa —
        mais simples que sliding window, mas suficiente pra rate limit
        de API e é o padrão recomendado pela documentação do Redis
        pra esse caso de uso).
        """
        chave = f"ratelimit:{identificador}"
        contagem_atual = self._cliente.incr(chave)
        if contagem_atual == 1:
            self._cliente.expire(chave, janela_segundos)
        return contagem_atual <= limite


def redis_disponivel() -> bool:
    """Diz se o Redis está configurado e o pacote instalado — usado pelo
    main.py pra decidir qual rate limiter usar, sem precisar instanciar nada."""
    return redis is not None and bool(os.environ.get("REDIS_URL"))
