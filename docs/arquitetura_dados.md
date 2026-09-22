# Arquitetura de Dados

## Visão geral do fluxo

```
┌─────────────┐      consentimento LGPD       ┌──────────────────┐
│   Usuário    │ ─────────────────────────────▶│  App (PF/PJ)      │
└─────────────┘                                └────────┬──────────┘
                                                          │
                    ┌─────────────────────────────────────┼─────────────────────────────┐
                    ▼                                     ▼                             ▼
          ┌───────────────────┐                ┌───────────────────┐        ┌───────────────────┐
          │  Open Finance      │                │  Birôs de Crédito  │        │  Bases Públicas    │
          │  (Pluggy/Belvo)    │                │  (Serasa/Quod/BV)  │        │  (Receita/PGFN)     │
          └─────────┬──────────┘                └─────────┬──────────┘        └─────────┬──────────┘
                    │                                     │                             │
                    ▼                                     ▼                             ▼
           extratos, cartões,                    score atual, histórico          CNPJ ativo, débitos
           saldo, comportamento                  de pagamento, restrições        federais, situação
           de pagamento                          ativas                         cadastral (Receitaws/
                                                                                  gov.br quando disponível)
                    │                                     │                             │
                    └─────────────────────┬───────────────┴──────────────┬──────────────┘
                                            ▼                              ▼
                                  ┌───────────────────────────────────────────┐
                                  │   Motor de Normalização e Auditoria         │
                                  │   (consolida, deduplica, calcula impacto)   │
                                  └───────────────────────┬─────────────────────┘
                                                            ▼
                                                  ┌───────────────────┐
                                                  │  Score + Plano de   │
                                                  │  Ação (dashboard)   │
                                                  └───────────────────┘
```

## Fontes de dado e o que cada uma fornece de fato

### 1. Open Finance — Pluggy / Belvo
São **agregadores certificados pelo Banco Central** dentro do ecossistema Open Finance Brasil. O produto se conecta via API REST/OAuth2, o usuário autentica diretamente na instituição financeira dele (nunca compartilha senha com o app), e o agregador retorna:

- Extratos bancários (categorizados)
- Faturas e limites de cartão de crédito
- Dívidas ativas registradas em outras instituições (empréstimos, financiamentos)
- Comportamento de pagamento (pontualidade, uso de limite)

**Uso real no produto**: esses dados alimentam o *modelo de simulação de impacto* (ex: "se você reduzir uso de limite de cartão de 90% para 30%, isso historicamente correlaciona com +X pontos em Y dias"). **Não são usados para aprovar ou negar crédito** — isso é decisão do parceiro financeiro.

### 2. Birôs de crédito — Serasa Experian, Quod, Boa Vista SCPC
Acesso via API B2B (contrato comercial direto, sujeito a aprovação de compliance de cada birô). Fornecem:

- Score atual do CPF/CNPJ
- Histórico de score (série temporal, quando disponível no plano contratado)
- Restrições ativas (protesto, ações judiciais, dívidas vencidas)
- Consultas recentes ao CPF (quem consultou e quando)

**Ponto crítico de compliance**: toda consulta ao CPF deve ser **soft inquiry** (não gera registro de "nova consulta de crédito" que penalizaria o usuário) — isso é um parâmetro contratual específico que precisa ser negociado e confirmado por escrito com cada birô antes de qualquer integração em produção. Consultas mal configuradas podem *piorar* o score do usuário.

### 3. Bases públicas — Receita Federal / PGFN
- **Receita Federal**: situação cadastral de CNPJ (ativo, suspenso, baixado) via consulta pública (ReceitaWS ou API oficial quando disponível)
- **PGFN**: certidões de débitos federais — usadas apenas para PJ, para informar ao usuário se há pendências que impactam crédito empresarial

Essas consultas são públicas e não exigem parceria comercial, mas têm rate limit e exigem cache agressivo (Redis, TTL de 24h) para não sobrecarregar os serviços públicos.

## Modelo de dados consolidado (simplificado)

```
Usuario (PF/PJ)
 ├── id, documento (CPF/CNPJ), tipo
 ├── consentimentos[] (open_finance, biro, base_publica) com timestamp e escopo
 ├── score_historico[] (data, valor, fonte_biro)
 ├── fatores_score[] (categoria, peso, valor_atual, impacto_estimado)
 └── plano_acao[] (acao, impacto_estimado_pontos, prazo_estimado_dias, status)
```

## Segurança e LGPD

- Todo dado de Open Finance e biro é criptografado em repouso (AES-256) e em trânsito (TLS 1.3)
- Consentimento é granular por fonte de dado, revogável a qualquer momento pelo usuário, com exclusão em até 15 dias úteis conforme LGPD
- Nenhum dado é usado para decisão automatizada de crédito dentro da plataforma — isso mitiga risco regulatório sob o art. 20 da LGPD (decisões automatizadas)
