# O Lema

> **"A gente resolve seu nome sujo e aumenta seu score — e te mostra exatamente como, passo a passo, até o fim."**

## O que esse lema significa na prática

| Palavra do lema | O que isso obriga o produto a fazer |
|---|---|
| **"A gente resolve"** | Não é só diagnóstico — o app executa a negociação em nome do usuário quando ele quiser (Pilar 2, `docs/solucao_completa_nome_limpo_score.md`), igual um escritório de verdade faz |
| **"nome sujo e aumenta seu score"** | As duas coisas juntas, na mesma jornada — não é um app só de score (que não resolve nada) nem um escritório só de negociação (que não explica nada) |
| **"te mostra exatamente como"** | Cada fator do score explicado em linguagem simples, cada dívida listada com valor e credor, cada ação com prazo em dias — nunca uma caixa preta (`docs/relatorio_detalhado_exemplo.md`, `docs/listagem_boletos_pendencias.md`) |
| **"passo a passo"** | O plano de ação é sequencial e rastreável — o usuário vê exatamente em que etapa está, o que já foi feito e o que falta |
| **"até o fim"** | O produto acompanha até a baixa ser confirmada no birô, não some depois de vender — e só cobra depois que o resultado é confirmado |

## Onde esse lema já está implementado (não é só intenção)

- O status de cada negociação é rastreado etapa por etapa no código (`StatusNegociacao` em `backend/app/core/negociacao.py`) — o usuário nunca fica sem saber "em que pé está"
- A comissão só é calculada quando a baixa é confirmada — isso é uma regra que o próprio código impede de ser quebrada, testada em `test_comissao_nao_pode_ser_calculada_em_estado_iniciada` e afins
- O detalhamento fator a fator já está especificado e funcionando no motor de score

## Onde esse lema deve aparecer no produto

1. **Tela de boas-vindas / onboarding** — primeira frase que o usuário vê
2. **Topo do dashboard de score** — reforço visual toda vez que o app abre
3. **Material de marketing/aquisição** — é o argumento central de posicionamento, já detalhado em `docs/estrategia_nacional_diferenciais.md`
4. **Rodapé de e-mails/notificações** — assinatura da marca em toda comunicação
