"""
tests/test_password_reset.py

Testes da lógica de token de recuperação de senha. Roda sem instalar
nada (stdlib puro).
"""

import sys
import os
from datetime import datetime, timedelta, timezone
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.password_reset import (
    criar_token_reset,
    token_e_valido,
    marcar_como_usado,
)


class TestCriarTokenReset(unittest.TestCase):
    def test_token_bruto_nao_e_igual_ao_hash_armazenado(self):
        token_bruto, registro = criar_token_reset("usuario-1")
        self.assertNotEqual(token_bruto, registro.token_hash)

    def test_registro_comeca_nao_usado(self):
        _, registro = criar_token_reset("usuario-1")
        self.assertFalse(registro.usado)

    def test_tokens_gerados_sao_unicos(self):
        _, r1 = criar_token_reset("usuario-1")
        _, r2 = criar_token_reset("usuario-1")
        self.assertNotEqual(r1.token_hash, r2.token_hash)


class TestTokenEValido(unittest.TestCase):
    def test_token_correto_dentro_da_validade_e_aceito(self):
        token_bruto, registro = criar_token_reset("usuario-1", validade_minutos=30)
        self.assertTrue(token_e_valido(registro, token_bruto))

    def test_token_incorreto_e_rejeitado(self):
        _, registro = criar_token_reset("usuario-1")
        self.assertFalse(token_e_valido(registro, "token-forjado-qualquer"))

    def test_token_expirado_e_rejeitado(self):
        token_bruto, registro = criar_token_reset("usuario-1", validade_minutos=30)
        agora_no_futuro = datetime.now(timezone.utc) + timedelta(minutes=31)
        self.assertFalse(token_e_valido(registro, token_bruto, agora=agora_no_futuro))

    def test_token_no_limite_da_validade_ainda_aceito(self):
        token_bruto, registro = criar_token_reset("usuario-1", validade_minutos=30)
        agora_dentro = datetime.now(timezone.utc) + timedelta(minutes=29)
        self.assertTrue(token_e_valido(registro, token_bruto, agora=agora_dentro))

    def test_token_ja_usado_e_rejeitado_mesmo_correto(self):
        token_bruto, registro = criar_token_reset("usuario-1")
        registro_usado = marcar_como_usado(registro)
        self.assertFalse(token_e_valido(registro_usado, token_bruto))


class TestMarcarComoUsado(unittest.TestCase):
    def test_marcar_usado_nao_altera_o_original(self):
        token_bruto, registro = criar_token_reset("usuario-1")
        registro_usado = marcar_como_usado(registro)
        self.assertFalse(registro.usado)  # original imutável
        self.assertTrue(registro_usado.usado)


if __name__ == "__main__":
    unittest.main()
