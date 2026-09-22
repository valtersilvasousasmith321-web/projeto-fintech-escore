import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.billing import (
    PlanoAssinatura, obter_valor_plano, ErroCobranca,
    token_webhook_valido, interpretar_webhook_pagamento, TipoEventoAsaas,
    PRECO_CONSULTA_AVULSA,
)


class TestObterValorPlano(unittest.TestCase):
    def test_plano_plus(self):
        self.assertEqual(obter_valor_plano(PlanoAssinatura.PLUS), 19.90)

    def test_plano_premium(self):
        self.assertEqual(obter_valor_plano(PlanoAssinatura.PREMIUM), 39.90)


class TestPrecoConsultaAvulsa(unittest.TestCase):
    """Trava a regra de negócio mais importante desse preço: nunca
    pode ficar abaixo do custo real da consulta (~R$16,06 confirmado
    no painel da SOA), senão cada venda dá prejuízo em vez de lucro."""

    CUSTO_REAL_CONSULTA_CREDNET = 16.06

    def test_preco_avulso_cobre_o_custo_real_com_margem(self):
        self.assertGreater(PRECO_CONSULTA_AVULSA, self.CUSTO_REAL_CONSULTA_CREDNET)


class TestTokenWebhook(unittest.TestCase):
    def test_token_correto_aceito(self):
        self.assertTrue(token_webhook_valido("segredo123", "segredo123"))

    def test_token_incorreto_rejeitado(self):
        self.assertFalse(token_webhook_valido("errado", "segredo123"))

    def test_token_ausente_rejeitado(self):
        self.assertFalse(token_webhook_valido(None, "segredo123"))

    def test_token_vazio_rejeitado(self):
        self.assertFalse(token_webhook_valido("", "segredo123"))


class TestInterpretarWebhookPagamento(unittest.TestCase):
    def test_pagamento_confirmado(self):
        payload = {
            "event": "PAYMENT_CONFIRMED",
            "payment": {"id": "pay_123", "customer": "cus_456", "value": 19.90},
        }
        resultado = interpretar_webhook_pagamento(payload)
        self.assertEqual(resultado.tipo, TipoEventoAsaas.PAGAMENTO_CONFIRMADO)
        self.assertEqual(resultado.asaas_payment_id, "pay_123")
        self.assertEqual(resultado.asaas_customer_id, "cus_456")
        self.assertEqual(resultado.valor, 19.90)

    def test_pagamento_recebido(self):
        payload = {"event": "PAYMENT_RECEIVED", "payment": {"id": "pay_1", "customer": "cus_1", "value": 100.0}}
        resultado = interpretar_webhook_pagamento(payload)
        self.assertEqual(resultado.tipo, TipoEventoAsaas.PAGAMENTO_RECEBIDO)

    def test_pagamento_atrasado(self):
        payload = {"event": "PAYMENT_OVERDUE", "payment": {"id": "pay_1", "customer": "cus_1", "value": 100.0}}
        resultado = interpretar_webhook_pagamento(payload)
        self.assertEqual(resultado.tipo, TipoEventoAsaas.PAGAMENTO_ATRASADO)

    def test_pagamento_cancelado_via_deletado(self):
        payload = {"event": "PAYMENT_DELETED", "payment": {"id": "pay_1", "customer": "cus_1", "value": 100.0}}
        resultado = interpretar_webhook_pagamento(payload)
        self.assertEqual(resultado.tipo, TipoEventoAsaas.PAGAMENTO_CANCELADO)

    def test_evento_desconhecido_nao_quebra(self):
        payload = {"event": "ALGO_NOVO_QUE_NAO_MAPEAMOS", "payment": {"id": "pay_1", "customer": "cus_1", "value": 1.0}}
        resultado = interpretar_webhook_pagamento(payload)
        self.assertEqual(resultado.tipo, TipoEventoAsaas.DESCONHECIDO)

    def test_payload_sem_payment_nao_quebra(self):
        resultado = interpretar_webhook_pagamento({"event": "PAYMENT_CONFIRMED"})
        self.assertIsNone(resultado.asaas_payment_id)
        self.assertIsNone(resultado.valor)

    def test_payload_vazio_nao_quebra(self):
        resultado = interpretar_webhook_pagamento({})
        self.assertEqual(resultado.tipo, TipoEventoAsaas.DESCONHECIDO)


if __name__ == "__main__":
    unittest.main()
