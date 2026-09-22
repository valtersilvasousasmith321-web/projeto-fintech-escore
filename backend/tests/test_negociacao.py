"""
tests/test_negociacao.py

Testes da máquina de estados de negociação. Foco especial em garantir
que comissão NUNCA pode ser calculada antes de BAIXA_CONFIRMADA —
essa é a regra de negócio mais crítica do módulo (ver docs/solucao_completa_nome_limpo_score.md).
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.negociacao import (
    Negociacao,
    StatusNegociacao,
    TransicaoInvalida,
    ErroValidacaoNegociacao,
)


class TestValidacaoNegociacao(unittest.TestCase):
    def test_valor_original_negativo_rejeitado(self):
        with self.assertRaises(ErroValidacaoNegociacao):
            Negociacao(negociacao_id="n1", usuario_id="u1", credor="X", valor_original=-10)

    def test_usuario_id_vazio_rejeitado(self):
        with self.assertRaises(ErroValidacaoNegociacao):
            Negociacao(negociacao_id="n1", usuario_id="", credor="X", valor_original=100)

    def test_estado_inicial_e_iniciada(self):
        neg = Negociacao(negociacao_id="n1", usuario_id="u1", credor="X", valor_original=100)
        self.assertEqual(neg.status, StatusNegociacao.INICIADA)
        self.assertEqual(len(neg.historico), 1)


class TestTransicoesValidas(unittest.TestCase):
    def setUp(self):
        self.neg = Negociacao(negociacao_id="n1", usuario_id="u1", credor="Credor X", valor_original=1000.0)

    def test_fluxo_feliz_completo(self):
        self.neg.registrar_proposta(700.0)
        self.assertEqual(self.neg.status, StatusNegociacao.PROPOSTA_RECEBIDA)

        self.neg.transicionar(StatusNegociacao.ACEITA_PELO_USUARIO)
        self.neg.transicionar(StatusNegociacao.PAGA)
        self.neg.transicionar(StatusNegociacao.BAIXA_CONFIRMADA)

        self.assertEqual(self.neg.status, StatusNegociacao.BAIXA_CONFIRMADA)
        self.assertEqual(len(self.neg.historico), 5)  # iniciada + 4 transições

    def test_cancelamento_a_partir_de_iniciada(self):
        self.neg.transicionar(StatusNegociacao.CANCELADA)
        self.assertEqual(self.neg.status, StatusNegociacao.CANCELADA)

    def test_cancelamento_a_partir_de_proposta_recebida(self):
        self.neg.registrar_proposta(700.0)
        self.neg.transicionar(StatusNegociacao.CANCELADA)
        self.assertEqual(self.neg.status, StatusNegociacao.CANCELADA)


class TestTransicoesInvalidas(unittest.TestCase):
    def setUp(self):
        self.neg = Negociacao(negociacao_id="n1", usuario_id="u1", credor="Credor X", valor_original=1000.0)

    def test_nao_pode_pular_direto_para_paga(self):
        with self.assertRaises(TransicaoInvalida):
            self.neg.transicionar(StatusNegociacao.PAGA)

    def test_nao_pode_pular_direto_para_baixa_confirmada(self):
        with self.assertRaises(TransicaoInvalida):
            self.neg.transicionar(StatusNegociacao.BAIXA_CONFIRMADA)

    def test_estado_terminal_baixa_confirmada_nao_aceita_novas_transicoes(self):
        self.neg.registrar_proposta(700.0)
        self.neg.transicionar(StatusNegociacao.ACEITA_PELO_USUARIO)
        self.neg.transicionar(StatusNegociacao.PAGA)
        self.neg.transicionar(StatusNegociacao.BAIXA_CONFIRMADA)
        with self.assertRaises(TransicaoInvalida):
            self.neg.transicionar(StatusNegociacao.CANCELADA)

    def test_estado_terminal_cancelada_nao_aceita_novas_transicoes(self):
        self.neg.transicionar(StatusNegociacao.CANCELADA)
        with self.assertRaises(TransicaoInvalida):
            self.neg.transicionar(StatusNegociacao.INICIADA)

    def test_proposta_com_valor_maior_que_original_rejeitada(self):
        with self.assertRaises(ErroValidacaoNegociacao):
            self.neg.registrar_proposta(1500.0)

    def test_proposta_com_valor_negativo_rejeitada(self):
        with self.assertRaises(ErroValidacaoNegociacao):
            self.neg.registrar_proposta(-100.0)


class TestCalculoComissao(unittest.TestCase):
    """
    O conjunto de testes mais importante do módulo: garante que a regra
    'só cobra se o resultado foi confirmado' é aplicada no código, não só
    na documentação.
    """

    def test_comissao_nao_pode_ser_calculada_em_estado_iniciada(self):
        neg = Negociacao(negociacao_id="n1", usuario_id="u1", credor="X", valor_original=1000.0)
        with self.assertRaises(ErroValidacaoNegociacao):
            neg.calcular_comissao()

    def test_comissao_nao_pode_ser_calculada_apos_proposta_aceita_mas_nao_paga(self):
        neg = Negociacao(negociacao_id="n1", usuario_id="u1", credor="X", valor_original=1000.0)
        neg.registrar_proposta(700.0)
        neg.transicionar(StatusNegociacao.ACEITA_PELO_USUARIO)
        with self.assertRaises(ErroValidacaoNegociacao):
            neg.calcular_comissao()

    def test_comissao_nao_pode_ser_calculada_apos_paga_mas_antes_de_baixa_confirmada(self):
        neg = Negociacao(negociacao_id="n1", usuario_id="u1", credor="X", valor_original=1000.0)
        neg.registrar_proposta(700.0)
        neg.transicionar(StatusNegociacao.ACEITA_PELO_USUARIO)
        neg.transicionar(StatusNegociacao.PAGA)
        with self.assertRaises(ErroValidacaoNegociacao):
            neg.calcular_comissao()

    def test_comissao_calculada_corretamente_faixa_ate_2000(self):
        neg = Negociacao(negociacao_id="n1", usuario_id="u1", credor="X", valor_original=1000.0)
        neg.registrar_proposta(700.0)  # desconto de 300
        neg.transicionar(StatusNegociacao.ACEITA_PELO_USUARIO)
        neg.transicionar(StatusNegociacao.PAGA)
        neg.transicionar(StatusNegociacao.BAIXA_CONFIRMADA)
        # desconto 300 * 15% = 45.0
        self.assertEqual(neg.calcular_comissao(), 45.0)

    def test_comissao_calculada_corretamente_faixa_acima_2000(self):
        neg = Negociacao(negociacao_id="n1", usuario_id="u1", credor="X", valor_original=5000.0)
        neg.registrar_proposta(3000.0)  # desconto de 2000
        neg.transicionar(StatusNegociacao.ACEITA_PELO_USUARIO)
        neg.transicionar(StatusNegociacao.PAGA)
        neg.transicionar(StatusNegociacao.BAIXA_CONFIRMADA)
        # desconto 2000 * 10% = 200.0
        self.assertEqual(neg.calcular_comissao(), 200.0)

    def test_comissao_zero_quando_nao_houve_desconto(self):
        neg = Negociacao(negociacao_id="n1", usuario_id="u1", credor="X", valor_original=1000.0)
        neg.registrar_proposta(1000.0)  # sem desconto
        neg.transicionar(StatusNegociacao.ACEITA_PELO_USUARIO)
        neg.transicionar(StatusNegociacao.PAGA)
        neg.transicionar(StatusNegociacao.BAIXA_CONFIRMADA)
        self.assertEqual(neg.calcular_comissao(), 0.0)


if __name__ == "__main__":
    unittest.main()
