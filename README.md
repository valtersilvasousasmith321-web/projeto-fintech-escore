# Score Transparente & Plano de Evolução de Crédito

> ### "A gente resolve seu nome sujo e aumenta seu score — e te mostra exatamente como, passo a passo, até o fim."
> Ver `LEMA.md` para o detalhamento de cada parte dessa frase e onde ela já está implementada no código.

## O que é

Plataforma (PF e PJ) que mostra ao usuário, de forma **transparente e auditável**, os fatores que compõem seu score de crédito, e gera um **plano de ação personalizado** com impacto estimado e prazo estimado para cada ação — sem prometer aprovação de crédito, que depende sempre da política de risco de cada instituição financeira.

Princípio de produto (não negociável): **nunca prometemos aprovação ou "garantia" de crédito**. Prometemos clareza sobre o score, estimativas de impacto baseadas em modelo estatístico, e conexão com ofertas de crédito **pré-qualificadas** (o usuário já atende aos critérios mínimos publicados pelo parceiro, mas a decisão final é sempre do banco/fintech parceiro).

## Por que isso é diferente de "score garantido"

| Promessa de mercado (vaporware) | O que este produto faz de verdade |
|---|---|
| "Token de garantia" que força aprovação | Motor de regras que verifica se o usuário bate os critérios *publicados* de cada parceiro (renda mínima, score mínimo, sem restrição ativa) |
| "100% aprovado" | "Você atende a X de Y critérios desta oferta. Aprovação final é do banco." |
| Integração mTLS "assinada" com bancos para forçar decisão | Open Finance (Pluggy/Belvo) para *leitura* de dados, com consentimento do usuário, usado para simular impacto no score — nunca para decidir crédito |

## Stack tecnológica

- **Backend**: Python 3.11+ (FastAPI), PostgreSQL, Redis (cache de score)
- **Open Finance**: Pluggy ou Belvo (agregadores certificados no Brasil) — leitura de extratos, cartões, dívidas ativas, mediante consentimento LGPD
- **Dados de score**: consulta a birôs via API (Serasa, Quod, Boa Vista) — sempre client-side "consulta suave" (soft inquiry), nunca hard inquiry sem ação explícita do usuário
- **Frontend**: React + TypeScript (não incluído neste pacote de docs — foco é backend/lógica)
- **Infra**: Docker, deploy sugerido em Railway/AWS ECS, segredo gerenciado via Vault/AWS Secrets Manager

## Como rodar (ambiente de simulação local)

```bash
git clone <repo>
cd projeto-fintech-score-garantido/src
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install --upgrade pip
python mock_analise_score.py
```

Não há dependências externas no mock — ele roda com Python puro para fins de demonstração da lógica de auditoria e cálculo de impacto.

## Estrutura do repositório

```
projeto-fintech-score-garantido/
├── README.md
├── docs/
│   ├── arquitetura_dados.md
│   ├── especificacao_algoritmo.md
│   ├── esteira_credito_pre_qualificado.md
│   ├── modelo_negocios_monetizacao.md
│   ├── guia_pratico_aumento_score.md
│   ├── solucao_completa_nome_limpo_score.md
│   ├── relatorio_detalhado_exemplo.md
│   ├── listagem_boletos_pendencias.md
│   └── estrategia_nacional_diferenciais.md
├── manual/
│   └── manual_usuario_operacao.md
├── src/
│   ├── mock_analise_score.py
│   └── mockup_telas_terminal.txt
└── backend/                          # API de produção (FastAPI) — ver backend/README.md
    ├── app/
    │   ├── core/                     # lógica de negócio pura, sem dependências
    │   ├── main.py, auth.py, schemas.py, database.py
    ├── tests/                        # 72 testes de lógica + testes de API
    ├── requirements.txt
    ├── SECURITY.md                   # postura de segurança e o que falta p/ produção
    └── README.md
```

## Guias

- **`frontend/teste_funcionamento.html`** — painel de teste automatizado: roda backend, cadastro, login, diagnóstico e negociação em sequência, mostrando sucesso/erro de cada passo — use depois de qualquer deploy pra confirmar rapidinho que nada quebrou
- **`CRITERIO_DE_ACEITE.md`** — checklist do que um profissional contratado precisa entregar de verdade, com como você mesmo confere cada item, sem depender só da palavra dele
- **`FICHA_TECNICA.md`** — handoff técnico pra um desenvolvedor: stack, arquitetura, schema do banco, endpoints, variáveis de ambiente, lacunas conhecidas (sem hand-holding, assume quem já programa)
- **`ENTENDA_O_SISTEMA.md`** — comece por aqui se quiser entender o que o sistema faz e como as peças se conectam, antes de ir pra produção
- **`SUAS_PENDENCIAS.md`** — checklist direto do que é sua parte (não código): testar pagamento, contrato com birô, pentest, em ordem de prioridade
- **`GUIA_COMPLETO_VSCODE_AO_AR.md`** — passo a passo técnico, numerado, do VS Code até o site no ar
- **`GUIA_APIS_E_SERVICOS_EXTERNOS.md`** — mapa completo de tudo que existe fora do código: quais contas criar agora (grátis) e quais exigem CNPJ/contrato comercial (birôs de crédito, Pluggy em produção)
- `INSTALACAO_WINDOWS.md` — passo a passo pra instalar e rodar tudo no Windows
- `DEPLOY_PUBLICO.md` — passo a passo pra publicar na internet: backend no Render, frontend no Render ou Vercel, com apps instaláveis no celular (PWA)
- `STATUS_DO_PROJETO.md` — snapshot honesto do que está testado, o que falta testar, e o que não existe ainda
- `frontend/index.html` — app público funcional (login, cadastro, esqueci senha, diagnóstico real via API)
- `frontend/admin.html` — painel administrativo (acesso restrito), também instalável como app separado
- `frontend/suporte.html` — central de ajuda com FAQ e chat de suporte (motor próprio, sem IA externa)
- `backend/SECURITY.md` — o que já está seguro e o que falta antes de operar em produção real

## Backend — como rodar e testar

```bash
cd backend

# 1. Validar a lógica de negócio (não precisa instalar nada)
python3 -m unittest discover -s tests -v

# 2. Instalar dependências e subir a API
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
export JWT_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))")
uvicorn app.main:app --reload --port 8000
# Documentação interativa: http://localhost:8000/docs

# 3. Rodar testes de API completos
pytest tests/test_api.py -v
```

Ver `backend/SECURITY.md` para o que já está implementado (hash de senha,
JWT, validação de CPF/CNPJ, rate limiting, proteção contra SQL injection,
isolamento de dados entre usuários) e o que ainda falta antes de operar
com dados reais em produção.

## Disclaimer de produto (deve aparecer em toda comunicação com o usuário final)

> "Os valores de impacto no score são estimativas estatísticas baseadas em modelos históricos e podem não se refletir exatamente no score calculado pelos birôs de crédito. A aprovação de qualquer produto de crédito é decisão exclusiva da instituição financeira ofertante."
