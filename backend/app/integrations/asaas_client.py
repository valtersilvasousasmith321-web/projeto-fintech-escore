"""
app/integrations/asaas_client.py

Cliente de integração com a API do Asaas (gateway de pagamento —
https://docs.asaas.com). Faz chamadas HTTP reais.

Confirmado na documentação oficial antes de escrever este arquivo:
- Base URL produção: https://api.asaas.com/v3
- Base URL sandbox:  https://sandbox.asaas.com/api/v3
- Autenticação: header "access_token" com sua API Key (não é Bearer/JWT)
- POST /customers    → cria cliente, retorna id tipo "cus_..."
- POST /payments     → cria cobrança única (BOLETO/PIX/CREDIT_CARD)
- POST /subscriptions → cria cobrança recorrente (assinatura)

IMPORTANTE: este cliente faz chamadas HTTP reais e não pôde ser testado
neste ambiente de geração (sandbox sem acesso à internet). O que FOI
testado e roda sem rede é a lógica de decisão em app/core/billing.py
(13 testes).
"""

from __future__ import annotations

import os

import httpx


class ErroIntegracaoAsaas(Exception):
    pass


class AsaasClient:
    def __init__(self, api_key: str | None = None, sandbox: bool | None = None, timeout: float = 15.0):
        self.api_key = api_key or os.environ.get("ASAAS_API_KEY")
        if not self.api_key:
            raise ErroIntegracaoAsaas(
                "ASAAS_API_KEY não configurada. Gere uma em Integrações > Chaves de API "
                "no painel do Asaas (sandbox.asaas.com para testar, api.asaas.com em produção)."
            )

        if sandbox is None:
            sandbox = os.environ.get("ASAAS_SANDBOX", "true").lower() == "true"

        self.base_url = "https://sandbox.asaas.com/api/v3" if sandbox else "https://api.asaas.com/v3"
        self._timeout = timeout

    def _headers(self) -> dict:
        return {"access_token": self.api_key, "content-type": "application/json"}

    def criar_cliente(self, nome: str, cpf_cnpj: str, email: str) -> dict:
        """Cria (ou duplica — a Asaas permite CPF/CNPJ duplicado, então
        quem chama deve guardar o id retornado pra não recriar depois)."""
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.post(
                f"{self.base_url}/customers",
                json={"name": nome, "cpfCnpj": cpf_cnpj, "email": email},
                headers=self._headers(),
            )
        if resp.status_code not in (200, 201):
            raise ErroIntegracaoAsaas(f"Falha ao criar cliente no Asaas: {resp.status_code} {resp.text}")
        return resp.json()

    def criar_cobranca_unica(self, customer_id: str, valor: float, vencimento_iso: str, tipo: str = "PIX") -> dict:
        """tipo: 'PIX', 'BOLETO' ou 'CREDIT_CARD'. Usado pra cobrar a
        comissão de negociação depois que a baixa é confirmada."""
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.post(
                f"{self.base_url}/payments",
                json={
                    "customer": customer_id, "billingType": tipo,
                    "value": round(valor, 2), "dueDate": vencimento_iso,
                },
                headers=self._headers(),
            )
        if resp.status_code not in (200, 201):
            raise ErroIntegracaoAsaas(f"Falha ao criar cobrança no Asaas: {resp.status_code} {resp.text}")
        return resp.json()

    def criar_assinatura(self, customer_id: str, valor: float, proximo_vencimento_iso: str, tipo: str = "CREDIT_CARD") -> dict:
        """Cobrança recorrente mensal — usado pros planos Plus/Premium."""
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.post(
                f"{self.base_url}/subscriptions",
                json={
                    "customer": customer_id, "billingType": tipo,
                    "value": round(valor, 2), "nextDueDate": proximo_vencimento_iso,
                    "cycle": "MONTHLY",
                },
                headers=self._headers(),
            )
        if resp.status_code not in (200, 201):
            raise ErroIntegracaoAsaas(f"Falha ao criar assinatura no Asaas: {resp.status_code} {resp.text}")
        return resp.json()
