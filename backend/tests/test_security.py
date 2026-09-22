"""
tests/test_security.py

Testes do módulo de segurança: hashing de senha, validação de CPF/CNPJ,
mascaramento de dados sensíveis, e geração de token.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.security import (
    gerar_hash_senha,
    verificar_senha,
    validar_cpf,
    validar_cnpj,
    mascarar_cpf,
    mascarar_cnpj,
    gerar_token_seguro,
    hash_deterministico_documento,
)


class TestHashSenha(unittest.TestCase):
    def test_senha_curta_rejeitada(self):
        with self.assertRaises(ValueError):
            gerar_hash_senha("1234567")  # 7 caracteres

    def test_senha_valida_gera_hash(self):
        h = gerar_hash_senha("senhaSegura123")
        self.assertIn("$", h)

    def test_verificar_senha_correta(self):
        h = gerar_hash_senha("minhaSenha123")
        self.assertTrue(verificar_senha("minhaSenha123", h))

    def test_verificar_senha_incorreta(self):
        h = gerar_hash_senha("minhaSenha123")
        self.assertFalse(verificar_senha("senhaErrada456", h))

    def test_hash_nunca_armazena_senha_em_texto_puro(self):
        senha = "senhaSecreta123"
        h = gerar_hash_senha(senha)
        self.assertNotIn(senha, h)

    def test_mesma_senha_gera_hashes_diferentes_por_causa_do_salt(self):
        h1 = gerar_hash_senha("senhaIgual123")
        h2 = gerar_hash_senha("senhaIgual123")
        self.assertNotEqual(h1, h2)  # salts diferentes -> hashes diferentes

    def test_hash_malformado_retorna_false_em_vez_de_lancar_excecao(self):
        self.assertFalse(verificar_senha("qualquer", "hash_sem_formato_valido"))


class TestValidacaoCpf(unittest.TestCase):
    def test_cpf_valido_conhecido(self):
        # CPF gerado com dígitos verificadores válidos (não pertence a pessoa real)
        self.assertTrue(validar_cpf("111.444.777-35"))

    def test_cpf_com_todos_digitos_iguais_invalido(self):
        self.assertFalse(validar_cpf("111.111.111-11"))

    def test_cpf_com_tamanho_errado_invalido(self):
        self.assertFalse(validar_cpf("123.456.789"))

    def test_cpf_com_digito_verificador_errado_invalido(self):
        self.assertFalse(validar_cpf("111.444.777-36"))

    def test_cpf_sem_formatacao_tambem_funciona(self):
        self.assertTrue(validar_cpf("11144477735"))


class TestValidacaoCnpj(unittest.TestCase):
    def test_cnpj_valido_conhecido(self):
        self.assertTrue(validar_cnpj("11.222.333/0001-81"))

    def test_cnpj_todos_digitos_iguais_invalido(self):
        self.assertFalse(validar_cnpj("11.111.111/1111-11"))

    def test_cnpj_tamanho_errado_invalido(self):
        self.assertFalse(validar_cnpj("11.222.333/0001"))

    def test_cnpj_digito_verificador_errado_invalido(self):
        self.assertFalse(validar_cnpj("11.222.333/0001-82"))


class TestMascaramento(unittest.TestCase):
    def test_mascarar_cpf_esconde_meio(self):
        resultado = mascarar_cpf("11144477735")
        self.assertEqual(resultado, "111.***.***-35")
        self.assertNotIn("444", resultado)
        self.assertNotIn("777", resultado)

    def test_mascarar_cpf_invalido(self):
        self.assertEqual(mascarar_cpf("123"), "***invalido***")

    def test_mascarar_cnpj_esconde_meio(self):
        resultado = mascarar_cnpj("11222333000181")
        self.assertEqual(resultado, "11.***.***/****-81")


class TestHashDeterministicoDocumento(unittest.TestCase):
    def test_mesmo_cpf_gera_mesmo_hash(self):
        h1 = hash_deterministico_documento("111.444.777-35")
        h2 = hash_deterministico_documento("111.444.777-35")
        self.assertEqual(h1, h2)

    def test_formatacao_diferente_mesmo_cpf_gera_mesmo_hash(self):
        h1 = hash_deterministico_documento("111.444.777-35")
        h2 = hash_deterministico_documento("11144477735")
        self.assertEqual(h1, h2)

    def test_cpfs_diferentes_geram_hashes_diferentes(self):
        h1 = hash_deterministico_documento("11144477735")
        h2 = hash_deterministico_documento("52998224725")
        self.assertNotEqual(h1, h2)


class TestTokenSeguro(unittest.TestCase):
    def test_token_gerado_tem_tamanho_razoavel(self):
        token = gerar_token_seguro()
        self.assertGreater(len(token), 30)

    def test_tokens_gerados_sao_unicos(self):
        tokens = {gerar_token_seguro() for _ in range(1000)}
        self.assertEqual(len(tokens), 1000)  # nenhuma colisão em 1000 gerações


if __name__ == "__main__":
    unittest.main()
