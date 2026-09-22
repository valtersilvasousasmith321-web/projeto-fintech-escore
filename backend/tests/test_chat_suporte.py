"""
tests/test_chat_suporte.py

Testes do motor de chat de suporte próprio (sem IA externa). Roda sem
instalar nada.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.chat_suporte import (
    classificar_intencao,
    processar_mensagem,
    Intencao,
    SUGESTAO_REDIRECIONAMENTO,
    CONTATO_HUMANO,
    CONFIRMACAO_SEM_REDIRECIONAMENTO,
)


class TestClassificarIntencao(unittest.TestCase):
    def test_saudacao(self):
        self.assertEqual(classificar_intencao("Oi, bom dia!"), Intencao.SAUDACAO)

    def test_pedido_humano(self):
        self.assertEqual(classificar_intencao("quero falar com um atendente"), Intencao.PEDIDO_HUMANO)

    def test_pedido_humano_tem_prioridade_sobre_topico(self):
        # menciona "score" mas o pedido de humano deve vencer
        self.assertEqual(classificar_intencao("quero falar com um humano sobre meu score"), Intencao.PEDIDO_HUMANO)

    def test_score(self):
        self.assertEqual(classificar_intencao("por que meu score está baixo?"), Intencao.SCORE_EXPLICACAO)

    def test_negociacao_divida(self):
        self.assertEqual(classificar_intencao("como faço para negociar minha dívida?"), Intencao.NEGOCIACAO_DIVIDA)

    def test_custo(self):
        self.assertEqual(classificar_intencao("quanto custa isso?"), Intencao.CUSTO)

    def test_senha(self):
        self.assertEqual(classificar_intencao("esqueci minha senha"), Intencao.SENHA)

    def test_frustracao(self):
        self.assertEqual(classificar_intencao("isso não funciona, que absurdo"), Intencao.FRUSTRACAO)

    def test_mensagem_sem_palavra_chave_e_desconhecida(self):
        self.assertEqual(classificar_intencao("qual é a capital da frança"), Intencao.DESCONHECIDA)

    def test_normalizacao_ignora_acentos_e_maiusculas(self):
        self.assertEqual(classificar_intencao("QUANTO TEMPO demora??"), Intencao.PRAZO)


class TestProcessarMensagem(unittest.TestCase):
    def test_exige_historico_terminando_em_usuario(self):
        with self.assertRaises(ValueError):
            processar_mensagem([{"role": "assistant", "content": "oi"}])

    def test_pedido_humano_direto_da_contato_sem_oferecer_de_novo(self):
        resposta = processar_mensagem([{"role": "user", "content": "quero falar com um humano"}])
        self.assertEqual(resposta.texto, CONTATO_HUMANO)
        self.assertFalse(resposta.oferecer_redirecionamento)

    def test_frustracao_oferece_redirecionamento(self):
        resposta = processar_mensagem([{"role": "user", "content": "isso não funciona, estou irritado"}])
        self.assertTrue(resposta.oferecer_redirecionamento)
        self.assertIn(SUGESTAO_REDIRECIONAMENTO.strip(), resposta.texto)

    def test_pergunta_reconhecida_nao_oferece_redirecionamento_na_primeira_vez(self):
        resposta = processar_mensagem([{"role": "user", "content": "por que meu score está baixo?"}])
        self.assertFalse(resposta.oferecer_redirecionamento)

    def test_uma_desconhecida_isolada_nao_oferece_ainda(self):
        # primeira mensagem da conversa sendo desconhecida: ainda não tem
        # histórico anterior de desconhecidas, então não oferece
        resposta = processar_mensagem([{"role": "user", "content": "qual é a capital da frança"}])
        self.assertFalse(resposta.oferecer_redirecionamento)

    def test_duas_desconhecidas_seguidas_oferece_redirecionamento(self):
        historico = [
            {"role": "user", "content": "qual é a capital da frança"},
            {"role": "assistant", "content": "Não tenho certeza se entendi sua pergunta."},
            {"role": "user", "content": "quanto é 2 mais 2"},
        ]
        resposta = processar_mensagem(historico)
        self.assertTrue(resposta.oferecer_redirecionamento)

    def test_confirmacao_positiva_apos_oferta_vira_contato_humano(self):
        historico = [
            {"role": "user", "content": "isso não funciona"},
            {"role": "assistant", "content": "Sinto muito." + SUGESTAO_REDIRECIONAMENTO},
            {"role": "user", "content": "sim, por favor"},
        ]
        resposta = processar_mensagem(historico)
        self.assertEqual(resposta.texto, CONTATO_HUMANO)
        self.assertFalse(resposta.oferecer_redirecionamento)

    def test_confirmacao_negativa_apos_oferta_nao_redireciona(self):
        historico = [
            {"role": "user", "content": "isso não funciona"},
            {"role": "assistant", "content": "Sinto muito." + SUGESTAO_REDIRECIONAMENTO},
            {"role": "user", "content": "não, deixa"},
        ]
        resposta = processar_mensagem(historico)
        self.assertEqual(resposta.texto, CONFIRMACAO_SEM_REDIRECIONAMENTO)

    def test_confirmacao_positiva_sem_oferta_anterior_e_tratada_normalmente(self):
        # "sim" sozinho, sem contexto de oferta prévia, não deveria virar
        # contato humano do nada
        resposta = processar_mensagem([{"role": "user", "content": "sim"}])
        self.assertNotEqual(resposta.texto, CONTATO_HUMANO)


if __name__ == "__main__":
    unittest.main()
