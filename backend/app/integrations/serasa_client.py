"""
app/integrations/serasa_client.py

Cliente de integração com a API da SOA Web Services (revenda oficial
Serasa Experian — soawebservices.com.br), produto CredNet.

Confirmado direto na conta de homologação do usuário antes de escrever
este arquivo (não é documentação pública — é dado real extraído do
painel da conta):

- Endpoint: POST /api/v2/Serasa/Consultas/CredNet
- Autenticação: NÃO é header, é campo "credenciais": {"email", "senha"}
  dentro do corpo de CADA requisição (diferente de Pluggy/Asaas, que
  usam header)
- Servidor de homologação: https://homologacao.soawebservices.com.br
- Servidor de produção: https://producao.soawebservices.com.br
  (confirmado direto no painel da conta do usuário — a caixa "Server"
  da documentação tinha 3 opções escondidas atrás de um dropdown;
  a terceira, "https://services.soawebservices.com.br", não identificamos
  o propósito e não usamos)

IMPORTANTE: este cliente faz chamada HTTP real e não pôde ser testado
neste ambiente (sandbox sem internet). O que FOI testado é o adaptador
em app/core/serasa_adapter.py (19 testes, usando o JSON real de
homologação extraído da conta do usuário).
"""

from __future__ import annotations

import os

import httpx

SOA_BASE_URL_HOMOLOGACAO = "https://homologacao.soawebservices.com.br"
SOA_BASE_URL_PRODUCAO = "https://producao.soawebservices.com.br"


class ErroIntegracaoSerasa(Exception):
    pass


class SerasaClient:
    def __init__(
        self, email: str | None = None, senha: str | None = None,
        base_url: str | None = None, timeout: float = 20.0,
    ):
        self.email = email or os.environ.get("SOA_EMAIL")
        self.senha = senha or os.environ.get("SOA_SENHA")
        if not self.email or not self.senha:
            raise ErroIntegracaoSerasa(
                "SOA_EMAIL e SOA_SENHA precisam estar configuradas (as mesmas credenciais "
                "de login do painel soawebservices.com.br — a API usa login/senha no corpo "
                "da requisição, não uma chave de API separada)."
            )
        self.base_url = base_url or self._resolver_base_url()
        self._timeout = timeout

    @staticmethod
    def _resolver_base_url() -> str:
        """
        Prioridade: SOA_BASE_URL (se você quiser colar a URL exata) >
        SOA_AMBIENTE=producao|homologacao (mais simples de configurar) >
        homologação como padrão seguro (nunca cobra por acidente).
        """
        url_explicita = os.environ.get("SOA_BASE_URL")
        if url_explicita:
            return url_explicita

        ambiente = os.environ.get("SOA_AMBIENTE", "homologacao").lower()
        if ambiente == "producao":
            return SOA_BASE_URL_PRODUCAO
        return SOA_BASE_URL_HOMOLOGACAO

    def _credenciais(self) -> dict:
        return {"email": self.email, "senha": self.senha}

    def consultar_crednet(self, documento: str, uf: str | None = None) -> dict:
        """
        Consulta o relatório CredNet (score + dívidas negativadas +
        restrições) de um CPF ou CNPJ. `uf` é opcional — a doc mostra
        o campo mas não deixa claro se é obrigatório; enviamos null
        quando não informado, igual o exemplo da doc faz.
        """
        payload = {
            "credenciais": self._credenciais(),
            "documento": documento,
            "uf": uf,
            "adicionais": [1],  # valor do exemplo da doc — confirmar com suporte SOA o que este código representa
        }
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.post(
                f"{self.base_url}/api/v2/Serasa/Consultas/CredNet",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
        if resp.status_code != 200:
            # IMPORTANTE: nunca repassar resp.text bruto na exceção — ela sobe
            # até o usuário final via HTTPException em app/main.py. Se a API
            # da SOA ecoar o corpo da requisição num erro (comum em várias
            # APIs), isso poderia expor SOA_SENHA pro cliente do app. O
            # detalhe completo (mascarado) só vai pro log do servidor.
            print(f"[SerasaClient] erro HTTP {resp.status_code} ao consultar CredNet: {self._mascarar_senha(resp.text)}")
            raise ErroIntegracaoSerasa(f"Falha ao consultar CredNet (status {resp.status_code})")

        corpo = resp.json()
        transacao = corpo.get("transacao") or {}
        if not transacao.get("status"):
            print(f"[SerasaClient] transação sem sucesso: {self._mascarar_senha(str(transacao))}")
            raise ErroIntegracaoSerasa("CredNet retornou transação sem sucesso — ver log do servidor para detalhes")
        return corpo

    def excluir_negativacao(self, unique_id: str, codigo_baixa: int, baixa_descricao: str = "") -> dict:
        """
        Exclui (dá baixa em) uma negativação na Serasa.

        ATENÇÃO — LIMITAÇÃO DE USO REAL: este endpoint exige o `unique_id`
        que foi devolvido quando a negativação foi CRIADA (via
        /api/v2/Serasa/Negativacoes/Inserir). Ou seja, só quem registrou
        a negativação consegue dar baixa nela.

        No modelo atual do produto (negociar dívidas que OUTRO credor já
        negativou), a gente não tem esse unique_id — o credor original
        é quem precisa dar baixa, do lado dele. Este método só faz
        sentido se, no futuro, a empresa se tornar agente autorizado de
        um credor parceiro (aí a própria empresa registraria a dívida
        via inserir_negativacao() e teria o unique_id pra usar aqui).

        `codigo_baixa`: código do motivo da baixa — a doc mostra o
        valor de exemplo `1` mas não lista a tabela de códigos
        possíveis. Confirme com o suporte da SOA antes de usar em
        produção com um valor diferente de 1.
        """
        payload = {
            "credenciais": self._credenciais(),
            "uniqueID": unique_id,
            "codigoBaixa": codigo_baixa,
            "baixaDescricao": baixa_descricao,
        }
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.post(
                f"{self.base_url}/api/v2/Serasa/Negativacoes/Excluir",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
        if resp.status_code != 200:
            print(f"[SerasaClient] erro HTTP {resp.status_code} ao excluir negativação: {self._mascarar_senha(resp.text)}")
            raise ErroIntegracaoSerasa(f"Falha ao excluir negativação (status {resp.status_code})")

        corpo = resp.json()
        transacao = corpo.get("transacao") or {}
        if not transacao.get("status"):
            print(f"[SerasaClient] exclusão sem sucesso: {self._mascarar_senha(str(transacao))}")
            raise ErroIntegracaoSerasa("Exclusão de negativação sem sucesso — ver log do servidor")
        return corpo

    def _mascarar_senha(self, texto: str) -> str:
        """Defesa em profundidade: mesmo em log do SERVIDOR (nunca visto
        pelo cliente do app), nunca imprime a senha em texto puro —
        caso a API da SOA eco a requisição de volta num erro."""
        if not texto:
            return texto
        return texto.replace(self.senha, "***SENHA_MASCARADA***")
