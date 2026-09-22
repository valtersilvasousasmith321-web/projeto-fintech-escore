import sys
import os
from datetime import datetime, timedelta, timezone
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.cache_score import cache_esta_valido, dias_restantes_ate_proxima_consulta


class TestCacheEstaValido(unittest.TestCase):
    def test_consulta_recente_esta_valida(self):
        agora = datetime.now(timezone.utc)
        consultado_em = agora - timedelta(days=5)
        self.assertTrue(cache_esta_valido(consultado_em, agora))

    def test_consulta_antiga_nao_esta_valida(self):
        agora = datetime.now(timezone.utc)
        consultado_em = agora - timedelta(days=31)
        self.assertFalse(cache_esta_valido(consultado_em, agora))

    def test_exatamente_no_limite_ainda_valido(self):
        agora = datetime.now(timezone.utc)
        consultado_em = agora - timedelta(days=29, hours=23)
        self.assertTrue(cache_esta_valido(consultado_em, agora))

    def test_validade_customizada(self):
        agora = datetime.now(timezone.utc)
        consultado_em = agora - timedelta(days=10)
        self.assertFalse(cache_esta_valido(consultado_em, agora, validade_dias=7))


class TestDiasRestantes(unittest.TestCase):
    def test_calcula_dias_restantes_corretamente(self):
        agora = datetime.now(timezone.utc)
        consultado_em = agora - timedelta(days=20)
        self.assertEqual(dias_restantes_ate_proxima_consulta(consultado_em, agora), 10)

    def test_nunca_retorna_negativo(self):
        agora = datetime.now(timezone.utc)
        consultado_em = agora - timedelta(days=50)
        self.assertEqual(dias_restantes_ate_proxima_consulta(consultado_em, agora), 0)


if __name__ == "__main__":
    unittest.main()
