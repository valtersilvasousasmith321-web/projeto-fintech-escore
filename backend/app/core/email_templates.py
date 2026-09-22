"""
app/core/email_templates.py

Montagem do conteúdo dos e-mails do sistema. Lógica pura — não faz
nenhuma chamada de rede, só monta texto. Testável sem depender do
SendGrid estar configurado.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EmailMontado:
    assunto: str
    corpo_texto: str
    corpo_html: str


def montar_email_reset_senha(token_bruto: str, url_base_frontend: str, validade_minutos: int = 30) -> EmailMontado:
    """
    Monta o e-mail de recuperação de senha. `url_base_frontend` é a URL
    do seu frontend publicado (ex: https://seuapp.onrender.com) — sem
    barra no final.
    """
    if not token_bruto:
        raise ValueError("token_bruto não pode ser vazio")
    if not url_base_frontend:
        raise ValueError("url_base_frontend não pode ser vazio")

    url_base_frontend = url_base_frontend.rstrip("/")
    link = f"{url_base_frontend}/index.html?token_reset={token_bruto}"

    assunto = "Redefinição de senha — Nome Limpo"

    corpo_texto = (
        "Recebemos um pedido para redefinir sua senha.\n\n"
        f"Clique no link abaixo (válido por {validade_minutos} minutos):\n{link}\n\n"
        "Se você não pediu isso, pode ignorar este e-mail — sua senha continua a mesma."
    )

    corpo_html = (
        f"<p>Recebemos um pedido para redefinir sua senha.</p>"
        f"<p><a href=\"{link}\">Clique aqui para redefinir sua senha</a> "
        f"(válido por {validade_minutos} minutos).</p>"
        f"<p>Se você não pediu isso, pode ignorar este e-mail — sua senha continua a mesma.</p>"
    )

    return EmailMontado(assunto=assunto, corpo_texto=corpo_texto, corpo_html=corpo_html)


def montar_email_boas_vindas(nome_ou_email: str) -> EmailMontado:
    assunto = "Bem-vindo ao Nome Limpo"
    corpo_texto = (
        f"Olá, {nome_ou_email}!\n\n"
        "Sua conta foi criada. A gente resolve seu nome sujo e aumenta seu score — "
        "e te mostra exatamente como, passo a passo, até o fim."
    )
    corpo_html = (
        f"<p>Olá, {nome_ou_email}!</p>"
        "<p>Sua conta foi criada. A gente resolve seu nome sujo e aumenta seu score — "
        "e te mostra exatamente como, passo a passo, até o fim.</p>"
    )
    return EmailMontado(assunto=assunto, corpo_texto=corpo_texto, corpo_html=corpo_html)
