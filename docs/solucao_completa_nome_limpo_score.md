# Solução Completa — Nome Limpo e Score em Alta

## A promessa real (o que pode ser dito publicamente)

> "Nós resolvemos seu nome sujo e aumentamos seu score — mostrando exatamente o que fazemos, quanto custa, e provando o resultado com dado real."

Isso é diferente de "garantimos aprovação de crédito". É uma promessa sobre **um processo que a empresa controla** (diagnóstico, negociação, acompanhamento), não sobre uma decisão de terceiro (o banco). É por isso que pode ser cumprida de verdade — e é isso que sustenta a fama no médio prazo.

## Os três pilares do serviço

### Pilar 1 — Diagnóstico (grátis, é a porta de entrada)
Já documentado em `especificacao_algoritmo.md` e `arquitetura_dados.md`. O usuário entra, conecta Open Finance e biro, e em minutos vê exatamente por que o nome está sujo e por que o score está baixo. Isso sozinho já é mais do que 90% do mercado oferece de graça.

### Pilar 2 — Execução (aqui é onde a empresa cobra)
Diferente dos escritórios genéricos, a execução é **por resultado, com transparência de processo**:

```
Fluxo de execução por dívida:

1. Sistema identifica a dívida e busca automaticamente:
   - Oferta pública no Serasa Limpa Nome / Boa Vista (grátis)
   - Se não houver oferta pública boa, oferece negociação assistida (paga)

2. Se o usuário aceita a negociação assistida:
   a. Assina procuração digital (e-CPF ou assinatura eletrônica simples,
      conforme MP 2.200-2/2001 e Lei 14.063/2020)
   b. Equipe/robô de negociação contata o credor
   c. Usuário recebe proposta ANTES de qualquer cobrança —
      só paga comissão se aceitar o acordo negociado
   d. Sistema acompanha a baixa no biro e confirma quando o nome
      efetivamente sai da lista de negativados

3. Cada etapa gera um evento no dashboard do usuário (status em tempo real,
   não uma caixa preta)
```

### Pilar 3 — Evolução do score (o que mantém o usuário por mais tempo)
Depois que o nome está limpo, a dívida quitada por si só não faz o score subir rápido — o produto mantém o usuário no **plano de ação contínuo** (utilização de crédito, comportamento, monitoramento), que é a parte por assinatura recorrente (`modelo_negocios_monetizacao.md`).

## Por que isso pode ficar "famoso no que faz"

| Alavanca de reputação | Como o produto entrega isso |
|---|---|
| **Prova pública e auditável** | Publicar métrica agregada real (ex: "score médio dos usuários ativos há 6 meses subiu X pontos"), gerada a partir do próprio `log_json` do motor de auditoria — não é número de marketing, é dado do sistema |
| **Nunca cobra sem entregar** | Comissão só é cobrada se o acordo for aceito e a baixa confirmada no biro — isso vira o argumento de venda ("só ganhamos se você ganhar") |
| **Transparência que o mercado não tem** | Mostrar sempre a opção grátis antes da paga (já documentado no guia prático) — isso é o tipo de prática que vira notícia/recomendação boca a boca em canais de educação financeira |
| **Conteúdo educacional aberto** | Publicar o próprio guia de "onde negociar de graça" como conteúdo público (redes sociais, blog) — vira ferramenta de aquisição de usuário e de autoridade no assunto |

## Estrutura de preço proposta para a execução (Pilar 2)

| Situação | Cobrança |
|---|---|
| Existe oferta pública de desconto (Serasa Limpa Nome etc.) | Grátis — o app só direciona o usuário |
| Negociação assistida, dívida até R$ 2.000 | Comissão de 15% sobre o valor do desconto conseguido, cobrada só após confirmação da baixa |
| Negociação assistida, dívida acima de R$ 2.000 ou múltiplos credores | Comissão de 10% sobre o desconto total, escalonada (quanto maior o valor, menor o percentual) |
| Usuário quer negociar sozinho, só precisa de orientação | Incluso na assinatura Plus/Premium (sem cobrança adicional) |

## O que precisa existir tecnicamente para isso funcionar (próximos módulos)

1. **Módulo de assinatura eletrônica de procuração** — integração com provedor de assinatura digital (ex: Clicksign, D4Sign) para autorizar a empresa a negociar em nome do usuário
2. **Módulo de tracking de negociação** — status em tempo real por dívida (`iniciada`, `proposta_recebida`, `aceita_pelo_usuario`, `paga`, `baixa_confirmada`)
3. **Módulo de faturamento pós-resultado** — só gera cobrança quando o status vira `baixa_confirmada`, nunca antes
4. **Painel público de métricas agregadas** — página institucional mostrando os números reais e atualizados (sem expor dados individuais de usuários, conforme LGPD)

## O limite que não pode ser cruzado

Mesmo cobrando pela execução, o produto **continua sem prometer aprovação de crédito de terceiros** (isso é o marketplace, Pilar separado, documentado em `esteira_credito_pre_qualificado.md`). O que se vende aqui é **trabalho de negociação e acompanhamento, com resultado mensurável e reembolsável se não for entregue** — isso é o que pode virar reputação forte sem risco jurídico.
