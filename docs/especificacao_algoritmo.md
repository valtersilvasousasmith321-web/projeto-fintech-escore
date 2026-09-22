# Especificação do Algoritmo de Impacto no Score

## Aviso de escopo

Este documento descreve o **modelo interno de estimativa de impacto** usado para gerar o plano de ação do usuário. Ele **não recalcula o score oficial** — o score oficial é sempre calculado pelo birô (Serasa, Quod, etc.) com modelo proprietário e fatores não totalmente públicos. Nosso modelo é uma **aproximação estatística educativa**, treinada sobre correlações publicamente conhecidas e documentadas pelos próprios birôs.

## Fatores considerados e pesos relativos

Baseado em fatores publicamente divulgados pelos birôs brasileiros (Serasa, Boa Vista) como componentes do score:

| Fator | Peso relativo | Direção |
|---|---|---|
| Histórico de pagamento (pontualidade últimos 24 meses) | 35% | quanto mais pontual, maior o score |
| Utilização de crédito (saldo devedor / limite total) | 30% | quanto menor a utilização, maior o score |
| Tempo de relacionamento com o mercado de crédito | 15% | quanto mais tempo, maior o score |
| Diversidade de tipos de crédito ativos | 10% | diversidade moderada é positiva |
| Consultas recentes ao CPF (hard inquiries) | 10% | quanto mais consultas em curto período, menor o score |

## Fórmula de impacto estimado

Para cada ação simulada, o impacto estimado em pontos é:

```
impacto_estimado = peso_fator * delta_normalizado * fator_confianca
```

Onde:
- `peso_fator`: peso relativo da tabela acima (0.0 a 1.0)
- `delta_normalizado`: variação da métrica subjacente, normalizada entre -1 e 1
  - Ex: reduzir utilização de crédito de 90% para 30% → delta_normalizado = (0.90 - 0.30) = 0.60
- `fator_confianca`: 0.5 a 0.9, baseado no volume de dados históricos disponíveis para aquele usuário (mais histórico = mais confiança na estimativa)
- O resultado é multiplicado pela amplitude típica de variação de score (ex: 100 pontos numa escala de 0-1000) e arredondado

### Exemplo de cálculo — reduzir utilização de cartão

```
peso_fator = 0.30 (utilização de crédito)
delta_normalizado = 0.60 (de 90% para 30% de uso do limite)
fator_confianca = 0.7 (usuário com 8 meses de histórico via Open Finance)
amplitude_escala = 100 pontos

impacto_estimado = 0.30 * 0.60 * 0.7 * 100 = 12.6 pontos (estimativa)
prazo_estimado = 30 a 45 dias (tempo médio de atualização de fatura reportado ao biro)
```

## Penalização por consulta de CPF (hard inquiry)

Quando o sistema detecta, via biro, uma **nova consulta de crédito no CPF do usuário** (ex: ele solicitou empréstimo em outro app), a lógica é:

```
penalizacao = peso_consulta * numero_consultas_30_dias * fator_severidade
```

- `peso_consulta = 0.10` (peso do fator "consultas recentes")
- `numero_consultas_30_dias`: contagem de hard inquiries nos últimos 30 dias
- `fator_severidade`: 1.0 para a primeira consulta no período, crescendo 0.3 a cada consulta adicional (múltiplas consultas em curto período são desproporcionalmente negativas, refletindo o comportamento real dos modelos de biro)

Quando uma nova consulta é detectada:

1. O sistema recalcula o `prazo_estimado_dias` de todas as ações em andamento no plano do usuário, adicionando um fator de atraso (`+15 dias` de janela de estabilização por consulta detectada)
2. Um evento é disparado (webhook interno) para notificar o usuário: *"Detectamos uma nova consulta ao seu CPF em [data]. Isso pode ter impacto temporário no seu score. Seu plano de ação foi recalculado."*
3. O evento é logado para auditoria (ver seção de logs abaixo)

## Logs de erro e auditoria do usuário

Toda vez que o motor de cálculo roda para um usuário, gera um log estruturado (JSON) com:

```json
{
  "usuario_id": "uuid",
  "timestamp": "ISO8601",
  "fatores_entrada": { "utilizacao_credito": 0.42, "pontualidade_24m": 0.95, "..." : "..." },
  "score_estimado_anterior": 612,
  "score_estimado_novo": 624,
  "delta": 12,
  "acoes_recalculadas": ["reduzir_limite_cartao_x", "quitar_divida_y"],
  "alertas": ["nova_consulta_cpf_detectada"],
  "confianca_modelo": 0.7,
  "fonte_dados": ["open_finance_pluggy", "biro_serasa"]
}
```

Esses logs são a base para:
- Auditoria de compliance (mostrar exatamente por que o sistema deu uma recomendação)
- Debug quando o usuário reporta "o score real não bateu com a estimativa"
- Melhoria contínua do modelo (retraining supervisionado usando o delta real reportado pelo biro vs. o estimado)
