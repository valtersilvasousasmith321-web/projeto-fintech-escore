"""
tests/test_serasa_client_url.py

Testa APENAS a lógica de escolha de URL (homologação vs produção) do
SerasaClient — não faz chamada de rede real. Como httpx pode não
estar instalado neste ambiente, ele é simulado (stub mínimo) só pra
permitir o import do módulo; nenhuma requisição HTTP é de fato feita
por estes testes.
"""

import sys
import os
import types
import unittest

# Stub de httpx só pra viabilizar o import QUANDO httpx genuinamente
# não está instalado (ex: este sandbox de geração, sem internet).
# Se o httpx real já estiver disponível (ambiente normal do usuário
# depois do pip install), usamos o real e nunca o substituímos — isso
# evita quebrar outros testes que precisam do httpx funcionando de
# verdade (ex: test_api.py via FastAPI TestClient).
try:
    import httpx  # noqa: F401
except ImportError:
    _httpx_stub = types.ModuleType("httpx")

    class _ClientStub:
        def __init__(self, *args, **kwargs):
            pass

    _httpx_stub.Client = _ClientStub
    sys.modules["httpx"] = _httpx_stub

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.integrations.serasa_client import (
    SerasaClient, SOA_BASE_URL_HOMOLOGACAO, SOA_BASE_URL_PRODUCAO,
)


class TestResolucaoDeUrl(unittest.TestCase):
    def setUp(self):
        os.environ["SOA_EMAIL"] = "teste@teste.com"
        os.environ["SOA_SENHA"] = "senha-teste"
        for chave in ("SOA_BASE_URL", "SOA_AMBIENTE"):
            os.environ.pop(chave, None)

    def tearDown(self):
        for chave in ("SOA_EMAIL", "SOA_SENHA", "SOA_BASE_URL", "SOA_AMBIENTE"):
            os.environ.pop(chave, None)

    def test_padrao_sem_configuracao_e_homologacao(self):
        """Segurança: sem nada configurado, nunca cai em produção por acidente."""
        cliente = SerasaClient()
        self.assertEqual(cliente.base_url, SOA_BASE_URL_HOMOLOGACAO)

    def test_soa_ambiente_producao(self):
        os.environ["SOA_AMBIENTE"] = "producao"
        cliente = SerasaClient()
        self.assertEqual(cliente.base_url, SOA_BASE_URL_PRODUCAO)

    def test_soa_ambiente_homologacao_explicito(self):
        os.environ["SOA_AMBIENTE"] = "homologacao"
        cliente = SerasaClient()
        self.assertEqual(cliente.base_url, SOA_BASE_URL_HOMOLOGACAO)

    def test_soa_ambiente_valor_invalido_cai_em_homologacao(self):
        os.environ["SOA_AMBIENTE"] = "qualquer-coisa-invalida"
        cliente = SerasaClient()
        self.assertEqual(cliente.base_url, SOA_BASE_URL_HOMOLOGACAO)

    def test_soa_base_url_explicita_tem_prioridade_sobre_ambiente(self):
        os.environ["SOA_AMBIENTE"] = "producao"
        os.environ["SOA_BASE_URL"] = "https://url-customizada-de-teste.com"
        cliente = SerasaClient()
        self.assertEqual(cliente.base_url, "https://url-customizada-de-teste.com")

    def test_base_url_passada_no_construtor_tem_prioridade_maxima(self):
        os.environ["SOA_AMBIENTE"] = "producao"
        cliente = SerasaClient(base_url="https://url-passada-direto.com")
        self.assertEqual(cliente.base_url, "https://url-passada-direto.com")


class TestMascaramentoDeSenhaNoLog(unittest.TestCase):
    """Garante que a senha nunca aparece em texto puro, mesmo em log
    interno do servidor — defesa em profundidade contra a API da SOA
    ecoar a requisição de volta num erro."""

    def setUp(self):
        os.environ["SOA_EMAIL"] = "teste@teste.com"
        os.environ["SOA_SENHA"] = "senha-super-secreta-123"

    def tearDown(self):
        for chave in ("SOA_EMAIL", "SOA_SENHA"):
            os.environ.pop(chave, None)

    def test_senha_e_removida_do_texto(self):
        cliente = SerasaClient()
        texto_com_senha = 'erro: {"credenciais": {"senha": "senha-super-secreta-123"}}'
        resultado = cliente._mascarar_senha(texto_com_senha)
        self.assertNotIn("senha-super-secreta-123", resultado)
        self.assertIn("***SENHA_MASCARADA***", resultado)

    def test_texto_sem_senha_permanece_igual(self):
        cliente = SerasaClient()
        texto = "erro genérico sem dado sensível"
        self.assertEqual(cliente._mascarar_senha(texto), texto)

    def test_texto_vazio_nao_quebra(self):
        cliente = SerasaClient()
        self.assertEqual(cliente._mascarar_senha(""), "")


if __name__ == "__main__":
    unittest.main()
