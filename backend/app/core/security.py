"""
app/core/security.py

Funções de segurança usadas pela API: hashing de senha, geração/validação
de token de sessão, validação de CPF/CNPJ, e mascaramento de dados
sensíveis em logs.

Implementado com biblioteca padrão do Python (hashlib, hmac, secrets)
para não depender de pacotes externos nesta camada crítica — reduz
superfície de ataque via supply chain e facilita auditoria de segurança.

Em produção, a camada de API (app/main.py) usa isso combinado com JWT
(via python-jose, ver requirements.txt) para sessões HTTP.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets


# ---------------------------------------------------------------------------
# Hashing de senha (PBKDF2-HMAC-SHA256, 600.000 iterações — recomendação
# OWASP 2023+ para PBKDF2-SHA256)
# ---------------------------------------------------------------------------

PBKDF2_ITERACOES = 600_000
TAMANHO_SALT_BYTES = 16


def gerar_hash_senha(senha: str) -> str:
    """Retorna string no formato 'salt_hex$hash_hex' pronta para armazenar."""
    if not senha or len(senha) < 8:
        raise ValueError("senha deve ter no mínimo 8 caracteres")
    salt = secrets.token_bytes(TAMANHO_SALT_BYTES)
    hash_bytes = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt, PBKDF2_ITERACOES)
    return f"{salt.hex()}${hash_bytes.hex()}"


def verificar_senha(senha: str, hash_armazenado: str) -> bool:
    """Comparação em tempo constante (hmac.compare_digest) para evitar timing attack."""
    try:
        salt_hex, hash_hex = hash_armazenado.split("$")
    except ValueError:
        return False
    salt = bytes.fromhex(salt_hex)
    hash_calculado = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt, PBKDF2_ITERACOES)
    return hmac.compare_digest(hash_calculado.hex(), hash_hex)


# ---------------------------------------------------------------------------
# Validação de CPF/CNPJ (algoritmo de dígito verificador oficial)
# ---------------------------------------------------------------------------

def _apenas_digitos(valor: str) -> str:
    return re.sub(r"\D", "", valor)


def validar_cpf(cpf: str) -> bool:
    cpf = _apenas_digitos(cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False

    def digito_verificador(cpf_parcial: str) -> int:
        peso_inicial = len(cpf_parcial) + 1
        soma = sum(int(d) * (peso_inicial - i) for i, d in enumerate(cpf_parcial))
        resto = soma % 11
        return 0 if resto < 2 else 11 - resto

    d1 = digito_verificador(cpf[:9])
    d2 = digito_verificador(cpf[:9] + str(d1))
    return cpf[-2:] == f"{d1}{d2}"


def validar_cnpj(cnpj: str) -> bool:
    cnpj = _apenas_digitos(cnpj)
    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
        return False

    def digito_verificador(cnpj_parcial: str, pesos: list[int]) -> int:
        soma = sum(int(d) * p for d, p in zip(cnpj_parcial, pesos))
        resto = soma % 11
        return 0 if resto < 2 else 11 - resto

    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    d1 = digito_verificador(cnpj[:12], pesos1)
    d2 = digito_verificador(cnpj[:12] + str(d1), pesos2)
    return cnpj[-2:] == f"{d1}{d2}"


# ---------------------------------------------------------------------------
# Mascaramento de dados sensíveis (para logs — nunca logar CPF em texto puro)
# ---------------------------------------------------------------------------

def mascarar_cpf(cpf: str) -> str:
    cpf = _apenas_digitos(cpf)
    if len(cpf) != 11:
        return "***invalido***"
    return f"{cpf[:3]}.***.***-{cpf[-2:]}"


def mascarar_cnpj(cnpj: str) -> str:
    cnpj = _apenas_digitos(cnpj)
    if len(cnpj) != 14:
        return "***invalido***"
    return f"{cnpj[:2]}.***.***/****-{cnpj[-2:]}"


# ---------------------------------------------------------------------------
# Geração de token de sessão (para uso em conjunto com JWT na API)
# ---------------------------------------------------------------------------

def gerar_token_seguro(tamanho_bytes: int = 32) -> str:
    """Token aleatório criptograficamente seguro (ex: para refresh token,
    token de convite, ou id de sessão opaco)."""
    return secrets.token_urlsafe(tamanho_bytes)


def hash_deterministico_documento(documento: str) -> str:
    """
    Hash SHA-256 determinístico (SEM salt) do documento — usado só como
    CHAVE DE BUSCA em cache (ex: 'já consultei esse CPF no Serasa nos
    últimos 30 dias?'), nunca para autenticação.

    Diferente de gerar_hash_senha (que usa salt aleatório de propósito,
    pra que o mesmo CPF gere hashes diferentes e não seja rastreável
    entre tabelas): aqui precisamos do oposto — o mesmo CPF tem que
    sempre gerar o mesmo hash, senão o cache nunca acha uma entrada
    repetida. Isso é aceitável para uma chave de cache (não é segredo
    que precisa resistir a força bruta — CPF já tem baixa entropia,
    11 dígitos, então nem hash com salt tornaria isso resistente a
    quem já tem a lista de CPFs candidata).
    """
    apenas_digitos = "".join(c for c in documento if c.isdigit())
    return hashlib.sha256(apenas_digitos.encode("utf-8")).hexdigest()
