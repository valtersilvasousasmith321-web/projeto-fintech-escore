"""
app/schemas.py

Modelos Pydantic (contratos de entrada/saída da API). Requer pydantic
instalado (ver requirements.txt) — não roda com stdlib puro, ao contrário
dos módulos em app/core/.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, EmailStr

from app.core.security import validar_cpf, validar_cnpj


class DividaEntrada(BaseModel):
    credor: str = Field(..., min_length=1, max_length=200, pattern=r"^[^<>]*$")
    valor: float = Field(..., gt=0)
    dias_atraso: int = Field(..., ge=0)
    origem: str
    negativado: bool
    linha_digitavel: str | None = None


class DiagnosticoRequest(BaseModel):
    documento: str = Field(..., description="CPF (11 dígitos) ou CNPJ (14 dígitos)")
    utilizacao_credito_atual: float = Field(..., ge=0.0, le=1.0)
    utilizacao_credito_meta: float = Field(..., ge=0.0, le=1.0)
    meses_historico_disponivel: int = Field(..., ge=0)
    pontualidade_pagamentos_24m: float = Field(..., ge=0.0, le=1.0)
    score_atual: int = Field(..., ge=0, le=1000)
    tempo_relacionamento_credito_meses: int = Field(..., ge=0)
    quantidade_tipos_credito_ativos: int = Field(..., ge=0)
    dividas_ativas: list[DividaEntrada] = Field(default_factory=list)
    consultas_cpf_ultimos_30_dias: int = Field(..., ge=0)

    @field_validator("documento")
    @classmethod
    def validar_documento(cls, v: str) -> str:
        apenas_digitos = "".join(c for c in v if c.isdigit())
        if len(apenas_digitos) == 11:
            if not validar_cpf(v):
                raise ValueError("CPF inválido (dígito verificador não confere)")
        elif len(apenas_digitos) == 14:
            if not validar_cnpj(v):
                raise ValueError("CNPJ inválido (dígito verificador não confere)")
        else:
            raise ValueError("documento deve ter 11 dígitos (CPF) ou 14 dígitos (CNPJ)")
        return v


class RegistrarPropostaRequest(BaseModel):
    valor_com_desconto: float = Field(..., gt=0)


class TransicaoRequest(BaseModel):
    novo_status: str
    detalhe: str = ""


class NovaNegociacaoRequest(BaseModel):
    usuario_id: str = Field(..., min_length=1)
    credor: str = Field(..., min_length=1, max_length=200, pattern=r"^[^<>]*$")
    valor_original: float = Field(..., gt=0)


class CriteriosParceiroEntrada(BaseModel):
    parceiro_id: str
    produto: str
    score_minimo: int = Field(..., ge=0, le=1000)
    sem_restricao_ativa: bool
    renda_minima_declarada: float = Field(..., ge=0)
    tempo_minimo_relacionamento_bancario_meses: int = Field(..., ge=0)


class AvaliarMarketplaceRequest(BaseModel):
    score_atual: int = Field(..., ge=0, le=1000)
    tem_restricao_ativa: bool
    renda_declarada: float = Field(..., ge=0)
    tempo_relacionamento_bancario_meses: int = Field(..., ge=0)
    ofertas_disponiveis: list[CriteriosParceiroEntrada]


class EsqueciSenhaRequest(BaseModel):
    email: EmailStr


class RedefinirSenhaRequest(BaseModel):
    token: str = Field(..., min_length=10)
    nova_senha: str = Field(..., min_length=8, max_length=128)


class MensagemChat(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1, max_length=2000)


class SuporteChatRequest(BaseModel):
    mensagens: list[MensagemChat] = Field(..., min_length=1, max_length=20)


class CadastroRequest(BaseModel):
    documento: str
    email: EmailStr
    senha: str = Field(..., min_length=8, max_length=128)

    @field_validator("documento")
    @classmethod
    def validar_documento(cls, v: str) -> str:
        apenas_digitos = "".join(c for c in v if c.isdigit())
        if len(apenas_digitos) == 11 and validar_cpf(v):
            return v
        if len(apenas_digitos) == 14 and validar_cnpj(v):
            return v
        raise ValueError("documento inválido")
        return v


class DiagnosticoSerasaRequest(BaseModel):
    """
    Diferente de DiagnosticoRequest (onde o cliente manda score e
    dívidas manualmente), aqui só mandamos o documento — score e
    dívidas vêm consultados de verdade no birô (Serasa CredNet via
    SOA Web Services). Os campos de Open Finance continuam vindo de
    fora (Pluggy ou input manual), porque o CredNet não retorna
    utilização de limite de cartão.
    """
    documento: str
    utilizacao_credito_atual: float = Field(..., ge=0.0, le=1.0)
    utilizacao_credito_meta: float = Field(default=0.30, ge=0.0, le=1.0)
    meses_historico_disponivel: int = Field(default=0, ge=0)
    pontualidade_pagamentos_24m: float = Field(default=1.0, ge=0.0, le=1.0)

    @field_validator("documento")
    @classmethod
    def validar_documento(cls, v: str) -> str:
        apenas_digitos = "".join(c for c in v if c.isdigit())
        if len(apenas_digitos) == 11 and validar_cpf(v):
            return v
        if len(apenas_digitos) == 14 and validar_cnpj(v):
            return v
        raise ValueError("documento inválido")


class CriarAssinaturaRequest(BaseModel):
    plano: str = Field(..., pattern="^(plus|premium)$")
    tipo_pagamento: str = Field(default="CREDIT_CARD", pattern="^(CREDIT_CARD|BOLETO|PIX)$")
    documento: str = Field(..., description="CPF ou CNPJ — repassado ao gateway de pagamento, nunca armazenado em texto puro")

    @field_validator("documento")
    @classmethod
    def validar_documento(cls, v: str) -> str:
        apenas_digitos = "".join(c for c in v if c.isdigit())
        if len(apenas_digitos) == 11 and validar_cpf(v):
            return v
        if len(apenas_digitos) == 14 and validar_cnpj(v):
            return v
        raise ValueError("documento inválido")


class CobrarComissaoRequest(BaseModel):
    documento: str = Field(..., description="CPF ou CNPJ — repassado ao gateway de pagamento, nunca armazenado em texto puro")

    @field_validator("documento")
    @classmethod
    def validar_documento(cls, v: str) -> str:
        apenas_digitos = "".join(c for c in v if c.isdigit())
        if len(apenas_digitos) == 11 and validar_cpf(v):
            return v
        if len(apenas_digitos) == 14 and validar_cnpj(v):
            return v
        raise ValueError("documento inválido")


class ComprarConsultaAvulsaRequest(BaseModel):
    documento: str = Field(..., description="CPF ou CNPJ — repassado ao gateway de pagamento, nunca armazenado em texto puro")
    tipo_pagamento: str = Field(default="PIX", pattern="^(CREDIT_CARD|BOLETO|PIX)$")

    @field_validator("documento")
    @classmethod
    def validar_documento(cls, v: str) -> str:
        apenas_digitos = "".join(c for c in v if c.isdigit())
        if len(apenas_digitos) == 11 and validar_cpf(v):
            return v
        if len(apenas_digitos) == 14 and validar_cnpj(v):
            return v
        raise ValueError("documento inválido")


class ConsultaManualAdminRequest(BaseModel):
    """Usado pelo admin pra consultar o Serasa manualmente, em nome de
    alguém que ligou/mandou mensagem — fluxo tipo 'escritório', sem
    passar pelo cadastro/assinatura pública."""
    documento: str
    observacao: str = Field(default="", max_length=500, description="ex: nome de quem ligou, forma de pagamento combinada")

    @field_validator("documento")
    @classmethod
    def validar_documento(cls, v: str) -> str:
        apenas_digitos = "".join(c for c in v if c.isdigit())
        if len(apenas_digitos) == 11 and validar_cpf(v):
            return v
        if len(apenas_digitos) == 14 and validar_cnpj(v):
            return v
        raise ValueError("documento inválido")
