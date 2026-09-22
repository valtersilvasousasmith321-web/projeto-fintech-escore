# Suas Pendências — O Que Fazer, Passo a Passo

Isso é só o que **não é código** — coisas que só você (ou seu time)
resolve, em ordem de prioridade real pro lançamento.

---

## 0. Banco de dados — ✅ código resolvido, falta só configurar no painel do Render

**Atualização**: escolhemos o caminho do disco persistente (mais rápido, menos risco — mantém o SQLite que já está testado com 220+ testes, em vez de reescrever pra Postgres sem poder testar aqui).

**O que já está pronto no código**: `backend/app/database.py` agora lê o caminho do banco de uma variável de ambiente (`DATABASE_PATH`) quando ela existir — testado com 3 testes reais (`TestResolverCaminhoBanco` em `tests/test_database.py`). Sem essa variável (ambiente local, VS Code), continua funcionando exatamente como antes.

**O que só você faz, no painel do Render** (passo a passo completo na seção 9.1 do `GUIA_COMPLETO_VSCODE_AO_AR.md`):
1. Trocar o plano do serviço pra `Starter` (~US$7/mês — o disco persistente exige plano pago)
2. Em **Disks** → **Add Disk** → Mount Path `/var/data`, tamanho 1GB
3. Configurar a variável `DATABASE_PATH=/var/data/dados_app.db`
4. Testar: cadastrar um usuário, forçar um redeploy manual, confirmar que o usuário continua lá

Isso não trava mais o lançamento — é só um passo de configuração, não decisão pendente.

---

## 1. Testar as integrações de pagamento no sandbox (antes de tudo)

**Por quê primeiro**: sem isso, você não sabe se vai cobrar corretamente
quando gente de verdade pagar.

**O que fazer**:
1. Entre em https://sandbox.asaas.com e crie a conta de sandbox (gratuita, na hora)
2. Gere uma API Key em Integrações → Chaves de API
3. Configure `ASAAS_API_KEY` e `ASAAS_SANDBOX=true` no Render
4. No app publicado, cadastre um usuário de teste e clique em "Assinar Plus"
5. Confirme que aparece uma cobrança fictícia no painel do Asaas
6. Configure o webhook (painel Asaas → Integrações → Webhooks) apontando pra `https://SEU-APP.onrender.com/pagamentos/webhook`, com o mesmo token que você colocou em `ASAAS_WEBHOOK_TOKEN`
7. Pague a cobrança fictícia no sandbox e confirme que o status muda no seu banco (consulte via `/admin/negociacoes` ou `/admin/usuarios`)

**Quando considerar concluído**: quando você mesmo, de ponta a ponta, cadastrar → assinar → pagar (fictício) → ver o status mudar, sem erro.

---

## 2. Contrato com birô de crédito (Serasa/Quod/Boa Vista) — ✅ código já integrado

**Atualização**: você já criou a conta na SOA Web Services e me passou a
documentação real dos produtos CredNet e Negativações/Excluir — o código
de integração já está escrito e testado (`app/core/serasa_adapter.py`,
29 testes usando JSON real da conta de homologação;
`app/integrations/serasa_client.py`).

**Descoberta importante sobre "Excluir Negativação"**: esse endpoint
exige um `uniqueID` que só existe se **você mesmo** registrou a
negativação via `Inserir`. No modelo atual do produto (negociar
dívidas que o CREDOR ORIGINAL já negativou), a empresa não tem esse
`uniqueID` — só o credor original consegue dar baixa do lado dele.
Isso não é um problema de código, é uma característica de como a
Serasa funciona: **confirmação de baixa, hoje, depende do credor
original fazer isso, não da nossa plataforma**. Se no futuro a empresa
se tornar agente autorizado de algum credor parceiro, aí sim
`inserir_negativacao()`/`excluir_negativacao()` fariam sentido de
ponta a ponta.

**O que ainda falta, do seu lado**:
1. Pedir o crédito de cortesia pra testar em produção (ou confirmar o modelo de cobrança pré-pago/pós-pago)
2. ~~Confirmar URL de produção~~ ✅ resolvido — é `https://producao.soawebservices.com.br`
3. Confirmar com o suporte o significado dos campos `"adicionais": [1]` (CredNet) e a tabela de códigos de `"codigoBaixa"` (Negativações/Excluir) — copiei os valores de exemplo da doc, mas não sabemos a lista completa de opções
4. Testar uma consulta real (não de homologação) antes de divulgar publicamente

**O que já dá pra fazer agora**: configurar `SOA_EMAIL`/`SOA_SENHA` no Render e testar o endpoint `/score/diagnostico-serasa` — ele já consulta o CredNet de verdade e roda pelo motor de score completo.

---

## 3. Pentest profissional (antes de divulgar em volume)

**Por quê**: eu revisei o código linha por linha, mas um pentest testa o
**sistema publicado, em produção**, com ferramentas que simulam ataque
real — é uma camada diferente da revisão de código.

**O que fazer**:

- **Opção econômica pra começar**: rode você mesmo um scan com OWASP ZAP (gratuito) contra a URL publicada — https://www.zaproxy.org/. Não substitui um pentest humano, mas pega os problemas mais óbvios de graça, antes de pagar por algo mais completo
- **Opção profissional**: contrate um freelancer especializado (busque "pentest" em Workana, 99Freelas, ou comunidades de segurança como a lista de profissionais da OWASP Brasil) — preço costuma variar de R$1.500 a R$8.000 dependendo da profundidade, pra um sistema desse tamanho
- **Quando fazer**: depois que o sistema já estiver no ar recebendo os primeiros usuários reais, mas **antes** de qualquer campanha de divulgação em volume (anúncio pago, mídia, etc.) — não precisa ser o primeiro passo, mas não deixe pra depois de já ter volume de dado sensível acumulado

---

## 4. Cofre de segredos gerenciado

**Por quê**: hoje `JWT_SECRET_KEY`, `ASAAS_API_KEY` etc. vivem como variável de ambiente simples no Render.

**O que fazer, na prática, agora**: nada urgente — o Render já criptografa variáveis de ambiente em repouso, o que é aceitável pra fase inicial. Isso só se torna prioridade se/quando você:
- Tiver mais de uma pessoa com acesso ao painel do Render (nesse caso, considere migrar segredos pra um cofre como HashiCorp Vault ou AWS Secrets Manager, com controle de quem acessa o quê)
- Precisar rotacionar chaves automaticamente por política de compliance

**Ação concreta se quiser fazer agora mesmo**: nenhuma — é decisão de "quando", não de "como". Guarde essa pendência pra quando tiver mais gente na operação.

---

## 5. Infraestrutura complementar (rápido, faça em uma tarde)

Cada um desses é uma conta gratuita + 5 minutos de configuração:

- [ ] **Cloudflare** — https://www.cloudflare.com, plano Free, aponte seu domínio pra lá
- [ ] **Sentry** — https://sentry.io, plano Free, pegue o DSN e configure alerta de erro
- [ ] **Backup do banco** — enquanto for SQLite, programe um lembrete (Google Calendar mesmo) pra baixar o arquivo `dados_app.db` do Render uma vez por semana
- [ ] **Dependabot** — já vem ativado automaticamente em repositório GitHub, só confirme em Settings → Security do seu repositório

---

## Ordem sugerida

```
Esta semana:     0 (configurar disco no Render) + 1 (testar pagamento sandbox) + 5 (infra rápida)
Próximas semanas: 2 (contrato birô) — inicia a conversa, mas não trava o lançamento
Antes de divulgar em volume: 3 (pentest)
Quando crescer o time: 4 (cofre de segredos)
```

Você pode lançar publicamente **depois do item 0 configurado e do item
1 testado** — os itens 2, 3 e 4 não bloqueiam o lançamento inicial, só
ficam cada vez mais
importantes conforme o sistema cresce em usuários e dinheiro real.
