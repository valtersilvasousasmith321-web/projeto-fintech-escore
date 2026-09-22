"""
app/integrations/pluggy_client.py

Cliente de integração com a API da Pluggy (agregador de Open Finance
certificado pelo Banco Central — https://docs.pluggy.ai).

Fluxo de autenticação real da Pluggy (confirmado na documentação oficial):

  1. Backend troca CLIENT_ID + CLIENT_SECRET por uma API Key
     (POST /auth) — válida por 2 horas, usada em todas as chamadas
     server-to-server.
  2. Para o frontend/widget de conexão do usuário, o backend gera um
     Connect Token (POST /connect_token, autenticado com a API Key) —
     válido por 30 minutos, com acesso restrito (só aquele item/conta).
  3. Depois que o usuário conecta a conta no widget, o backend usa a
     API Key para buscar os dados: GET /accounts?itemId=...,
     GET /transactions?accountId=...

Credenciais de sandbox são gratuitas — criar conta em https://dashboard.pluggy.ai

IMPORTANTE: este cliente faz chamadas HTTP reais. Ele não pôde ser
testado neste ambiente de geração de documentação (sandbox sem acesso
à internet). O que FOI testado e roda sem rede é o adaptador de dados
em app/integrations/pluggy_adapter.py, que processa a resposta já
recebida da API — essa é a parte com lógica de negócio real.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import httpx

PLUGGY_BASE_URL = "https://api.pluggy.ai"


class ErroIntegracaoPluggy(Exception):
    pass


class PluggyClient:
    def __init__(self, client_id: str | None = None, client_secret: str | None = None, timeout: float = 15.0):
        self.client_id = client_id or os.environ.get("PLUGGY_CLIENT_ID")
        self.client_secret = client_secret or os.environ.get("PLUGGY_CLIENT_SECRET")
        if not self.client_id or not self.client_secret:
            raise ErroIntegracaoPluggy(
                "PLUGGY_CLIENT_ID e PLUGGY_CLIENT_SECRET precisam estar configurados "
                "(variáveis de ambiente ou parâmetro do construtor). "
                "Crie credenciais de sandbox gratuitas em https://dashboard.pluggy.ai"
            )
        self._timeout = timeout
        self._api_key: str | None = None
        self._api_key_expira_em: datetime | None = None

    def _api_key_valida(self) -> str:
        agora = datetime.now(timezone.utc)
        if self._api_key is None or self._api_key_expira_em is None or agora >= self._api_key_expira_em:
            self._autenticar()
        return self._api_key  # type: ignore[return-value]

    def _autenticar(self) -> None:
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.post(
                f"{PLUGGY_BASE_URL}/auth",
                json={"clientId": self.client_id, "clientSecret": self.client_secret},
                headers={"accept": "application/json", "content-type": "application/json"},
            )
        if resp.status_code != 200:
            raise ErroIntegracaoPluggy(f"Falha ao autenticar na Pluggy: {resp.status_code} {resp.text}")
        dados = resp.json()
        self._api_key = dados["apiKey"]
        # API key expira em 2h — renovamos com 5 min de folga
        self._api_key_expira_em = datetime.now(timezone.utc) + timedelta(hours=2, minutes=-5)

    def criar_connect_token(self, client_user_id: str, oauth_redirect_uri: str | None = None) -> str:
        """Gera o token de 30 min usado pelo frontend (widget Pluggy Connect)
        para o usuário autorizar a conexão com o banco dele."""
        api_key = self._api_key_valida()
        payload: dict = {"clientUserId": client_user_id}
        if oauth_redirect_uri:
            payload["options"] = {"oauthRedirectUri": oauth_redirect_uri}

        with httpx.Client(timeout=self._timeout) as client:
            resp = client.post(
                f"{PLUGGY_BASE_URL}/connect_token",
                json=payload,
                headers={"X-API-KEY": api_key, "accept": "application/json", "content-type": "application/json"},
            )
        if resp.status_code != 200:
            raise ErroIntegracaoPluggy(f"Falha ao criar connect_token: {resp.status_code} {resp.text}")
        return resp.json()["accessToken"]

    def obter_contas(self, item_id: str) -> list[dict]:
        """Retorna as contas (inclui cartões de crédito) vinculadas a um item
        (uma conexão do usuário com uma instituição financeira)."""
        api_key = self._api_key_valida()
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.get(
                f"{PLUGGY_BASE_URL}/accounts",
                params={"itemId": item_id},
                headers={"X-API-KEY": api_key, "accept": "application/json"},
            )
        if resp.status_code != 200:
            raise ErroIntegracaoPluggy(f"Falha ao buscar contas: {resp.status_code} {resp.text}")
        return resp.json().get("results", [])

    def obter_transacoes(self, account_id: str, pagina: int = 1) -> list[dict]:
        api_key = self._api_key_valida()
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.get(
                f"{PLUGGY_BASE_URL}/transactions",
                params={"accountId": account_id, "page": pagina},
                headers={"X-API-KEY": api_key, "accept": "application/json"},
            )
        if resp.status_code != 200:
            raise ErroIntegracaoPluggy(f"Falha ao buscar transações: {resp.status_code} {resp.text}")
        return resp.json().get("results", [])
