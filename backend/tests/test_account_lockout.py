import sys
import os
from datetime import datetime, timedelta, timezone
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.account_lockout import deve_bloquear, calcular_fim_bloqueio, esta_bloqueado, LIMITE_TENTATIVAS


class TestDeveBloquear(unittest.TestCase):
    def test_abaixo_do_limite_nao_bloqueia(self):
        self.assertFalse(deve_bloquear(LIMITE_TENTATIVAS - 1))

    def test_no_limite_bloqueia(self):
        self.assertTrue(deve_bloquear(LIMITE_TENTATIVAS))

    def test_acima_do_limite_bloqueia(self):
        self.assertTrue(deve_bloquear(LIMITE_TENTATIVAS + 10))

    def test_zero_tentativas_nao_bloqueia(self):
        self.assertFalse(deve_bloquear(0))


class TestEstaBloqueado(unittest.TestCase):
    def test_sem_bloqueio_registrado_nao_esta_bloqueado(self):
        self.assertFalse(esta_bloqueado(None, datetime.now(timezone.utc)))

    def test_dentro_do_periodo_de_bloqueio(self):
        agora = datetime.now(timezone.utc)
        fim_bloqueio = calcular_fim_bloqueio(agora)
        um_minuto_depois = agora + timedelta(minutes=1)
        self.assertTrue(esta_bloqueado(fim_bloqueio, um_minuto_depois))

    def test_apos_o_periodo_de_bloqueio_liberado(self):
        agora = datetime.now(timezone.utc)
        fim_bloqueio = calcular_fim_bloqueio(agora)
        depois_do_fim = fim_bloqueio + timedelta(minutes=1)
        self.assertFalse(esta_bloqueado(fim_bloqueio, depois_do_fim))


if __name__ == "__main__":
    unittest.main()
