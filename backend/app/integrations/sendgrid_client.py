"""
app/integrations/sendgrid_client.py

Cliente de integração com a API v3 do SendGrid (envio de e-mail —
https://docs.sendgrid.com). Confirmado antes de escrever:
- Endpoint: POST https://api.sendgrid.com/v3/mail/send
- Autenticação: header Authorization: Bearer <API_KEY>
- Corpo: personalizations (destinatário) + from + subject + content

Faz chamada HTTP real — não pôde ser testada neste ambiente (sandbox
sem internet). O que É testado é a montagem do conteúdo do e-mail
(app/core/email_templates.py), que é lógica pura.
"""

from __future__ import annotations

import os

import httpx

SENDGRID_API_URL = "https://api.sendgrid.com/v3/mail/send"


class ErroIntegracaoSendGrid(Exception):
    pass


class SendGridClient:
    def __init__(self, api_key: str | None = None, remetente: str | None = None, timeout: float = 15.0):
        self.api_key = api_key or os.environ.get("SENDGRID_API_KEY")
        self.remetente = remetente or os.environ.get("SENDGRID_FROM_EMAIL")
        if not self.api_key:
            raise ErroIntegracaoSendGrid(
                "SENDGRID_API_KEY não configurada. Crie uma em Settings > API Keys no painel do SendGrid."
            )
        if not self.remetente:
            raise ErroIntegracaoSendGrid(
                "SENDGRID_FROM_EMAIL não configurada. Precisa ser um e-mail com domínio verificado no SendGrid "
                "(Settings > Sender Authentication) — não pode ser um e-mail genérico não verificado."
            )
        self._timeout = timeout

    def enviar(self, destinatario: str, assunto: str, corpo_texto: str, corpo_html: str | None = None) -> None:
        conteudo = [{"type": "text/plain", "value": corpo_texto}]
        if corpo_html:
            conteudo.append({"type": "text/html", "value": corpo_html})

        payload = {
            "personalizations": [{"to": [{"email": destinatario}]}],
            "from": {"email": self.remetente},
            "subject": assunto,
            "content": conteudo,
        }

        with httpx.Client(timeout=self._timeout) as client:
            resp = client.post(
                SENDGRID_API_URL,
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            )

        # SendGrid responde 202 (aceito) em caso de sucesso — não é 200/201
        if resp.status_code != 202:
            raise ErroIntegracaoSendGrid(f"Falha ao enviar e-mail via SendGrid: {resp.status_code} {resp.text}")
