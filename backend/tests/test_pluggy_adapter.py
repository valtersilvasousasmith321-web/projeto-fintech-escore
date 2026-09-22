"""
tests/test_pluggy_adapter.py

Testes do adaptador de dados Pluggy -> DadosOpenFinance. Não faz
nenhuma chamada de rede: usa payloads fixos no formato documentado
da API da Pluggy. Roda com Python padrão (não importa pluggy_client,
então não precisa de httpx instalado).
"""

import sys
import os
from datetime import date
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.integrations.pluggy_adapter import (
    calcular_utilizacao_conta_credito,
    calcular_utilizacao_agregada,
    extrair_faturas_em_aberto,
    montar_dados_open_finance,
    ErroAdaptadorPluggy,
)


CONTA_CREDITO_EXEMPLO = {
    "id": "acc-1", "type": "CREDIT", "name": "Banco XPTO Cartão",
    "balance": -880.0,
    "creditData": {"creditLimit": 1000.0, "availableCreditLimit": 120.0, "balanceDueDate": "2026-09-01"},
}

CONTA_CREDITO_2 = {
    "id": "acc-2", "type": "CREDIT", "name": "Banco Beta Cartão",
    "balance": -200.0,
    "creditData": {"creditLimit": 2000.0, "availableCreditLimit": 1800.0, "balanceDueDate": "2026-09-20"},
}

CONTA_CORRENTE = {
    "id": "acc-3", "type": "BANK", "name": "Conta Corrente",
    "balance": 1500.0,
}


class TestCalcularUtilizacaoContaCredito(unittest.TestCase):
    def test_calculo_correto(self):
        util = calcular_utilizacao_conta_credito(CONTA_CREDITO_EXEMPLO)
        self.assertAlmostEqual(util, 0.88, places=2)

    def test_conta_que_nao_e_credito_rejeitada(self):
        with self.assertRaises(ErroAdaptadorPluggy):
            calcular_utilizacao_conta_credito(CONTA_CORRENTE)

    def test_limite_ausente_rejeitado(self):
        conta_sem_limite = {"type": "CREDIT", "balance": -100, "creditData": {}}
        with self.assertRaises(ErroAdaptadorPluggy):
            calcular_utilizacao_conta_credito(conta_sem_limite)

    def test_utilizacao_nunca_ultrapassa_100_por_cento(self):
        conta_estourada = {
            "type": "CREDIT", "balance": -1500.0,
            "creditData": {"creditLimit": 1000.0},
        }
        util = calcular_utilizacao_conta_credito(conta_estourada)
        self.assertEqual(util, 1.0)


class TestCalcularUtilizacaoAgregada(unittest.TestCase):
    def test_agregacao_de_multiplos_cartoes(self):
        util = calcular_utilizacao_agregada([CONTA_CREDITO_EXEMPLO, CONTA_CREDITO_2])
        # saldo total = 880+200=1080, limite total = 1000+2000=3000
        self.assertAlmostEqual(util, 1080 / 3000, places=3)

    def test_ignora_contas_que_nao_sao_credito(self):
        util = calcular_utilizacao_agregada([CONTA_CREDITO_EXEMPLO, CONTA_CORRENTE])
        self.assertAlmostEqual(util, 0.88, places=2)

    def test_nenhuma_conta_credito_lanca_erro(self):
        with self.assertRaises(ErroAdaptadorPluggy):
            calcular_utilizacao_agregada([CONTA_CORRENTE])


class TestExtrairFaturasEmAberto(unittest.TestCase):
    def test_fatura_vencida_e_extraida(self):
        hoje = date(2026, 9, 15)
        dividas = extrair_faturas_em_aberto([CONTA_CREDITO_EXEMPLO], hoje=hoje)
        self.assertEqual(len(dividas), 1)
        self.assertEqual(dividas[0].credor, "Banco XPTO Cartão")
        self.assertEqual(dividas[0].valor, 880.0)
        self.assertEqual(dividas[0].dias_atraso, 14)  # 15/09 - 01/09
        self.assertFalse(dividas[0].negativado)
        self.assertEqual(dividas[0].origem, "open_finance_pluggy")

    def test_fatura_ainda_nao_vencida_nao_e_extraida(self):
        hoje = date(2026, 9, 15)
        dividas = extrair_faturas_em_aberto([CONTA_CREDITO_2], hoje=hoje)  # vence em 20/09
        self.assertEqual(dividas, [])

    def test_conta_sem_saldo_devedor_ignorada(self):
        conta_zerada = {
            "type": "CREDIT", "name": "X", "balance": 0.0,
            "creditData": {"creditLimit": 1000.0, "balanceDueDate": "2026-08-01"},
        }
        dividas = extrair_faturas_em_aberto([conta_zerada], hoje=date(2026, 9, 15))
        self.assertEqual(dividas, [])

    def test_conta_que_nao_e_credito_ignorada_sem_erro(self):
        dividas = extrair_faturas_em_aberto([CONTA_CORRENTE], hoje=date(2026, 9, 15))
        self.assertEqual(dividas, [])


class TestMontarDadosOpenFinance(unittest.TestCase):
    def test_objeto_montado_corretamente(self):
        dados = montar_dados_open_finance(
            [CONTA_CREDITO_EXEMPLO, CONTA_CREDITO_2],
            utilizacao_credito_meta=0.3,
            meses_historico_disponivel=6,
            pontualidade_pagamentos_24m=0.9,
        )
        self.assertAlmostEqual(dados.utilizacao_credito_atual, 1080 / 3000, places=3)
        self.assertEqual(dados.utilizacao_credito_meta, 0.3)
        self.assertEqual(dados.meses_historico_disponivel, 6)


if __name__ == "__main__":
    unittest.main()
