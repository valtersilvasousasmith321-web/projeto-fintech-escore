# Listagem de Boletos e Pendências — Como Puxar e Exibir

## O que é tecnicamente possível puxar (importante ser realista aqui)

Não existe uma API única que devolve "o boleto" (o PDF/imagem) de qualquer credor do Brasil — cada empresa emite boleto no seu próprio sistema. O que **existe e é possível puxar de forma confiável** são os **registros da dívida**, vindos de duas fontes:

| Fonte | O que retorna | Nível de detalhe |
|---|---|---|
| **Birôs (Serasa/Quod/Boa Vista)** | Dívidas negativadas: credor, valor original, data de inclusão, dias em atraso | Não traz o boleto em si, mas traz todos os dados para localizá-lo/negociá-lo |
| **Open Finance (Pluggy/Belvo)** | Faturas em aberto vinculadas às contas conectadas pelo usuário (cartão, conta corrente) | Pode trazer valor, vencimento, e em muitos casos a **linha digitável** do boleto/fatura, quando o banco de origem expõe esse dado via Open Finance |
| **Registrato (Bacen)** | Todas as operações de crédito formais em nome do CPF/CNPJ | Não traz boletos avulsos (contas de consumo, por ex.), só operações de crédito regulado |

Ou seja: para **dívidas negativadas** (já viraram "nome sujo"), a fonte é o birô. Para **faturas ainda não vencidas ou recém-vencidas** (ainda não foram para o birô), a fonte é o Open Finance, quando o usuário conecta a conta de origem.

## Estrutura de dado consolidada (o que o app monta a partir das duas fontes)

```json
{
  "pendencias": [
    {
      "credor": "Credor Alfa Financeira",
      "valor": 340.00,
      "data_vencimento_original": "2026-05-18",
      "dias_atraso": 120,
      "origem": "biro_serasa",
      "negativado": true,
      "linha_digitavel": null,
      "acoes_disponiveis": ["negociar_direto", "ver_oferta_limpa_nome", "assessoria_paga"]
    },
    {
      "credor": "Loja Beta Varejo",
      "valor": 89.90,
      "data_vencimento_original": "2026-08-16",
      "dias_atraso": 30,
      "origem": "biro_boa_vista",
      "negativado": true,
      "linha_digitavel": null,
      "acoes_disponiveis": ["negociar_direto", "ver_oferta_limpa_nome"]
    },
    {
      "credor": "Banco XPTO — Fatura Cartão",
      "valor": 612.40,
      "data_vencimento_original": "2026-09-10",
      "dias_atraso": 5,
      "origem": "open_finance_pluggy",
      "negativado": false,
      "linha_digitavel": "34191.79001 01043.510047 91020.150008 1 96380000061240",
      "acoes_disponiveis": ["pagar_agora", "negociar_com_banco"]
    }
  ]
}
```

Campos-chave:
- **`origem`**: de qual fonte o dado veio (importante para o app saber se pode mostrar linha digitável ou não)
- **`negativado`**: se já está registrado como negativo no birô (afeta o score de forma mais pesada) ou é fatura recente ainda não reportada
- **`linha_digitável`**: só existe quando vem de Open Finance e o banco de origem expõe esse campo — nem todo banco expõe

## Tela: Lista de Pendências (o que o usuário vê)

```
════════════════════════════════════════════════════════════
  SUAS PENDÊNCIAS ATIVAS (3)
════════════════════════════════════════════════════════════

  🔴 Credor Alfa Financeira — R$ 340,00
     Vencida há 120 dias • NEGATIVADO no Serasa
     [Ver opções para negociar →]

  🔴 Loja Beta Varejo — R$ 89,90
     Vencida há 30 dias • NEGATIVADO na Boa Vista
     [Ver opções para negociar →]

  🟡 Banco XPTO — Fatura do cartão — R$ 612,40
     Vencida há 5 dias • Ainda não negativada
     Linha digitável: 34191.79001 01043.510047...  [Copiar]
     [Pagar agora]  [Negociar com o banco]

────────────────────────────────────────────────────────────
  ⚠ Pagar a fatura do cartão (🟡) antes que ela complete 30 dias
     de atraso evita que ela vire uma nova negativação — priorize
     esta primeiro.
```

## Regra de priorização de exibição

1. **Faturas ainda não negativadas** (🟡) aparecem primeiro com um aviso de urgência — evitar que virem negativação é sempre mais barato/rápido do que negociar depois
2. **Dívidas já negativadas** (🔴) aparecem em seguida, ordenadas por dias de atraso (mais antigas primeiro, porque pesam mais no fator "histórico de pagamento")
3. Cada pendência linka direto para as opções de ação já definidas em `guia_pratico_aumento_score.md`

## Frequência de atualização

- Dados do birô: consulta automática a cada 7 dias (soft inquiry, não penaliza) + sempre que o usuário abre o app manualmente
- Dados de Open Finance: sincronização diária (a maioria dos agregadores atualiza extratos 1x por dia) + webhook em tempo real quando o agregador suporta (Pluggy e Belvo oferecem webhooks de atualização de fatura)
