# Backend — Score Transparente & Plano de Evolução de Crédito

API de produção (FastAPI) que implementa os três pilares do produto:
diagnóstico de score, negociação de dívidas e marketplace de crédito
pré-qualificado.

## Estrutura

```
backend/
├── app/
│   ├── core/                  # Lógica de negócio pura (SEM dependências externas)
│   │   ├── score_engine.py    # Cálculo de score e plano de ação
│   │   ├── negociacao.py      # Máquina de estados de negociação de dívida
│   │   ├── marketplace.py     # Motor de elegibilidade (nunca "aprova")
│   │   └── security.py        # Hash de senha, validação de CPF/CNPJ, tokens
│   ├── integrations/
│   │   ├── pluggy_client.py   # Cliente HTTP real da API Pluggy (Open Finance)
│   │   └── pluggy_adapter.py  # Converte dados Pluggy -> DadosOpenFinance (✅ testado, sem rede)
│   ├── main.py                 # API FastAPI (endpoints)
│   ├── auth.py                 # Autenticação JWT
│   ├── schemas.py              # Contratos Pydantic de entrada/saída
│   └── database.py             # Persistência SQLite (stdlib)
├── tests/
│   ├── test_score_engine.py       # ✅ roda sem instalar nada (stdlib puro)
│   ├── test_negociacao.py         # ✅ roda sem instalar nada
│   ├── test_marketplace.py        # ✅ roda sem instalar nada
│   ├── test_security.py           # ✅ roda sem instalar nada
│   ├── test_pluggy_adapter.py     # ✅ roda sem instalar nada (não faz chamada de rede)
│   └── test_api.py                # requer pip install (fastapi + httpx)
├── requirements.txt
├── SECURITY.md                 # postura de segurança e o que falta para produção real
└── README.md
```

## Integração real com Open Finance (Pluggy)

`app/integrations/pluggy_client.py` implementa o fluxo real de autenticação
da Pluggy (confirmado na documentação oficial em docs.pluggy.ai):
`CLIENT_ID`/`CLIENT_SECRET` → API Key (2h) → Connect Token (30 min, para o
frontend) → busca de contas/transações.

Para testar com dados reais (sandbox gratuito):

```bash
# 1. Crie uma conta gratuita em https://dashboard.pluggy.ai e pegue suas
#    credenciais de sandbox (CLIENT_ID e CLIENT_SECRET)

export PLUGGY_CLIENT_ID="seu_client_id_sandbox"
export PLUGGY_CLIENT_SECRET="seu_client_secret_sandbox"

python3 -c "
from app.integrations.pluggy_client import PluggyClient
client = PluggyClient()
token = client.criar_connect_token(client_user_id='usuario_teste_1')
print('Connect token gerado:', token)
"
```

Esse `token` é o que o widget Pluggy Connect (frontend) usa para o usuário
conectar o banco dele de verdade no sandbox. Depois de conectado, a Pluggy
gera um `item_id`, que o backend usa para buscar contas de crédito:

```python
contas = client.obter_contas(item_id="...")

from app.integrations.pluggy_adapter import montar_dados_open_finance
dados_of = montar_dados_open_finance(contas)
```

`pluggy_adapter.py` é a peça mais importante tecnicamente: ele é **lógica
pura, sem chamada de rede**, então roda e foi testado (12 testes) neste
ambiente mesmo sem internet — usando payloads no formato real documentado
pela Pluggy. Já o `pluggy_client.py` faz chamadas HTTP de verdade e precisa
ser testado com suas próprias credenciais de sandbox no seu ambiente.

## Por que isso está dividido assim

A lógica de negócio (`app/core/`) foi escrita **sem nenhuma dependência externa**,
de propósito — só Python padrão (`dataclasses`, `enum`, `hashlib`, `sqlite3`).
Isso significa:

1. Você pode rodar e validar as regras de negócio (cálculo de score, máquina de
   estados de negociação, elegibilidade de marketplace, segurança) **sem instalar
   absolutamente nada** — já testado e rodando com 72 testes passando.
2. A camada de API (FastAPI) é só uma "casca" fina por cima dessa lógica — troca
   HTTP por chamada direta de função. Isso facilita testar, auditar e até trocar
   o framework de API no futuro sem tocar na regra de negócio.

## Como rodar no VS Code

### 1. Validar a lógica de negócio (sem instalar nada)

```bash
cd backend
python3 -m unittest discover -s tests -v
```

Isso já roda `test_score_engine.py`, `test_negociacao.py`, `test_marketplace.py`
e `test_security.py` — 72 testes, cobrindo as regras mais importantes do
produto (inclusive a regra crítica: comissão de negociação só pode ser
calculada quando o status é `BAIXA_CONFIRMADA`).

### 2. Instalar dependências e subir a API completa

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

export JWT_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))")
# Windows (PowerShell): $env:JWT_SECRET_KEY = python -c "import secrets; print(secrets.token_urlsafe(64))"

uvicorn app.main:app --reload --port 8000
```

Depois de subir, acesse `http://localhost:8000/docs` — o FastAPI gera
documentação interativa automática (Swagger UI) de todos os endpoints,
onde dá pra testar cada rota direto no navegador.

### 3. Rodar os testes de API (integração completa)

```bash
pytest tests/test_api.py -v
```

Esses testes cobrem: cadastro/login, rejeição de CPF inválido, proteção
de rota por token, isolamento de dados entre usuários (usuário A não
acessa negociação de usuário B), e o fluxo completo de negociação até
o cálculo de comissão.

## Endpoints principais

| Método | Rota | Descrição |
|---|---|---|
| POST | `/auth/cadastro` | Cria usuário (valida CPF/CNPJ, hash de senha) |
| POST | `/auth/login` | Retorna access + refresh token |
| POST | `/score/diagnostico` | Roda o motor de score e devolve plano de ação (rota protegida) |
| POST | `/negociacao` | Cria uma negociação de dívida (rota protegida) |
| POST | `/negociacao/{id}/proposta` | Registra proposta de desconto recebida do credor |
| POST | `/negociacao/{id}/transicao` | Avança o status da negociação (só calcula comissão em `BAIXA_CONFIRMADA`) |
| POST | `/marketplace/ofertas` | Retorna ofertas rankeadas por % de aderência (nunca "aprovado") |
| GET | `/health` | Health check |

## Segurança

Ver `SECURITY.md` para o detalhamento completo do que está implementado
e — igualmente importante — o que **ainda falta** antes de operar com
dados reais de usuários em produção (rate limiting distribuído,
persistência de negociação em banco real, integração com cofre de
segredos, etc.).
