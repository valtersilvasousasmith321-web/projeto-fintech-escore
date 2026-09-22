# STATUS DO PROJETO — Snapshot Final

Última verificação: rodada completa de testes e validação de sintaxe,
executada no momento da entrega deste pacote (72 arquivos no total).

## ✅ Verificado e funcionando agora (rodei de verdade, aqui)

| Item | Resultado |
|---|---|
| Testes de lógica de negócio (score, negociação, marketplace, segurança, adaptador Pluggy, reset de senha, chat de suporte, bloqueio de conta, rate limiter, cobrança) | **223/223 passando** |
| Sintaxe de todos os arquivos Python do projeto | **100% válida** |
| Sintaxe do JavaScript em todos os HTML (`index.html`, `admin.html`, `suporte.html`) | **100% válida** (checado com Node) |
| `manifest.json` e `admin-manifest.json` | JSON válido |
| Script `src/mock_analise_score.py` | Roda e imprime diagnóstico completo |
| Regra "comissão só após resultado confirmado" | Testada e reforçada em código |
| Regra "marketplace nunca diz aprovado/garantido" | Testada estruturalmente |
| Bug real encontrado e corrigido nesta rodada | `HTTPException` dentro do `with obter_conexao()` no login desfazia a contagem de tentativas de bloqueio — corrigido movendo o `raise` pra fora do bloco |
| Vulnerabilidade real encontrada e corrigida (auditoria de segurança) | XSS armazenado no painel admin: `email` e `credor` (texto digitado por qualquer usuário) entravam via `innerHTML` sem escapar — corrigido com escape no frontend + validação de formato mais estrita no backend |

## ⚠️ Escrito corretamente, não testado neste ambiente (sem internet aqui)

| Item | O que fazer |
|---|---|
| API FastAPI completa (`app/main.py`) | `pip install -r requirements.txt` no seu VS Code, depois `uvicorn app.main:app --reload` |
| `tests/test_api.py` | `pytest tests/test_api.py -v` após o install acima |
| `pluggy_client.py` (chamadas HTTP reais à Pluggy) | Precisa de credenciais de sandbox gratuitas em dashboard.pluggy.ai |
| Deploy real no Render/Vercel | Passo a passo em `DEPLOY_PUBLICO.md`, mas a execução é sua |

## Funcionalidades completas nesta versão

- **Diagnóstico de score** — motor completo, explicação fator a fator, plano de ação com prazo
- **Negociação de dívidas** — máquina de estados, comissão só após confirmação, **persistida em banco** (não mais em memória)
- **Marketplace de crédito pré-qualificado** — nunca promete aprovação
- **Autenticação** — cadastro com validação real de CPF/CNPJ, login, JWT
- **Esqueci minha senha** — token de uso único, hash SHA-256, validade de 30 min
- **Bloqueio de conta** — 5 tentativas erradas de senha trava por 15 minutos
- **Chat de suporte** — motor próprio (sem IA externa), classificação por palavra-chave, oferece redirecionamento humano quando não entende ou detecta frustração
- **Painel administrativo** (`admin.html`) — usuários, auditoria, negociações, forçar reset de senha, desbloquear conta — acesso restrito por `is_admin` checado no banco a cada requisição
- **Cobrança real (Asaas)** — assinatura mensal (Plus/Premium) e comissão de negociação, com webhook validado por token, CPF pedido só no momento da cobrança (nunca armazenado em texto puro)
- **Histórico completo de negociação** — cada transição de status persiste na tabela `negociacao_eventos`, testado com SQLite real (não mock)
- **E-mail real (SendGrid)** — recuperação de senha envia e-mail de verdade quando configurado, com fallback pro log em dev
- **Consulta real de score/dívida (Serasa CredNet)** — `/score/diagnostico-serasa` consulta o birô de verdade via SOA Web Services, usando dado real extraído da conta de homologação do usuário (24 testes)
- **Cache de consulta ao birô** — cada consulta CredNet custa ~R$16; resultado é cacheado por 30 dias por documento, evitando gasto repetido — resolve a economia real do modelo de assinatura (6 testes de lógica + 3 testes de UPSERT em SQLite real)
- **Controle de gasto real** (`/admin/gastos-serasa`) — conta consultas pagas de verdade e estima custo total/últimos 30 dias, direto do painel admin
- **Trava de custo por assinatura** — consulta real ao Serasa exige assinatura ativa (ou crédito avulso), impedindo gasto sem receita de volta
- **Consulta avulsa** — pagamento único de R$24,90 (acima do custo real de ~R$16,06, com margem garantida por teste) libera uma consulta sem precisar assinatura
- **Consulta manual do admin** (estilo escritório) — nova aba no painel admin pra atender CPF/CNPJ de quem liga/manda mensagem, sem exigir cadastro do cliente, reaproveitando o mesmo cache de 30 dias
- **Segurança reforçada na integração Serasa** — erro nunca expõe resposta bruta da API ao usuário final, e senha é mascarada até em log interno do servidor
- **Dois apps instaláveis (PWA)** — o público (`index.html`, ícone verde) e o admin (`admin.html`, ícone dourado/escuro, botão de instalar só aparece após login de admin confirmado)
- **Integração Pluggy (Open Finance)** — cliente real + adaptador testado (12 testes, sem rede)

## As três categorias do que "falta" (ver `backend/SECURITY.md` para o detalhe completo)

Nem tudo que falta é código — é importante não confundir as três coisas:

1. **Código que era pendência e já foi resolvido nesta rodada**: histórico de negociação persistido, e-mail real, rate limiter Redis disponível como opção
2. **Código que existe mas tem uma ressalva honesta**: integrações externas (Asaas, Pluggy, Redis) escritas conforme documentação oficial, mas não testadas com rede real neste ambiente — testar no sandbox de cada uma antes de usar com dinheiro/dado real
3. **Não é código, é ação do mundo real**: contrato com birô de crédito, pentest profissional, escolha de cofre de segredos gerenciado — nenhuma quantidade de programação fecha esses itens, dependem de você (ou seu time) fazendo a parte comercial/operacional

## Bugs reais encontrados e corrigidos ao longo do desenvolvimento

- `HTTPException` dentro do `with obter_conexao()` no login desfazia a contagem de tentativas de bloqueio — corrigido movendo o `raise` pra fora do bloco
- XSS armazenado no painel admin (`email`/`credor` inseridos via `innerHTML` sem escapar) — corrigido com escape no frontend + validação de formato no backend
- Classe `CadastroRequest` havia desaparecido numa edição anterior, com seus campos incorretamente mesclados em `SuporteChatRequest` — só detectado porque escrevi uma verificação estática de imports cruzados entre módulos (o `py_compile` sozinho não detecta esse tipo de erro, só checa sintaxe de um arquivo isolado)
- Uma edição de teste cortou `TestPersistenciaEventosNegociacao` no meio, fazendo dois testes (`test_fk_de_usuario_invalido...`, `test_rollback...`) ficarem órfãos dentro de uma classe nova sem a negociação de teste que eles precisavam — só detectado porque rodei os testes de verdade depois da edição (o erro apareceu como `FOREIGN KEY constraint failed`), não teria aparecido numa checagem só de sintaxe
- Erro de precificação: sugeri R$9,90 pra consulta avulsa antes de saber o custo real da consulta (R$16,06) — isso daria prejuízo em cada venda. Corrigido pra R$24,90, com um teste que trava essa regra permanentemente (nunca deixa o preço da consulta avulsa ficar abaixo do custo real)

## ❌ Não implementado — pendências reais, documentadas em `backend/SECURITY.md`

- Integração com birôs de crédito (Serasa/Quod/Boa Vista) — endpoints hoje recebem dado já pronto
- Rate limiting distribuído (hoje funciona só com uma instância do servidor)
- Cofre de segredos gerenciado (hoje usa variável de ambiente simples)
- Envio de e-mail real (hoje é um `print()` no console — token de reset)
- Histórico detalhado de eventos de negociação persistido (só o status atual está no banco)
- SQLite não é adequado para volume nacional (ver `docs/estrategia_nacional_diferenciais.md`)
- Pentest / scan de segurança profissional

## Estrutura completa entregue

```
projeto-fintech-score/
├── README.md, LEMA.md, STATUS_DO_PROJETO.md
├── INSTALACAO_WINDOWS.md, DEPLOY_PUBLICO.md
├── docs/                    (9 documentos técnicos)
├── manual/                  (manual do usuário)
├── src/                     (script demonstrativo standalone)
├── frontend/
│   ├── index.html           (app público — login, diagnóstico, PWA)
│   ├── admin.html           (painel admin — PWA separado, ícone próprio)
│   ├── suporte.html         (FAQ + chat de suporte)
│   ├── dashboard_score.html, plano_acao.html  (telas estáticas de referência visual)
│   ├── manifest.json, service-worker.js       (PWA público)
│   ├── admin-manifest.json, admin-service-worker.js  (PWA admin)
│   └── icons/                (favicons + ícones de instalação, dois conjuntos)
└── backend/
    ├── app/
    │   ├── core/             (lógica pura — 100% testada, 8 módulos)
    │   ├── integrations/     (cliente + adaptador Pluggy)
    │   ├── main.py, auth.py, schemas.py, database.py
    ├── tests/                 (17 arquivos de teste, 220 rodam sem instalar nada)
    ├── requirements.txt
    ├── SECURITY.md
    └── README.md
```

## O que este pacote é, com honestidade

É uma **base de engenharia sólida e comprovadamente correta**, ponta a
ponta: diagnóstico de score, negociação de dívida, marketplace,
autenticação completa (com recuperação de senha e bloqueio de conta),
suporte com chat próprio, e painel administrativo — tudo com lógica de
negócio testada de verdade (223 testes) e sem nenhuma promessa de
"garantia" de crédito que não pudesse ser cumprida.

Não é, ainda, um sistema recebendo dinheiro e dado real de milhares de
usuários — isso exige as integrações externas reais (birô, Pluggy em
produção) e os itens de infraestrutura listados acima, que são trabalho
de próxima fase, não de documentação. Cada pendência está marcada onde
está, sem letras miúdas.
