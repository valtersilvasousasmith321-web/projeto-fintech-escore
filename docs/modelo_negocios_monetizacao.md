# Modelo de Negócios e Monetização

## Princípio comercial

Monetização baseada em **valor entregue e permitido por lei** — nunca cobrança por "garantia de aprovação" (isso configuraria, na prática, venda de algo que não pode ser entregue, com risco de enquadramento como propaganda enganosa/estelionato conforme o caso).

## Linhas de receita — Pessoa Física (PF)

| Linha | Modelo | Descrição |
|---|---|---|
| Freemium — Score básico | Grátis | Score consolidado + 3 fatores principais |
| Assinatura Plus | R$ 19,90/mês | Score detalhado, plano de ação completo, alertas de consulta de CPF em tempo real, histórico de 24 meses |
| Assinatura Premium | R$ 39,90/mês | Tudo do Plus + monitoramento de CNPJ (para autônomos/MEI), simulações ilimitadas de cenários |
| Comissão por lead qualificado (marketplace) | % sobre operação fechada, paga pelo parceiro financeiro, **nunca pelo usuário** | Parceiro paga apenas se o crédito for efetivamente contratado — modelo de performance, comum em comparadores de crédito |

## Linhas de receita — Pessoa Jurídica (PJ)

| Linha | Modelo | Descrição |
|---|---|---|
| Score empresarial | R$ 79,90/mês | Score de CNPJ + certidões PGFN/Receita consolidadas + alertas de pendência fiscal |
| API B2B para concessionárias/varejo | Contrato de licenciamento (setup + mensalidade por volume de consultas) | Empresas (ex: concessionárias de veículos, imobiliárias) usam nossa API de pré-qualificação para filtrar leads antes de encaminhar para análise de crédito própria |
| White-label do motor de elegibilidade | Contrato customizado | Fintechs menores licenciam nosso motor de regras de elegibilidade para seus próprios produtos |

## Estrutura de contrato B2B com parceiros de originação (ex: concessionárias)

O contrato deve deixar explícito, em cláusula própria:

1. O parceiro **paga por lead qualificado entregue**, não por aprovação garantida
2. Definição contratual de "lead qualificado" = usuário que atende a X% dos critérios mínimos publicados pelo próprio parceiro
3. Nenhuma cláusula de SLA de taxa de aprovação — isso seria uma promessa sobre decisão de terceiro (o banco financiador), que o parceiro/concessionária não controla e nós também não
4. Cláusula de compliance: dados trafegados seguem LGPD, com log de consentimento auditável, disponível para o parceiro em caso de fiscalização

## Por que este modelo é sustentável (vs. o modelo "garantido")

- **Modelo garantido**: gera receita rápida no curto prazo (usuários pagam por uma promessa), mas colapsa no primeiro ciclo de negações em massa — geraria ações no Procon, reclamações em massa, e risco de enquadramento penal para os sócios.
- **Modelo de transparência + performance**: receita menor por usuário no curto prazo, mas parceiros financeiros só integram (e pagam comissão) com empresas que não geram passivo jurídico para eles. Isso é o que permite fechar contratos reais com bancos e fintechs — nenhuma instituição regulada assina parceria com um marketplace que promete decisão que não é dele.

## Métricas-chave (KPIs) para o modelo de negócio

- **Taxa de conversão de lead qualificado → operação fechada** (mede qualidade real da pré-qualificação, não taxa de "aprovação garantida")
- **Churn de assinatura Plus/Premium**
- **Ticket médio de comissão por operação fechada** (varia por tipo de crédito: pessoal, consignado, veicular, PJ)
- **NPS pós-recusa** (mede se o usuário entende por que foi recusado mesmo pré-qualificado — indicador direto de saúde jurídica do produto)
