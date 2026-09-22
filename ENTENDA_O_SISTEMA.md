# Entenda o Sistema — Antes de Estruturar Para Produção

Isso não é um guia de instalação (esse já existe em
`GUIA_COMPLETO_VSCODE_AO_AR.md`). Isso é um **tour** — abra o VS Code
do lado enquanto lê, e vá clicando nos arquivos que eu for citando.

---

## PARTE 1 — O que o sistema faz, em uma frase

> "A gente resolve seu nome sujo e aumenta seu score — e te mostra
> exatamente como, passo a passo, até o fim." (ver `LEMA.md`)

Isso se desdobra em **três pilares**:

1. **Diagnóstico** — mostra o score da pessoa e explica por que está
   naquele número, fator por fator
2. **Negociação** — ajuda a pessoa a quitar dívidas negativadas
3. **Marketplace** — mostra ofertas de crédito pré-qualificadas (sem
   nunca prometer aprovação, porque isso é decisão do banco)

E por cima disso, tem **como o sistema se sustenta financeiramente** —
assinatura, consulta avulsa, comissão de negociação.

---

## PARTE 2 — A estrutura de pastas, explicada

Abre o Explorer do VS Code e olha a pasta raiz. São 4 áreas:

```
projeto-fintech-score/
├── docs/          ← documentos que explicam O PRODUTO (negócio, não código)
├── backend/       ← o "cérebro" — toda a lógica roda aqui, em Python
├── frontend/      ← as telas que a pessoa vê e clica, em HTML/JavaScript
└── (vários .md na raiz) ← guias de instalação, deploy, segurança, pendências
```

**Regra simples pra você nunca se perder**: se é uma **decisão de
negócio** (quanto cobrar, como funciona a negociação), está em `docs/`.
Se é **código que roda**, está em `backend/` ou `frontend/`.

---

## PARTE 3 — O backend, por dentro

Abre `backend/app/`. Tem duas subpastas que importam mais:

### `app/core/` — a lógica pura, o "motor"
Cada arquivo aqui faz **uma coisa só**, sem depender de internet nem
de banco de dados. É por isso que a gente conseguiu testar tudo (220
testes) sem precisar de rede.

| Arquivo | O que calcula |
|---|---|
| `score_engine.py` | O motor de score — quanto cada ação (quitar dívida, reduzir uso de cartão) vale em pontos |
| `negociacao.py` | As "regras do jogo" de uma negociação — que status pode virar qual outro status |
| `marketplace.py` | Compara o perfil da pessoa com os critérios de cada oferta de crédito |
| `security.py` | Hash de senha, validação de CPF/CNPJ |
| `billing.py` | Preços (assinatura, consulta avulsa) e leitura de pagamento do Asaas |
| `cache_score.py` | Decide se uma consulta ao Serasa pode usar resultado salvo (economiza dinheiro) |
| `serasa_adapter.py` | Traduz a resposta do Serasa pro formato que o `score_engine.py` entende |

### `app/integrations/` — as chamadas pra fora
Esses arquivos são os únicos que **falam com internet de verdade**
(Pluggy, Asaas, SOA/Serasa). Separados de propósito do `core/`, pra
poder testar a lógica sem precisar de rede.

### `app/main.py` — a "porta de entrada"
É onde ficam os **endpoints** — cada `@app.post(...)` ou `@app.get(...)`
é uma porta que o frontend bate pra pedir alguma coisa. Se você
procurar por `/score/diagnostico-serasa`, por exemplo, vai achar a
função que roda quando alguém pede um diagnóstico real.

---

## PARTE 4 — O frontend, por dentro

Abre `frontend/`. São três telas principais, cada uma um arquivo `.html`:

| Arquivo | Quem usa | O que faz |
|---|---|---|
| `index.html` | O público | Cadastro, login, dashboard de score, assinar plano |
| `admin.html` | Só você | Ver usuários, auditoria, negociações, consulta manual |
| `suporte.html` | O público | Perguntas frequentes + chat de suporte |

Cada um desses arquivos tem, dentro dele mesmo, tanto o **visual**
(HTML/CSS) quanto o **comportamento** (JavaScript, dentro da tag
`<script>`) — é assim que dá pra abrir só com duplo clique, sem
precisar de servidor especial.

---

## PARTE 5 — A jornada de um usuário, do início ao fim

Segue esse caminho, mentalmente, pra entender como as peças se
conectam:

```
1. Pessoa abre index.html → cadastra (CPF validado de verdade)
       ↓
2. Faz login → recebe um "crachá digital" (token JWT)
       ↓
3. Pede diagnóstico:
   - Grátis: digita os dados manualmente (/score/diagnostico)
   - Pago: consulta real no Serasa (/score/diagnostico-serasa)
     → só libera se tiver assinatura OU crédito avulso pago
       ↓
4. Vê as dívidas negativadas → decide negociar uma delas
       ↓
5. Negociação passa por status: iniciada → proposta → aceita → paga → confirmada
       ↓
6. Quando confirmada, o sistema pode cobrar a comissão (via Asaas)
       ↓
7. Score sobe (na próxima consulta) → pessoa vê o progresso
```

---

## PARTE 6 — Onde o dinheiro entra e onde ele sai

Essa é a parte que você mais perguntou, então merece destaque:

**Entra dinheiro** (três portas, todas via Asaas):
- `/pagamentos/assinatura` — R$19,90 (Plus) ou R$39,90 (Premium) por mês
- `/pagamentos/consulta-avulsa` — R$24,90, pagamento único
- `/negociacao/{id}/cobrar-comissao` — só depois que a dívida foi paga de verdade

**Sai dinheiro**:
- Cada consulta real ao Serasa: ~R$16,06 (confirmado no painel da SOA)
- Taxa do Asaas em cada cobrança (Pix, cartão, boleto — variável)

**O que impede sair dinheiro sem entrar receita**: a trava em
`possui_assinatura_ativa()` / `possui_credito_avulso_disponivel()` —
sem uma das duas, o sistema nem tenta consultar o Serasa.

---

## PARTE 7 — Um exercício pra fixar (faz isso agora, no VS Code)

1. Abre `backend/app/main.py`
2. Usa `Ctrl+F` e procura por `/score/diagnostico-serasa`
3. Lê a função de cima a baixo — ela literalmente segue os passos que
   eu descrevi na Parte 6: checa assinatura → consulta (ou usa cache)
   → monta a resposta
4. Agora abre `backend/tests/test_database.py` e procura por
   `TestPossuiAssinaturaAtiva` — são os testes que provam que essa
   trava funciona de verdade

Se você conseguir seguir esse caminho e entender o que cada pedaço
faz, você já entende o sistema o suficiente pra tomar decisão de
produto sobre ele — que é o que importa, não decorar código.

---

## Próximo passo depois de entender

Com isso entendido, os próximos documentos, na ordem certa pra ir pra
produção de verdade:

1. `SUAS_PENDENCIAS.md` — o que só você resolve (crédito, decisão sobre banco de dados)
2. `GUIA_COMPLETO_VSCODE_AO_AR.md` — o passo a passo técnico de deploy
3. `SECURITY.md` — o que está seguro e o que falta antes de operar com dinheiro real de muita gente
