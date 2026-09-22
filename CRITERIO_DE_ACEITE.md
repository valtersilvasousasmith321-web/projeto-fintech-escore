# O Que o Profissional Precisa Entregar

Checklist de aceite. Cada item tem uma forma de **você mesmo
conferir**, sem precisar confiar só na palavra de quem foi contratado.

---

## 1. URLs funcionando

- [ ] URL do backend (ex: `https://algo.onrender.com`)
- [ ] URL do frontend (ex: `https://algo-frontend.onrender.com` ou domínio próprio)

**Como você confere**: abre `https://SUA-URL-BACKEND/health` no
navegador — tem que aparecer `{"status":"ok"}`. Abre a URL do
frontend — tem que carregar a tela de login, sem erro branco.

---

## 2. Banco de dados persistente configurado

Esse é o item mais importante — sem ele, o sistema "esquece" usuário
sozinho de tempos em tempos (documentado em `SUAS_PENDENCIAS.md`,
item 0).

- [ ] Disco persistente anexado no Render (ou Postgres, se escolherem
      trocar)
- [ ] Variável `DATABASE_PATH` configurada apontando pro disco

**Como você confere**: cadastra um usuário de teste no site
publicado. Pede pro profissional forçar um redeploy (ou espera 24h).
Confere se o usuário ainda existe (login de novo, ou via
`/admin/usuarios`). Se sumiu, não foi entregue certo.

---

## 3. Todas as variáveis de ambiente configuradas

Lista completa em `FICHA_TECNICA.md`, seção "Variáveis de ambiente".
Peça pro profissional confirmar, uma por uma:

- [ ] `JWT_SECRET_KEY` (gerada nova, não reaproveitada de teste local)
- [ ] `APP_ENV=production`
- [ ] `DATABASE_PATH`
- [ ] `ADMIN_BOOTSTRAP_EMAIL` / `ADMIN_BOOTSTRAP_SENHA` (configuradas
      no primeiro deploy, **removidas depois** — item 4 abaixo confirma isso)
- [ ] `CORS_ALLOWED_ORIGINS` (apontando pra URL real do frontend, não
      `localhost`)
- [ ] `SOA_EMAIL` / `SOA_SENHA` / `SOA_AMBIENTE`
- [ ] `ASAAS_API_KEY` / `ASAAS_SANDBOX` / `ASAAS_WEBHOOK_TOKEN`
- [ ] `SENDGRID_API_KEY` / `SENDGRID_FROM_EMAIL` (se for usar e-mail real)

**Como você confere**: pede print da tela de "Environment Variables"
do Render (os valores não precisam aparecer, só confirma que cada
nome da lista está lá).

---

## 4. Segurança básica de produção

- [ ] `ADMIN_BOOTSTRAP_EMAIL`/`SENHA` **removidas** do Render depois
      que a conta de admin já foi criada com sucesso
- [ ] Login no `admin.html` publicado funciona com a conta de admin
- [ ] HTTPS confirmado nas duas URLs (backend e frontend) — Render já
      faz isso automático, só confere que a URL começa com `https://`
      e não `http://`

**Como você confere**: tenta entrar no admin com o e-mail/senha que
vocês combinaram. Se funcionar, e se você pedir pro profissional
mostrar que as variáveis de bootstrap sumiram do painel, está OK.

---

## 5. Pagamento testado de ponta a ponta

- [ ] Webhook do Asaas configurado, apontando pra URL de produção
- [ ] Um pagamento de teste (sandbox) foi feito e confirmado no
      sistema

**Como você confere**: cadastra um usuário de teste, clica em
"Assinar Plus", paga a cobrança fictícia no sandbox do Asaas. Confere
no `/admin/usuarios` (ou pedindo consulta ao banco) se o status da
assinatura mudou pra "ativa".

---

## 6. Todos os testes passando

- [ ] `python -m unittest discover -s tests -v` — sem nenhum `FAILED`
      (exceto o `test_api` se `pytest` não estiver instalado nesse
      ambiente específico)
- [ ] `pytest tests/ -v` — suíte completa, incluindo `test_api.py`

**Como você confere**: peça o print (ou log completo) da execução
desses dois comandos, mostrando `OK` no final.

---

## 7. Painel de teste funcionando contra a URL de produção

- [ ] `frontend/teste_funcionamento.html` rodado com a URL da API
      trocada pra produção, todos os 6 passos com status "OK"

**Como você confere**: abre esse arquivo você mesmo, troca a URL no
campo do topo pra `https://SUA-URL-BACKEND`, clica em "Rodar todos os
testes". Não depende do profissional pra essa checagem — é
autoexplicativo.

---

## 8. Acesso devolvido pra você

- [ ] Acesso de colaborador/admin no repositório GitHub
- [ ] Acesso de admin (ou transferência de owner) na conta do Render
- [ ] Lista de todas as contas de terceiro criadas em seu nome (Asaas,
      SOA, SendGrid, etc.) com login que só você controla — nunca deixe
      um prestador ser o único com acesso a essas contas

**Como você confere**: entra você mesmo em cada painel (GitHub,
Render, Asaas) com sua própria conta e confirma acesso — não aceite
"depois eu te passo" como entrega finalizada.

---

## 9. Documentação do que foi decidido/mudado

- [ ] Se o profissional tomou alguma decisão técnica não coberta
      pelos documentos existentes (ex: trocou de Render pra outro
      provedor, mudou alguma configuração de segurança), isso precisa
      estar escrito em algum lugar — não só na cabeça da pessoa

**Como você confere**: pede um resumo por escrito (e-mail, ou
atualização nos próprios `.md` do projeto) de qualquer coisa que
tenha saído do que já estava documentado.

---

## Resumo — a pergunta de uma frase pra fazer antes de aceitar

> "Eu, sem depender de você, consigo abrir o site, cadastrar,
> assinar, ver isso funcionando no admin, e continuar vendo depois de
> alguns dias?"

Se a resposta é sim pros 9 itens acima, o serviço foi entregue de
verdade. Se qualquer um depende de "confia em mim que está certo",
não está completo.
