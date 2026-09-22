"""
tests/test_marketplace.py

Testes do motor de elegibilidade do marketplace. Garante que o motor
NUNCA retorna "aprovado" — apenas percentual de aderência.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.marketplace import (
    CriteriosParceiro,
    PerfilUsuario,
    avaliar_elegibilidade,
    rankear_ofertas,
    ErroValidacaoMarketplace,
)


class TestValidacaoCriterios(unittest.TestCase):
    def test_score_minimo_negativo_rejeitado(self):
        with self.assertRaises(ErroValidacaoMarketplace):
            CriteriosParceiro(
                parceiro_id="p1", produto="credito_pessoal", score_minimo=-1,
                sem_restricao_ativa=True, renda_minima_declarada=1000,
                tempo_minimo_relacionamento_bancario_meses=6,
            )


class TestAvaliarElegibilidade(unittest.TestCase):
    def setUp(self):
        self.criterios = CriteriosParceiro(
            parceiro_id="fintech_x", produto="credito_pessoal", score_minimo=550,
            sem_restricao_ativa=True, renda_minima_declarada=1800,
            tempo_minimo_relacionamento_bancario_meses=6,
        )

    def test_perfil_que_atende_tudo_100_por_cento(self):
        perfil = PerfilUsuario(
            score_atual=700, tem_restricao_ativa=False,
            renda_declarada=3000, tempo_relacionamento_bancario_meses=24,
        )
        resultado = avaliar_elegibilidade(perfil, self.criterios)
        self.assertEqual(resultado.percentual_aderencia, 1.0)
        self.assertTrue(resultado.elegivel_para_exibicao)
        self.assertEqual(resultado.criterios_atendidos, resultado.criterios_totais)

    def test_perfil_que_nao_atende_score_minimo(self):
        perfil = PerfilUsuario(
            score_atual=400, tem_restricao_ativa=False,
            renda_declarada=3000, tempo_relacionamento_bancario_meses=24,
        )
        resultado = avaliar_elegibilidade(perfil, self.criterios)
        self.assertFalse(resultado.detalhamento["score_minimo"])
        self.assertLess(resultado.percentual_aderencia, 1.0)

    def test_perfil_com_restricao_ativa_falha_criterio(self):
        perfil = PerfilUsuario(
            score_atual=700, tem_restricao_ativa=True,
            renda_declarada=3000, tempo_relacionamento_bancario_meses=24,
        )
        resultado = avaliar_elegibilidade(perfil, self.criterios)
        self.assertFalse(resultado.detalhamento["sem_restricao_ativa"])

    def test_resultado_nunca_contem_campo_aprovado(self):
        """Garante estruturalmente que o motor não expõe nenhum campo
        que sugira decisão de aprovação — só percentual de aderência."""
        perfil = PerfilUsuario(
            score_atual=700, tem_restricao_ativa=False,
            renda_declarada=3000, tempo_relacionamento_bancario_meses=24,
        )
        resultado = avaliar_elegibilidade(perfil, self.criterios)
        campos = resultado.__dataclass_fields__.keys()
        for campo in campos:
            self.assertNotIn("aprovad", campo.lower())
            self.assertNotIn("garanti", campo.lower())

    def test_baixa_aderencia_nao_e_exibivel(self):
        perfil = PerfilUsuario(
            score_atual=100, tem_restricao_ativa=True,
            renda_declarada=100, tempo_relacionamento_bancario_meses=0,
        )
        resultado = avaliar_elegibilidade(perfil, self.criterios)
        self.assertFalse(resultado.elegivel_para_exibicao)


class TestRankearOfertas(unittest.TestCase):
    def test_ofertas_ordenadas_por_aderencia_decrescente(self):
        perfil = PerfilUsuario(
            score_atual=600, tem_restricao_ativa=False,
            renda_declarada=2000, tempo_relacionamento_bancario_meses=12,
        )
        criterios = [
            CriteriosParceiro("p1", "credito_pessoal", 550, True, 1800, 6),
            CriteriosParceiro("p2", "credito_pessoal", 800, True, 5000, 36),  # aderência baixa
            CriteriosParceiro("p3", "credito_pessoal", 500, False, 1000, 3),  # aderência alta
        ]
        ranking = rankear_ofertas(perfil, criterios)
        percentuais = [r.percentual_aderencia for r in ranking]
        self.assertEqual(percentuais, sorted(percentuais, reverse=True))

    def test_ofertas_com_aderencia_muito_baixa_nao_aparecem(self):
        perfil = PerfilUsuario(
            score_atual=100, tem_restricao_ativa=True,
            renda_declarada=0, tempo_relacionamento_bancario_meses=0,
        )
        criterios = [CriteriosParceiro("p1", "credito_pessoal", 800, True, 5000, 36)]
        ranking = rankear_ofertas(perfil, criterios)
        self.assertEqual(ranking, [])


if __name__ == "__main__":
    unittest.main()
