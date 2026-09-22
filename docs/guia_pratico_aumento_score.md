# Guia Prático — Onde Agir para Aumentar o Score (e o que cada canal cobra)

## Princípio deste guia

Cada ação do plano (ver `especificacao_algoritmo.md`) precisa virar um **link acionável**: não basta dizer "quite sua dívida", o app precisa dizer **onde** o usuário faz isso e **quanto custa** (taxa, comissão, ou se é gratuito). Isso é o que separa o produto de um dashboard bonito de um produto que resolve o problema.

---

## 1. Negociar/quitar dívida ativa

### Onde fazer

| Canal | Como funciona | Custo para o usuário |
|---|---|---|
| **Direto com o credor** (banco, loja, financeira) | Ligar/acessar app do próprio credor e pedir renegociação | Grátis (o desconto negociado é o "ganho", não há taxa de intermediação) |
| **Serasa Limpa Nome** (serasalimpanome.com.br) | Plataforma gratuita que lista dívidas negativadas com descontos já pré-negociados pelos credores parceiros | Grátis — Serasa é remunerada pelo credor, não pelo usuário |
| **Boa Vista "Como Limpar Meu Nome"** (consumidor.boavistaservicos.com.br) | Similar ao Serasa, para dívidas registradas na base deles | Grátis |
| **Consumidor.gov.br** | Canal oficial do governo para reclamar/negociar quando o credor não responde | Grátis |
| **Escritórios de assessoria/negociação de dívida** (ex: Recovery, escritórios independentes) | Negociam em nome do usuário mediante procuração | Comissão de 10% a 20% sobre o valor do desconto conseguido, cobrada só se houver acordo (modelo comum no mercado) |

### Recomendação de exibição no app

```
Dívida: Credor Alfa Financeira — R$ 340,00 (120 dias de atraso)

  → [Negociar direto com o credor]   (grátis, recomendado primeiro)
  → [Ver oferta no Serasa Limpa Nome] (grátis, se disponível para esta dívida)
  → [Contratar assessoria de negociação] (comissão 10-20% sobre desconto,
     recomendado só se as opções gratuitas não resolverem)
```

O app deve **sempre mostrar a opção gratuita primeiro**, e só oferecer a assessoria paga como alternativa quando fizer sentido (dívida antiga, credor sem canal de negociação direta, ou o usuário já tentou e não conseguiu).

---

## 2. Reduzir utilização de limite de cartão

### Onde fazer
Direto no app do próprio banco/cartão — não existe intermediário aqui. O produto só orienta:

1. Priorizar pagamento acima do mínimo na fatura atual
2. Se possível, pedir aumento de limite (reduz o *percentual* de uso sem precisar pagar mais — mas só funciona se o banco aprovar, e não se deve usar o limite extra)
3. Considerar portabilidade de dívida de cartão para uma linha com juros menores (ver seção 4)

**Custo**: gratuito — é comportamento financeiro, não um serviço a ser contratado.

---

## 3. Consultar e corrigir cadastro no biro

### Onde fazer

| Canal | Serviço | Custo |
|---|---|---|
| **Registrato (Banco Central)** — registrato.bcb.gov.br | Relatório oficial e gratuito de todas as operações de crédito em seu nome, útil para conferir se alguma dívida está errada/duplicada | Grátis |
| **Serasa Consumidor** (app/site) | Consulta de score e relatório detalhado, disputa de dados incorretos | Plano gratuito cobre consulta básica e contestação; planos pagos (a partir de ~R$ 19,90/mês) dão monitoramento e relatório completo |
| **Quod** (app "Quero Meu Score") | Similar ao Serasa | Consulta básica grátis |

Se o usuário encontrar uma dívida **que não reconhece ou já paga e ainda aparece negativada**, o caminho correto é contestação direta no biro (prazo legal de resposta: até 5 dias úteis conforme CDC) — isso é **sempre gratuito**, nunca deveria ser cobrado.

---

## 4. Portabilidade de dívida / crédito com juros menores

### Onde fazer
- **Portabilidade de crédito consignado**: qualquer banco que ofereça consignado pode fazer a portabilidade da dívida de outro banco, por lei (Resolução CMN), sem custo de tarifa de portabilidade
- Comparadores de crédito (ver módulo de marketplace do produto) mostram as taxas de cada banco lado a lado

**Custo**: a portabilidade em si é gratuita por lei; o que muda é a taxa de juros da nova operação, que precisa ser comparada.

---

## 5. Resumo — tabela de decisão para o usuário

| Se a situação é... | Primeiro canal a tentar | Custo esperado |
|---|---|---|
| Dívida pequena, credor de banco grande | Negociar direto no app do banco | Grátis |
| Dívida negativada há tempo, credor sem resposta | Serasa Limpa Nome / Boa Vista | Grátis |
| Múltiplas dívidas, sem tempo/energia para negociar sozinho | Assessoria de negociação | Comissão 10-20% sobre desconto |
| Dado errado no cadastro do biro | Contestação direto no biro | Grátis (é direito do consumidor) |
| Cartão com limite muito usado | Ação comportamental própria | Grátis |
| Consignado com juros altos | Portabilidade em outro banco | Grátis (a portabilidade em si) |

## Regra de produto (importante)

O app **nunca deve esconder a opção gratuita** para empurrar a paga. Isso é o que mantém a confiança do usuário e evita risco regulatório (CDC, práticas abusivas). A assessoria paga é uma opção legítima de conveniência — não a única, e o app deve deixar isso explícito na interface.
