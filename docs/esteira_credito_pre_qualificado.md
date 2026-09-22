# Esteira de Crédito Pré-Qualificado

## Princípio central

Esta esteira **não aprova crédito** e **não emite nenhum token de garantia**. Ela faz uma coisa, de forma honesta: verifica se o usuário atende aos **critérios mínimos publicados** por cada parceiro financeiro, e só então mostra a oferta a ele. A decisão de aprovação, análise de risco e condições finais são sempre feitas pelo parceiro, no ambiente dele, seguindo a política de crédito dele.

Isso é o mesmo modelo usado por marketplaces de crédito legítimos que operam no Brasil (ex: comparadores de empréstimo) — eles filtram elegibilidade, não decidem crédito.

## Fluxo técnico

```
┌──────────────┐
│   Usuário     │
└──────┬────────┘
        │ 1. Consulta ofertas disponíveis
        ▼
┌───────────────────────────┐
│  Motor de Elegibilidade     │
│  (regras publicadas         │
│   por cada parceiro)        │
└──────┬─────────────────────┘
        │ 2. Compara critérios do usuário (score, renda declarada,
        │    restrições ativas) com critérios mínimos do parceiro
        ▼
┌───────────────────────────┐
│  Ranking de ofertas          │
│  "pré-qualificadas"          │
│  (% de critérios atendidos)  │
└──────┬─────────────────────┘
        │ 3. Usuário escolhe oferta
        ▼
┌───────────────────────────┐
│  Redirecionamento/API do     │
│  parceiro (fluxo próprio,    │
│  fora do nosso controle)     │
└──────┬─────────────────────┘
        │ 4. Parceiro faz sua própria análise
        ▼
   Aprovado / Negado (decisão do parceiro)
```

## Critérios de elegibilidade (exemplo de estrutura, não valores reais de contrato)

Cada parceiro publica (via API própria ou contrato comercial) critérios mínimos, por exemplo:

```json
{
  "parceiro_id": "exemplo_fintech_x",
  "produto": "credito_pessoal",
  "criterios_minimos": {
    "score_minimo": 550,
    "sem_restricao_ativa": true,
    "renda_minima_declarada": 1800,
    "tempo_minimo_relacionamento_bancario_meses": 6
  }
}
```

O motor de elegibilidade compara os dados do usuário (via Open Finance + biro) contra esses critérios e retorna um **percentual de aderência**, nunca uma promessa de aprovação:

```
"Você atende a 3 de 4 critérios desta oferta (75%). 
 Critério não atendido: renda mínima declarada.
 A decisão final de aprovação é sempre do parceiro."
```

## Integração com parceiros — modelo real (não mTLS "de garantia")

A integração técnica com cada parceiro segue o padrão de API do próprio parceiro — normalmente:

1. **Autenticação**: OAuth2 client credentials (padrão de mercado) ou API key + HMAC de request, conforme especificação de cada parceiro
2. **mTLS quando exigido pelo parceiro**: alguns bancos exigem certificado mútuo por política de segurança de infraestrutura — isso é uma exigência de transporte seguro (proteger dados em trânsito), **não um mecanismo de "garantia de aprovação"**. mTLS autentica *quem está falando*, não decide crédito.
3. **Payload de encaminhamento de lead**: contém apenas os dados que o usuário consentiu compartilhar (CPF, dados de contato, e opcionalmente o snapshot de elegibilidade calculado) — assinado digitalmente (JWS) apenas para garantir **integridade e não-repúdio do lead**, não para "forçar" decisão

```json
{
  "lead_id": "uuid",
  "usuario_documento": "hash_ou_cpf_conforme_contrato",
  "snapshot_elegibilidade": { "score_estimado": 610, "aderencia_criterios": 0.75 },
  "timestamp": "ISO8601",
  "assinatura_jws": "..."
}
```

4. **Resposta do parceiro**: assíncrona, via webhook — `pendente`, `em_analise`, `aprovado`, `negado`, `aprovado_condicional` — e essa resposta é sempre do sistema de decisão do parceiro, nunca da nossa esteira.

## O que fazer quando o usuário pergunta "por que não fui aprovado se o app disse que eu era elegível?"

Resposta padrão do produto (deve estar no manual de atendimento):

> "A pré-qualificação mostra que você atendia aos critérios *públicos* do parceiro no momento da consulta. A análise final considera fatores adicionais (política interna de risco, capacidade de pagamento detalhada, verificação de identidade) que não são compartilhados publicamente pelo parceiro. Isso não significa que sua elegibilidade estava errada — significa que a decisão de crédito tem uma etapa final que só o parceiro controla."

Essa transparência é o que protege legalmente o produto de acusações de propaganda enganosa (Código de Defesa do Consumidor, art. 37).
