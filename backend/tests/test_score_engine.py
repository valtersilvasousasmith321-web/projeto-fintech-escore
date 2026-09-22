"""
tests/test_score_engine.py

Testes do motor de score. Usa apenas unittest (stdlib) — roda sem
nenhuma dependência externa instalada.

Rodar: python3 -m unittest tests.test_score_engine -v
(ou: pytest tests/ — ambos funcionam, já que os testes usam unittest.TestCase)
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.score_engine import (
    Divida,
    DadosOpenFinance,
    DadosBiro,
    ErroValidacao,
    rodar_auditoria,
    calcular_fator_confianca,
    calcular_impacto_reducao_utilizacao,
    calcular_impacto_quitacao_divida,
    calcular_penalizacao_consultas,
    SCORE_MIN,
    SCORE_MAX,
)


class TestValidacaoDados(unittest.TestCase):
    def test_divida_valor_negativo_rejeitada(self):
        with self.assertRaises(ErroValidacao):
            Divida(credor="X", valor=-10, dias_atraso=5, origem="biro", negativado=True)

    def test_divida_dias_atraso_negativo_rejeitada(self):
        with self.assertRaises(ErroValidacao):
            Divida(credor="X", valor=100, dias_atraso=-1, origem="biro", negativado=True)

    def test_divida_credor_vazio_rejeitada(self):
        with self.assertRaises(ErroValidacao):
            Divida(credor="  ", valor=100, dias_atraso=5, origem="biro", negativado=True)

    def test_utilizacao_fora_da_faixa_rejeitada(self):
        with self.assertRaises(ErroValidacao):
            DadosOpenFinance(
                utilizacao_credito_atual=1.5,  # inválido, > 1.0
                utilizacao_credito_meta=0.3,
                meses_historico_disponivel=6,
                pontualidade_pagamentos_24m=0.9,
            )

    def test_score_fora_da_faixa_rejeitado(self):
        with self.assertRaises(ErroValidacao):
            DadosBiro(
                score_atual=1500,  # inválido, > 1000
                tempo_relacionamento_credito_meses=12,
                quantidade_tipos_credito_ativos=2,
                dividas_ativas=[],
                consultas_cpf_ultimos_30_dias=0,
            )

    def test_score_negativo_rejeitado(self):
        with self.assertRaises(ErroValidacao):
            DadosBiro(
                score_atual=-1,
                tempo_relacionamento_credito_meses=12,
                quantidade_tipos_credito_ativos=2,
                dividas_ativas=[],
                consultas_cpf_ultimos_30_dias=0,
            )


class TestFatorConfianca(unittest.TestCase):
    def test_sem_historico_confianca_minima(self):
        self.assertEqual(calcular_fator_confianca(0), 0.5)

    def test_historico_negativo_trata_como_zero(self):
        self.assertEqual(calcular_fator_confianca(-5), 0.5)

    def test_historico_maximo_confianca_maxima(self):
        self.assertEqual(calcular_fator_confianca(12), 0.9)

    def test_historico_acima_do_teto_nao_ultrapassa_09(self):
        self.assertEqual(calcular_fator_confianca(100), 0.9)

    def test_historico_parcial_intermediario(self):
        resultado = calcular_fator_confianca(6)
        self.assertTrue(0.5 < resultado < 0.9)


class TestImpactoUtilizacao(unittest.TestCase):
    def test_reducao_gera_impacto_positivo(self):
        imp_min, imp_max = calcular_impacto_reducao_utilizacao(0.9, 0.3, 0.7)
        self.assertGreater(imp_min, 0)
        self.assertGreater(imp_max, imp_min)

    def test_sem_reducao_impacto_zero(self):
        imp_min, imp_max = calcular_impacto_reducao_utilizacao(0.3, 0.3, 0.7)
        self.assertEqual(imp_min, 0.0)
        self.assertEqual(imp_max, 0.0)

    def test_utilizacao_ja_abaixo_da_meta_nao_gera_impacto_negativo(self):
        imp_min, imp_max = calcular_impacto_reducao_utilizacao(0.1, 0.3, 0.7)
        self.assertEqual(imp_min, 0.0)
        self.assertEqual(imp_max, 0.0)


class TestImpactoQuitacaoDivida(unittest.TestCase):
    def test_divida_mais_antiga_gera_impacto_maior(self):
        imp_recente = calcular_impacto_quitacao_divida(500, 10, 0.7)
        imp_antiga = calcular_impacto_quitacao_divida(500, 300, 0.7)
        self.assertGreater(imp_antiga[1], imp_recente[1])

    def test_impacto_sempre_positivo(self):
        imp_min, imp_max = calcular_impacto_quitacao_divida(100, 5, 0.5)
        self.assertGreater(imp_min, 0)


class TestPenalizacaoConsultas(unittest.TestCase):
    def test_sem_consultas_sem_penalizacao(self):
        self.assertEqual(calcular_penalizacao_consultas(0), 0.0)

    def test_multiplas_consultas_penalizacao_crescente(self):
        pen_1 = calcular_penalizacao_consultas(1)
        pen_3 = calcular_penalizacao_consultas(3)
        # 3 consultas deve penalizar mais que 3x uma única consulta
        # (severidade crescente por consulta adicional)
        self.assertGreater(pen_3, pen_1 * 3)


class TestRodarAuditoriaIntegracao(unittest.TestCase):
    def setUp(self):
        self.dados_of = DadosOpenFinance(
            utilizacao_credito_atual=0.88,
            utilizacao_credito_meta=0.30,
            meses_historico_disponivel=8,
            pontualidade_pagamentos_24m=0.92,
        )
        self.dados_biro = DadosBiro(
            score_atual=560,
            tempo_relacionamento_credito_meses=42,
            quantidade_tipos_credito_ativos=3,
            dividas_ativas=[
                Divida(credor="Credor Alfa", valor=340.0, dias_atraso=120, origem="biro_serasa", negativado=True),
                Divida(credor="Loja Beta", valor=89.9, dias_atraso=30, origem="biro_boa_vista", negativado=True),
            ],
            consultas_cpf_ultimos_30_dias=2,
        )

    def test_score_estimado_maior_que_atual_quando_ha_acoes_positivas(self):
        resultado = rodar_auditoria(self.dados_of, self.dados_biro)
        self.assertGreaterEqual(resultado.score_estimado_apos_plano, resultado.score_atual)

    def test_score_estimado_nunca_ultrapassa_limites(self):
        resultado = rodar_auditoria(self.dados_of, self.dados_biro)
        self.assertGreaterEqual(resultado.score_estimado_apos_plano, SCORE_MIN)
        self.assertLessEqual(resultado.score_estimado_apos_plano, SCORE_MAX)

    def test_plano_ordenado_por_impacto_decrescente(self):
        resultado = rodar_auditoria(self.dados_of, self.dados_biro)
        impactos = [a.impacto_estimado_max for a in resultado.plano_acao]
        self.assertEqual(impactos, sorted(impactos, reverse=True))

    def test_alerta_gerado_para_divida_critica(self):
        resultado = rodar_auditoria(self.dados_of, self.dados_biro)
        self.assertTrue(any("divida_critica" in a for a in resultado.alertas))

    def test_alerta_gerado_para_consulta_recente(self):
        resultado = rodar_auditoria(self.dados_of, self.dados_biro)
        self.assertTrue(any("nova_consulta_cpf_detectada" in a for a in resultado.alertas))

    def test_score_extremo_1000_nao_estoura_limite(self):
        dados_biro_no_limite = DadosBiro(
            score_atual=999,
            tempo_relacionamento_credito_meses=100,
            quantidade_tipos_credito_ativos=5,
            dividas_ativas=[
                Divida(credor="X", valor=10000, dias_atraso=365, origem="biro", negativado=True),
            ],
            consultas_cpf_ultimos_30_dias=0,
        )
        resultado = rodar_auditoria(self.dados_of, dados_biro_no_limite)
        self.assertLessEqual(resultado.score_estimado_apos_plano, SCORE_MAX)

    def test_sem_dividas_nem_consultas_plano_pode_ficar_vazio_ou_so_utilizacao(self):
        dados_biro_limpo = DadosBiro(
            score_atual=750,
            tempo_relacionamento_credito_meses=50,
            quantidade_tipos_credito_ativos=3,
            dividas_ativas=[],
            consultas_cpf_ultimos_30_dias=0,
        )
        dados_of_ok = DadosOpenFinance(
            utilizacao_credito_atual=0.2,
            utilizacao_credito_meta=0.3,
            meses_historico_disponivel=12,
            pontualidade_pagamentos_24m=1.0,
        )
        resultado = rodar_auditoria(dados_of_ok, dados_biro_limpo)
        self.assertEqual(resultado.plano_acao, [])
        self.assertEqual(resultado.alertas, [])


if __name__ == "__main__":
    unittest.main()
