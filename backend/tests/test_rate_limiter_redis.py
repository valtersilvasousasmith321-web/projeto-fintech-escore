"""
tests/test_rate_limiter_redis.py

Testa só a parte que RODA sem o pacote 'redis' instalado e sem
servidor Redis disponível: a detecção de disponibilidade. A classe
RateLimiterRedis em si (que faz chamada de rede pro Redis) não é
testada aqui — ver o aviso no topo de app/core/rate_limiter_redis.py.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.rate_limiter_redis import redis_disponivel, RateLimiterRedis, ErroRateLimiterRedis


class TestRedisDisponivel(unittest.TestCase):
    def test_sem_redis_url_retorna_falso(self):
        os.environ.pop("REDIS_URL", None)
        self.assertFalse(redis_disponivel())


class TestRateLimiterRedisSemConfiguracao(unittest.TestCase):
    def test_instanciar_sem_redis_url_lanca_erro_claro(self):
        os.environ.pop("REDIS_URL", None)
        with self.assertRaises(ErroRateLimiterRedis):
            RateLimiterRedis()


if __name__ == "__main__":
    unittest.main()
