# Estratégia Nacional — Escala e Diferenciais

## Parte 1 — O que muda tecnicamente para atender o Brasil inteiro

### 1.1 Volume e infraestrutura

O Brasil tem ~160 milhões de CPFs com histórico de crédito ativo. Mesmo capturando 1% como usuários ativos, são 1,6 milhão de perfis sendo recalculados periodicamente. Isso muda decisões de arquitetura:

| Componente | Decisão para escala nacional |
|---|---|
| **Consulta a birôs** | Nunca consultar em tempo real a cada abertura de app — usar fila assíncrona (ex: AWS SQS/Kafka) com throttling por contrato com cada birô, e cache (Redis) com TTL de 24-72h |
| **Processamento do motor de score** | Rodar como job em batch/worker (Celery, ou AWS Lambda com fila), não como cálculo síncrono na requisição HTTP — o usuário vê o último resultado calculado, com "atualizando..." se houver refresh em andamento |
| **Banco de dados** | PostgreSQL particionado por região/data, com réplicas de leitura; histórico de score em série temporal pode ir para um banco colunar (TimescaleDB) se o volume de log crescer muito |
| **Multirregião** | Nomeio geográfico não é crítico como em e-commerce, mas a infra deve estar em datacenter no Brasil (ex: AWS sa-east-1 São Paulo) por exigência prática de latência com birôs e Open Finance, e para reduzir fricção regulatória de dados sensíveis |

### 1.2 Parcerias que precisam escalar junto (não é só tecnologia)

- **Contratos com birôs** costumam ter tiers de volume — negociar contrato que preveja crescimento (custo por consulta cai conforme volume sobe), senão o produto quebra financeiramente ao escalar
- **Capacidade de atendimento humano** para a parte de negociação assistida (Pilar 2 do `solucao_completa_nome_limpo_score.md`) precisa crescer com o volume — aqui entra automação: bots de negociação para casos simples/padronizados, humano só para casos complexos
- **Cobertura de credores**: quanto mais regional o credor (loja de bairro, financeira local), menos provável ter API — nesses casos o app precisa lidar com fallback manual (orientação de como negociar, sem automação)

### 1.3 Compliance em escala

- LGPD exige capacidade de responder pedidos de exclusão/portabilidade de dados em prazo — com milhões de usuários, isso precisa ser um fluxo automatizado, não manual
- Auditoria (Bacen, se em algum momento o produto operar como correspondente bancário) precisa de trilha de log completa e imutável — já é a base do `log_json` documentado, mas em escala isso vai para um sistema de log dedicado (ex: dados append-only em S3 + Athena para consulta)

---

## Parte 2 — O que ninguém mais está entregando (a lista real de diferenciais)

Comparando com os três tipos de concorrente que existem hoje no Brasil — **apps de score dos próprios birôs** (Serasa Consumidor, Boa Vista), **escritórios de negociação/limpa nome**, e **comparadores de crédito genéricos**:

| Diferencial | Serasa/Boa Vista (apps de biro) | Escritórios de negociação | Comparadores de crédito | Este produto |
|---|---|---|---|---|
| Explica **por que** o score está naquele número, fator a fator, em linguagem simples | Parcial (mostra fatores, mas genérico) | Não | Não | ✓ (`relatorio_detalhado_exemplo.md`) |
| Dá **prazo estimado em dias** para cada ação, não só "melhore isso" | Não | Não | Não | ✓ |
| Lista as **dívidas/faturas específicas** pesando no score, com linha digitável quando disponível | Parcial (só negativadas, sem contexto de score) | Sim, mas sem ligar ao score | Não | ✓ (`listagem_boletos_pendencias.md`) |
| Mostra **sempre a opção gratuita antes da paga** para resolver cada pendência | Não (empurra plano pago) | Não (o negócio deles é a cobrança) | Não se aplica | ✓ (`guia_pratico_aumento_score.md`) |
| Cobra pela negociação **só se o resultado for confirmado** | Não se aplica | Raro — muitos cobram taxa de entrada | Não se aplica | ✓ |
| Publica **métrica agregada real e auditável** de quanto os usuários melhoram | Não | Não | Não | Proposto em `solucao_completa_nome_limpo_score.md` |
| Une diagnóstico + execução + marketplace pré-qualificado numa jornada só | Não (só diagnóstico) | Não (só execução) | Não (só marketplace) | ✓ — é o produto completo |

## O argumento de posicionamento (resumo para pitch/marketing)

> "Os apps de score te mostram um número. Os escritórios resolvem sua dívida, mas não te explicam nada e cobram antes de saber se vai funcionar. Nós fazemos as duas coisas, mostramos o porquê de cada número, o prazo real, e só cobramos quando o resultado é confirmado."

## Ordem recomendada de expansão nacional

1. **Fase 1 — Região piloto** (ex: uma capital ou estado): validar o fluxo completo com volume controlado, negociação humana ainda manual
2. **Fase 2 — Automação de negociação** para os credores mais comuns nacionalmente (bancos grandes, principais financeiras de varejo) antes de expandir geograficamente — isso é o que permite escalar sem escalar o time de atendimento na mesma proporção
3. **Fase 3 — Expansão nacional** apoiada em conteúdo educacional (redes sociais) como motor de aquisição de baixo custo, com o produto já provado tecnicamente
4. **Fase 4 — B2B/white-label**, uma vez que a marca tenha reconhecimento suficiente para outras empresas quererem licenciar a tecnologia
