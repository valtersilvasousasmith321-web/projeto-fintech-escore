"""
tests/test_api.py

Testes de integração da API via FastAPI TestClient.

⚠ ATENÇÃO: este arquivo requer fastapi, httpx e python-jose instalados
(pip install -r requirements.txt). Diferente de test_score_engine.py,
test_negociacao.py, test_marketplace.py e test_security.py — que rodam
com Python puro — este arquivo não pôde ser executado no ambiente de
geração desta documentação (sandbox sem acesso à internet para pip
install). Rode-o no VS Code após instalar as dependências para validar.

Rodar: pytest tests/test_api.py -v
"""

import os
import sys

os.environ.setdefault("JWT_SECRET_KEY", "chave-apenas-para-teste-nunca-usar-em-producao")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

CPF_VALIDO = "111.444.777-35"
CPF_VALIDO_2 = "529.982.247-25"


@pytest.fixture(autouse=True)
def banco_limpo(tmp_path, monkeypatch):
    """Usa um banco SQLite temporário e isolado para cada teste."""
    import app.database as db_module
    caminho_temp = tmp_path / "test.db"
    monkeypatch.setattr(db_module, "DB_PATH", caminho_temp)
    db_module.inicializar_banco(caminho_temp)

    original_obter_conexao = db_module.obter_conexao

    def obter_conexao_teste(caminho=caminho_temp):
        return original_obter_conexao(caminho)

    monkeypatch.setattr(db_module, "obter_conexao", obter_conexao_teste)
    monkeypatch.setattr("app.main.obter_conexao", obter_conexao_teste)
    yield


def _cadastrar_e_logar(email="usuario@teste.com", senha="senhaSegura123", cpf=CPF_VALIDO):
    resp_cadastro = client.post("/auth/cadastro", json={
        "documento": cpf, "email": email, "senha": senha,
    })
    assert resp_cadastro.status_code == 201, resp_cadastro.text
    usuario_id = resp_cadastro.json()["usuario_id"]

    resp_login = client.post(f"/auth/login?email={email}&senha={senha}")
    assert resp_login.status_code == 200, resp_login.text
    token = resp_login.json()["access_token"]
    return usuario_id, token


class TestHealthCheck:
    def test_health_check_ok(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestCadastroLogin:
    def test_cadastro_com_cpf_invalido_rejeitado(self):
        resp = client.post("/auth/cadastro", json={
            "documento": "111.111.111-11", "email": "x@x.com", "senha": "senhaSegura123",
        })
        assert resp.status_code == 422

    def test_cadastro_com_senha_curta_rejeitado(self):
        resp = client.post("/auth/cadastro", json={
            "documento": CPF_VALIDO, "email": "x@x.com", "senha": "123",
        })
        assert resp.status_code == 422

    def test_cadastro_e_login_fluxo_completo(self):
        usuario_id, token = _cadastrar_e_logar()
        assert usuario_id
        assert token

    def test_cadastro_duplicado_rejeitado(self):
        _cadastrar_e_logar(email="dup@teste.com", cpf=CPF_VALIDO)
        resp = client.post("/auth/cadastro", json={
            "documento": CPF_VALIDO, "email": "dup@teste.com", "senha": "outraSenha123",
        })
        assert resp.status_code == 409

    def test_login_com_senha_errada_rejeitado(self):
        _cadastrar_e_logar(email="teste2@teste.com", cpf=CPF_VALIDO_2)
        resp = client.post("/auth/login?email=teste2@teste.com&senha=senhaErrada")
        assert resp.status_code == 401

    def test_login_com_email_inexistente_mesma_mensagem_que_senha_errada(self):
        """Garante que não há user enumeration: mensagem idêntica para
        e-mail inexistente e senha errada."""
        resp_inexistente = client.post("/auth/login?email=naoexiste@teste.com&senha=qualquer123")
        assert resp_inexistente.status_code == 401
        assert resp_inexistente.json()["detail"] == "e-mail ou senha inválidos"


class TestDiagnosticoProtegido:
    def test_diagnostico_sem_token_rejeitado(self):
        resp = client.post("/score/diagnostico", json={})
        assert resp.status_code == 401

    def test_diagnostico_com_token_valido_funciona(self):
        _, token = _cadastrar_e_logar(email="score@teste.com", cpf=CPF_VALIDO_2)
        payload = {
            "documento": CPF_VALIDO_2,
            "utilizacao_credito_atual": 0.88,
            "utilizacao_credito_meta": 0.30,
            "meses_historico_disponivel": 8,
            "pontualidade_pagamentos_24m": 0.92,
            "score_atual": 560,
            "tempo_relacionamento_credito_meses": 42,
            "quantidade_tipos_credito_ativos": 3,
            "dividas_ativas": [
                {"credor": "Credor Alfa", "valor": 340.0, "dias_atraso": 120, "origem": "biro", "negativado": True},
            ],
            "consultas_cpf_ultimos_30_dias": 2,
        }
        resp = client.post("/score/diagnostico", json=payload, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["score_atual"] == 560
        assert body["score_estimado_apos_plano"] >= 560
        assert "aviso_legal" in body


class TestNegociacaoAPI:
    def test_criar_negociacao_e_fluxo_completo_ate_comissao(self):
        usuario_id, token = _cadastrar_e_logar(email="neg@teste.com", cpf=CPF_VALIDO_2)
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.post("/negociacao", json={
            "usuario_id": usuario_id, "credor": "Credor X", "valor_original": 1000.0,
        }, headers=headers)
        assert resp.status_code == 201
        negociacao_id = resp.json()["negociacao_id"]

        resp = client.post(f"/negociacao/{negociacao_id}/proposta", json={"valor_com_desconto": 700.0}, headers=headers)
        assert resp.status_code == 200

        for novo_status in ["aceita_pelo_usuario", "paga", "baixa_confirmada"]:
            resp = client.post(f"/negociacao/{negociacao_id}/transicao", json={"novo_status": novo_status}, headers=headers)
            assert resp.status_code == 200

        assert resp.json()["comissao_devida"] == 45.0  # (1000-700) * 15%

    def test_negociacao_de_outro_usuario_nao_pode_ser_acessada(self):
        usuario_id_1, token_1 = _cadastrar_e_logar(email="userA@teste.com", cpf=CPF_VALIDO)
        _, token_2 = _cadastrar_e_logar(email="userB@teste.com", cpf=CPF_VALIDO_2)

        resp = client.post("/negociacao", json={
            "usuario_id": usuario_id_1, "credor": "X", "valor_original": 500.0,
        }, headers={"Authorization": f"Bearer {token_1}"})
        negociacao_id = resp.json()["negociacao_id"]

        resp_intruso = client.post(
            f"/negociacao/{negociacao_id}/transicao",
            json={"novo_status": "cancelada"},
            headers={"Authorization": f"Bearer {token_2}"},
        )
        assert resp_intruso.status_code == 403


class TestMarketplaceAPI:
    def test_ofertas_retornadas_nunca_dizem_aprovado(self):
        _, token = _cadastrar_e_logar(email="mkt@teste.com", cpf=CPF_VALIDO_2)
        payload = {
            "score_atual": 700, "tem_restricao_ativa": False,
            "renda_declarada": 3000, "tempo_relacionamento_bancario_meses": 24,
            "ofertas_disponiveis": [
                {
                    "parceiro_id": "p1", "produto": "credito_pessoal", "score_minimo": 550,
                    "sem_restricao_ativa": True, "renda_minima_declarada": 1800,
                    "tempo_minimo_relacionamento_bancario_meses": 6,
                }
            ],
        }
        resp = client.post("/marketplace/ofertas", json=payload, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        texto_resposta = resp.text.lower()
        assert "aprovado" not in texto_resposta
        assert "garantido" not in texto_resposta
