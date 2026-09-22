"""
tests/test_serasa_adapter.py

Testes do adaptador CredNet -> Divida/score. O fixture RESPOSTA_HOMOLOGACAO
é EXATAMENTE o JSON retornado pela conta de homologação do usuário no
SOA Web Services (Serasa CredNet) — dado real de ambiente de teste,
não inventado.
"""

import sys
import os
from datetime import date
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.serasa_adapter import (
    transacao_bem_sucedida, extrair_score, extrair_probabilidade_inadimplencia,
    extrair_dividas_negativadas, extrair_consultas_recentes,
    extrair_confirmacao_exclusao, resposta_indica_cpf_sem_restricao, ErroAdaptadorSerasa,
)


# JSON real devolvido pela conta de homologação (ambiente de teste do
# provedor gera valores fixos como 1 e datas de hoje — não é dado de
# CPF real, é o "eco" padrão de homologação).
RESPOSTA_HOMOLOGACAO = {
    "sinteseCadastral": {
        "pessoaFisica": {"documento": None, "nome": None, "dataNascimento": "2026-09-18"},
    },
    "dadosNegativos": {
        "resumo": {"totalOcorrencias": 1, "valorTotal": 1, "mensagem": None},
        "pendenciasFinanceiras": {
            "detalhes": [
                {
                    "dataOcorrencia": "2026-09-18", "modalidade": None, "contrato": None,
                    "credor": None, "valor": 1, "principal": True, "cidade": None,
                    "disputa": {"indicadorDisputa": True}, "cadus": None,
                }
            ],
            "resumo": {"totalOcorrencias": 1, "valorTotal": 1},
        },
        "restricoesFinanceiras": {
            "detalhes": [
                {
                    "dataOcorrencia": "2026-09-18", "modalidade": None, "contrato": None,
                    "credor": None, "valor": 1, "principal": True, "cidade": None,
                    "disputa": {"indicadorDisputa": True}, "cadus": None,
                }
            ],
            "resumo": {"totalOcorrencias": 1, "valorTotal": 1},
        },
    },
    "informacoesAdicionais": {
        "score": {
            "pontuacao": 1, "modelo": None, "faixa": None,
            "probabilidadeInadimplencia": 1, "codigoMensagem": 1, "mensagem": None,
        },
    },
    "transacao": {"status": True, "codigoStatus": None, "codigoStatusDescricao": None},
}


class TestTransacaoBemSucedida(unittest.TestCase):
    def test_status_true_e_sucesso(self):
        self.assertTrue(transacao_bem_sucedida(RESPOSTA_HOMOLOGACAO))

    def test_status_false_e_falha(self):
        resposta = {"transacao": {"status": False}}
        self.assertFalse(transacao_bem_sucedida(resposta))

    def test_ausencia_de_transacao_e_falha(self):
        self.assertFalse(transacao_bem_sucedida({}))


class TestExtrairScore(unittest.TestCase):
    def test_extrai_pontuacao_do_json_real(self):
        self.assertEqual(extrair_score(RESPOSTA_HOMOLOGACAO), 1)

    def test_score_ausente_retorna_none(self):
        resposta = {"informacoesAdicionais": {"score": {"pontuacao": None}}}
        self.assertIsNone(extrair_score(resposta))

    def test_secao_informacoesAdicionais_ausente_retorna_none(self):
        self.assertIsNone(extrair_score({}))

    def test_score_fora_da_faixa_lanca_erro(self):
        resposta = {"informacoesAdicionais": {"score": {"pontuacao": 5000}}}
        with self.assertRaises(ErroAdaptadorSerasa):
            extrair_score(resposta)

    def test_score_valido_realista(self):
        resposta = {"informacoesAdicionais": {"score": {"pontuacao": 650}}}
        self.assertEqual(extrair_score(resposta), 650)


class TestExtrairProbabilidadeInadimplencia(unittest.TestCase):
    def test_extrai_do_json_real(self):
        self.assertEqual(extrair_probabilidade_inadimplencia(RESPOSTA_HOMOLOGACAO), 1)

    def test_ausente_retorna_none(self):
        self.assertIsNone(extrair_probabilidade_inadimplencia({}))


class TestExtrairDividasNegativadas(unittest.TestCase):
    def test_extrai_duas_dividas_do_json_real(self):
        # uma de pendenciasFinanceiras + uma de restricoesFinanceiras
        dividas = extrair_dividas_negativadas(RESPOSTA_HOMOLOGACAO, hoje=date(2026, 9, 18))
        self.assertEqual(len(dividas), 2)
        self.assertTrue(all(d.negativado for d in dividas))

    def test_credor_nulo_recebe_texto_padrao(self):
        dividas = extrair_dividas_negativadas(RESPOSTA_HOMOLOGACAO, hoje=date(2026, 9, 18))
        self.assertEqual(dividas[0].credor, "Credor não informado pelo birô")

    def test_dias_atraso_calculado_corretamente(self):
        resposta = {
            "dadosNegativos": {
                "pendenciasFinanceiras": {
                    "detalhes": [{"dataOcorrencia": "2026-05-18", "credor": "Credor X", "valor": 340.0}]
                }
            }
        }
        dividas = extrair_dividas_negativadas(resposta, hoje=date(2026, 9, 18))
        self.assertEqual(len(dividas), 1)
        self.assertEqual(dividas[0].dias_atraso, 123)  # 18/05 -> 18/09

    def test_valor_zero_ou_ausente_e_ignorado(self):
        resposta = {
            "dadosNegativos": {
                "pendenciasFinanceiras": {"detalhes": [{"dataOcorrencia": "2026-01-01", "valor": 0}]}
            }
        }
        dividas = extrair_dividas_negativadas(resposta)
        self.assertEqual(dividas, [])

    def test_sem_dados_negativos_retorna_lista_vazia(self):
        self.assertEqual(extrair_dividas_negativadas({}), [])

    def test_origem_diferencia_pendencia_de_restricao(self):
        dividas = extrair_dividas_negativadas(RESPOSTA_HOMOLOGACAO, hoje=date(2026, 9, 18))
        origens = {d.origem for d in dividas}
        self.assertEqual(origens, {"serasa_crednet_pendencia", "serasa_crednet_restricao"})


class TestExtrairConsultasRecentes(unittest.TestCase):
    def test_consulta_dentro_do_limite_e_contada(self):
        resposta = {"outrasInformacoes": {"registroConsultas": {"detalhes": [{"quantidadeDias": 1}]}}}
        self.assertEqual(extrair_consultas_recentes(resposta), 1)

    def test_consulta_fora_do_limite_nao_e_contada(self):
        resposta = {"outrasInformacoes": {"registroConsultas": {"detalhes": [{"quantidadeDias": 45}]}}}
        self.assertEqual(extrair_consultas_recentes(resposta), 0)

    def test_mistura_dentro_e_fora_do_limite(self):
        resposta = {
            "outrasInformacoes": {
                "registroConsultas": {"detalhes": [{"quantidadeDias": 5}, {"quantidadeDias": 60}, {"quantidadeDias": 20}]}
            }
        }
        self.assertEqual(extrair_consultas_recentes(resposta), 2)

    def test_sem_detalhes_retorna_zero(self):
        self.assertEqual(extrair_consultas_recentes({}), 0)

    def test_limite_customizado(self):
        resposta = {"outrasInformacoes": {"registroConsultas": {"detalhes": [{"quantidadeDias": 45}]}}}
        self.assertEqual(extrair_consultas_recentes(resposta, limite_dias=60), 1)


class TestExtrairConfirmacaoExclusao(unittest.TestCase):
    # JSON real devolvido pela conta de homologação do usuário ao testar
    # /api/v2/Serasa/Negativacoes/Excluir
    RESPOSTA_EXCLUSAO_REAL = {
        "uniqueID": "123e4567-e89b-12d3-a456-426614174000",
        "documentoCredor": None,
        "nomeCredor": None,
        "documentoDevedor": None,
        "nomeDevedor": None,
        "codigoRestricao": 1,
        "restricaoDescricao": None,
        "codigoBaixa": 1,
        "baixaDescricao": None,
        "valor": 1,
        "dataHoraExclusao": "2026-09-18",
        "transacao": {"status": True, "codigoStatus": None, "codigoStatusDescricao": None},
    }

    def test_extrai_unique_id_do_json_real(self):
        resultado = extrair_confirmacao_exclusao(self.RESPOSTA_EXCLUSAO_REAL)
        self.assertEqual(resultado["unique_id"], "123e4567-e89b-12d3-a456-426614174000")

    def test_extrai_data_da_exclusao(self):
        resultado = extrair_confirmacao_exclusao(self.RESPOSTA_EXCLUSAO_REAL)
        self.assertEqual(resultado["data_hora_exclusao"], "2026-09-18")

    def test_sucesso_true_quando_transacao_ok(self):
        resultado = extrair_confirmacao_exclusao(self.RESPOSTA_EXCLUSAO_REAL)
        self.assertTrue(resultado["sucesso"])

    def test_sucesso_false_quando_transacao_falha(self):
        resposta = {**self.RESPOSTA_EXCLUSAO_REAL, "transacao": {"status": False}}
        resultado = extrair_confirmacao_exclusao(resposta)
        self.assertFalse(resultado["sucesso"])

    def test_resposta_vazia_nao_quebra(self):
        resultado = extrair_confirmacao_exclusao({})
        self.assertIsNone(resultado["unique_id"])
        self.assertFalse(resultado["sucesso"])


class TestRespostaIndicaCpfSemRestricao(unittest.TestCase):
    def test_com_ocorrencias_retorna_falso(self):
        self.assertFalse(resposta_indica_cpf_sem_restricao(RESPOSTA_HOMOLOGACAO))

    def test_sem_ocorrencias_retorna_verdadeiro(self):
        resposta = {"dadosNegativos": {"resumo": {"totalOcorrencias": 0}}}
        self.assertTrue(resposta_indica_cpf_sem_restricao(resposta))

    def test_campo_ausente_assume_sem_restricao(self):
        self.assertTrue(resposta_indica_cpf_sem_restricao({}))


if __name__ == "__main__":
    unittest.main()
