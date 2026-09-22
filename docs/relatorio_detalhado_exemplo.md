# Relatório Detalhado — Exemplo de Saída (CPF com score 530)

## Objetivo deste documento

Especificar exatamente o que o usuário vê na tela quando consulta o CPF: não só o número do score, mas o **"porquê" de cada fator**, escrito em linguagem simples, com **direção de ação** e **tempo estimado**. Este é o formato de referência para a equipe de produto/frontend implementar a tela real.

---

## Tela: Diagnóstico Detalhado

```
════════════════════════════════════════════════════════════
  SEU SCORE: 530 (FAIXA: REGULAR)
════════════════════════════════════════════════════════════

  Por que seu score está em 530?

  Seu score é calculado combinando 5 fatores. Veja o peso de
  cada um e o que está pesando a favor ou contra você:
```

### Fator 1 — Histórico de pagamento (peso 35% — o que mais pesa)

```
  ✓ 78% dos seus pagamentos nos últimos 24 meses foram em dia

  POR QUE ISSO AFETA SEU SCORE:
  Este é o fator mais pesado do cálculo. Cada atraso registrado
  reduz a confiança do modelo em você pagar em dia no futuro.
  Você tem 2 atrasos recentes (Credor Alfa: 120 dias; Loja Beta: 30 dias)
  que ainda estão "pesando" contra você.

  DIREÇÃO PARA MELHORAR:
  → Quitar as 2 dívidas em atraso (ver botões de negociação abaixo)
  → Depois de quitadas, manter 100% dos pagamentos futuros em dia

  TEMPO ESTIMADO:
  A baixa da dívida no birô leva até 5 dias úteis após o pagamento.
  Mas o "peso" desse atraso no seu score só se dissolve totalmente
  depois de cerca de 55 a 85 dias — é o tempo que o modelo do
  birô leva para considerar o atraso "resolvido e superado".
```

### Fator 2 — Utilização de crédito (peso 30%)

```
  ⚠ Você está usando 88% do limite disponível dos seus cartões

  POR QUE ISSO AFETA SEU SCORE:
  Usar quase todo o limite disponível é interpretado como sinal
  de aperto financeiro, mesmo que você pague em dia. O ideal
  considerado "saudável" pelo mercado é usar até 30% do limite.

  DIREÇÃO PARA MELHORAR:
  → Reduzir o uso do cartão de 88% para 30% do limite
  → Alternativa: pedir aumento de limite ao banco (sem usar o
    valor extra) — isso reduz o percentual sem precisar pagar mais

  TEMPO ESTIMADO:
  30 a 45 dias — é o tempo até a fatura fechar e o birô receber
  a informação atualizada de uso do limite.
```

### Fator 3 — Tempo de relacionamento com crédito (peso 15%)

```
  ✓ Você tem 42 meses de histórico de crédito

  POR QUE ISSO AFETA SEU SCORE:
  Quanto mais tempo de histórico, mais dado o modelo tem para
  confiar em você. Este fator está jogando A SEU FAVOR.

  DIREÇÃO:
  Nenhuma ação necessária — esse fator só melhora com o tempo,
  naturalmente, mantendo suas contas ativas.
```

### Fator 4 — Diversidade de crédito (peso 10%)

```
  • Você tem 3 tipos de crédito ativos (cartão, empréstimo, financiamento)

  POR QUE ISSO AFETA SEU SCORE:
  Ter tipos diferentes de crédito bem administrados mostra
  capacidade de lidar com produtos financeiros diversos.
  Você já está numa faixa considerada equilibrada — nem pouco,
  nem excesso de produtos.

  DIREÇÃO:
  Nenhuma ação necessária agora.
```

### Fator 5 — Consultas recentes ao CPF (peso 10%)

```
  ⚠ 2 consultas ao seu CPF nos últimos 30 dias

  POR QUE ISSO AFETA SEU SCORE:
  Muitas consultas em pouco tempo podem indicar que você está
  buscando crédito em vários lugares ao mesmo tempo, o que é
  visto como sinal de risco pelo modelo do birô.

  DIREÇÃO PARA MELHORAR:
  → Evitar solicitar crédito/consultar CPF em múltiplos lugares
    nos próximos 90 dias

  TEMPO ESTIMADO:
  O efeito dessas consultas se dissolve gradualmente em até 90 dias.
```

---

## Resumo executivo (topo da tela, antes dos detalhes)

```
════════════════════════════════════════════════════════════
  RESUMO: SE VOCÊ SEGUIR O PLANO...

  Score atual:            530
  Score estimado em 90 dias:  606  (+76 pontos)

  Isso é uma ESTIMATIVA baseada em modelo estatístico interno,
  não um recálculo oficial do birô.
════════════════════════════════════════════════════════════
```

## Regra de escrita do texto explicativo (para quem for gerar isso dinamicamente)

Cada fator, ao ser exibido, segue sempre a mesma estrutura de 3 blocos:

1. **O que está acontecendo** — fato objetivo, sem jargão ("você está usando 88% do limite")
2. **Por que isso afeta o score** — explicação em 1-2 frases, sem termos técnicos de modelo estatístico
3. **Direção + tempo estimado** — sempre uma ação clara, e sempre um prazo em dias (nunca "logo" ou "em breve")

Isso garante que o usuário nunca veja só o número — ele sempre entende o "porquê" e sai com uma ação concreta na mão.
