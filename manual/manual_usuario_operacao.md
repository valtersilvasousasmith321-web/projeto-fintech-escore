# Manual do Usuário — Jornada de Evolução do Score

## Etapa 1 — Cadastro e consentimento

1. Usuário cria conta (PF: CPF; PJ: CNPJ + CPF do responsável)
2. Tela de consentimento LGPD, granular: o usuário escolhe explicitamente quais fontes autoriza (Open Finance, consulta a biro, bases públicas)
3. Nenhuma fonte é consultada sem consentimento explícito e registrado com timestamp

## Etapa 2 — Diagnóstico inicial

1. Sistema consulta score atual via biro (soft inquiry, não penaliza o usuário)
2. Sistema conecta Open Finance (se autorizado) para trazer extratos e comportamento de crédito
3. Dashboard mostra:
   - Score atual (número + faixa: ruim, regular, bom, muito bom, excelente)
   - Os 5 fatores que mais pesam no score dele, com participação percentual
   - Alertas de restrições ativas (se houver)

## Etapa 3 — Plano de ação personalizado

O sistema gera uma lista de ações ordenadas por **impacto estimado / esforço**, por exemplo:

```
1. Reduzir uso do limite do cartão XPTO de 88% para 30%
   Impacto estimado: +12 a +18 pontos
   Prazo estimado: 30-45 dias após a fatura fechar
   Esforço: baixo

2. Quitar dívida em aberto com Credor Y (R$ 340,00)
   Impacto estimado: +25 a +40 pontos
   Prazo estimado: até 60 dias após baixa no biro
   Esforço: médio

3. Evitar novas consultas de CPF nos próximos 90 dias
   Impacto estimado: preserva pontuação atual
   Esforço: comportamental
```

Cada ação tem um botão "marcar como concluída" — quando marcada, o sistema agenda uma nova consulta ao biro no prazo estimado para validar se o impacto real bateu com o estimado (e usa isso para recalibrar o modelo).

**Cada ação também mostra o canal onde o usuário pode efetivamente agir** — não fica só no diagnóstico. Ex: para "quitar dívida", o app mostra os botões "Negociar direto com o credor" (grátis), "Ver oferta no Serasa Limpa Nome" (grátis) e "Contratar assessoria de negociação" (comissão 10-20% sobre o desconto conseguido), sempre priorizando a opção gratuita. Ver `docs/guia_pratico_aumento_score.md` para a lista completa de canais por tipo de ação.

## Etapa 4 — Monitoramento contínuo

- Alerta em tempo real se uma nova consulta ao CPF for detectada
- Alerta se uma dívida ativa mudar de status (ex: for negativada)
- Recalculo automático do plano de ação sempre que novos dados chegam via Open Finance

## Etapa 5 — Marketplace (quando o score/perfil permitir)

1. Usuário acessa aba "Ofertas"
2. Sistema mostra ofertas com o **percentual de aderência aos critérios mínimos** de cada parceiro (nunca "aprovado")
3. Usuário escolhe encaminhar seus dados (consentimento específico, separado do consentimento de diagnóstico) para o parceiro
4. Parceiro analisa e responde (prazo varia por parceiro, tipicamente 1 a 5 dias úteis)
5. Status é atualizado no app: `em análise` → `aprovado` / `negado` / `aprovado com condições`

## Texto padrão obrigatório em toda tela de oferta

> "Esta é uma pré-qualificação baseada em critérios públicos do parceiro. A decisão final de crédito é exclusiva da instituição financeira."

## Atendimento — perguntas frequentes que a equipe de suporte deve saber responder

**"Por que meu score no app é diferente do score que vi direto no Serasa?"**
→ Porque o app mostra o score oficial do biro (mesma fonte), mas os "pontos estimados" de cada ação são uma projeção nossa, não um recálculo oficial. O número principal do dashboard é sempre o dado real do biro, atualizado na última consulta.

**"Fui pré-qualificado e mesmo assim fui negado, isso é enganação?"**
→ Não. Explicar a diferença entre pré-qualificação (critérios públicos) e análise final (critérios internos do parceiro), conforme texto padrão da esteira.
